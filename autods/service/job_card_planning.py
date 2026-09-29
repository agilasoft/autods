# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Repair Order → Job Card planning: one card per selected Service line; Service Settings drive capacity, close time, overlap, and multi-day sliding."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, flt, get_datetime, getdate, today

from autods.service.charge_service_row import (
	iter_service_charge_rows,
	service_line_index_for_charge_row_name,
	sparepart_linked_to_service,
)
from autods.service.gate_pass_utils import require_entry_gate_pass
from autods.service.vehicle_schedule_utils import job_card_schedule_window

# Charge fields that must not change while a non-Cancelled Job Card locks the row.
# ``service_row`` is excluded: label may be refreshed by bind_charge_service_link;
# link identity is ``parent_service_charge``. Keep in sync with
# AUTODS_JOB_CARD_LOCKED_CHARGE_FIELDS in repair_order.js (minus service_row).
_LOCKED_CHARGE_FIELDS = (
	"service_item_type",
	"item",
	"qty",
	"rate",
	"standard_hours",
	"parent_service_charge",
	"description",
	"bill_type",
	"uom",
	"bill_to",
	"item_type",
	"warehouse",
	"color_code",
	"paint_type",
)


def _time_field_to_str(val) -> str:
	if val is None:
		return "09:00:00"
	if isinstance(val, str):
		return val
	if hasattr(val, "total_seconds"):
		secs = int(val.total_seconds()) % 86400
		h, rem = divmod(secs, 3600)
		m, s = divmod(rem, 60)
		return f"{h:02d}:{m:02d}:{s:02d}"
	return "09:00:00"


def _planning_settings():
	return frappe.get_cached_doc("Service Settings")


def _service_charge_rows(ro):
	for row in ro.get("charges") or []:
		if (row.service_item_type or "").strip() == "Service":
			yield row


def _existing_job_card_for_charge_row(repair_order: str, charge_row_name: str) -> str | None:
	if not repair_order or not charge_row_name:
		return None
	existing = frappe.get_all(
		"Job Card",
		filters={
			"repair_order": repair_order,
			"service_charge_row": charge_row_name,
			"status": ("!=", "Cancelled"),
		},
		pluck="name",
		limit=1,
	)
	return existing[0] if existing else None


def get_active_job_cards_by_service_charge_row(repair_order: str) -> dict[str, str]:
	"""Map Service charge row name → Job Card name for non-Cancelled cards."""
	if not repair_order:
		return {}
	rows = frappe.get_all(
		"Job Card",
		filters={
			"repair_order": repair_order,
			"status": ("!=", "Cancelled"),
			"service_charge_row": ("is", "set"),
		},
		fields=["name", "service_charge_row"],
	)
	out: dict[str, str] = {}
	for r in rows:
		svc = (r.get("service_charge_row") if isinstance(r, dict) else r.service_charge_row) or ""
		svc = str(svc).strip()
		if not svc:
			continue
		jc = r.get("name") if isinstance(r, dict) else r.name
		out[svc] = jc
	return out


def get_locked_charge_row_names(ro) -> dict[str, str]:
	"""Charge child row name → Job Card name for rows locked by a non-Cancelled Job Card.

	Locks the Service line that has a Job Card and all Spareparts/Overhead linked to it.
	"""
	repair_order = getattr(ro, "name", None) or ""
	jc_by_service = get_active_job_cards_by_service_charge_row(repair_order)
	if not jc_by_service:
		return {}

	locked: dict[str, str] = {}
	for svc in iter_service_charge_rows(ro):
		jc = jc_by_service.get(svc.name)
		if not jc:
			continue
		locked[svc.name] = jc
		idx = service_line_index_for_charge_row_name(ro, svc.name)
		for row in ro.get("charges") or []:
			t = (getattr(row, "service_item_type", None) or "").strip()
			if t not in ("Spareparts", "Overhead"):
				continue
			if sparepart_linked_to_service(row, svc.name, idx):
				locked[row.name] = jc
	return locked


def _charge_field_value(row, fieldname: str):
	val = getattr(row, fieldname, None)
	if fieldname in ("qty", "rate", "standard_hours"):
		return flt(val)
	return (val if val is not None else "") if not isinstance(val, str) else val.strip()


def validate_charges_not_locked(ro) -> None:
	"""Block edit/delete of charge rows locked by a non-Cancelled Job Card.

	Call **before** ``validate_charge_service_links`` so bind-side label/parent
	refreshes do not look like user edits. Use ``validate_no_new_links_to_locked_services``
	after bind for new Spareparts/Overhead targeting a locked Service.
	"""
	if not getattr(ro, "name", None) or getattr(ro, "is_new", lambda: False)():
		return

	jc_by_service = get_active_job_cards_by_service_charge_row(ro.name)
	if not jc_by_service:
		return

	before = None
	if hasattr(ro, "get_doc_before_save"):
		before = ro.get_doc_before_save()
	if before is None and frappe.db.exists("Repair Order", ro.name):
		before = frappe.get_doc("Repair Order", ro.name)

	locked_before = get_locked_charge_row_names(before) if before else {}
	if not locked_before:
		return

	current_by_name = {r.name: r for r in (ro.get("charges") or []) if getattr(r, "name", None)}
	before_by_name = {
		r.name: r for r in (before.get("charges") or []) if getattr(r, "name", None)
	} if before else {}

	for row_name, jc in locked_before.items():
		if row_name not in current_by_name:
			frappe.throw(
				_("Cannot remove charge line locked by Job Card {0}.").format(frappe.bold(jc)),
				title=_("Charges Locked"),
			)
		old = before_by_name.get(row_name)
		new = current_by_name[row_name]
		if not old:
			continue
		for fieldname in _LOCKED_CHARGE_FIELDS:
			if _charge_field_value(old, fieldname) != _charge_field_value(new, fieldname):
				label = _(fieldname.replace("_", " ").title())
				frappe.throw(
					_("Cannot change {0} on charge line locked by Job Card {1}.").format(
						frappe.bold(label), frappe.bold(jc)
					),
					title=_("Charges Locked"),
				)


def validate_no_new_links_to_locked_services(ro) -> None:
	"""Block new or re-linked Spareparts/Overhead targeting a Service with a non-Cancelled Job Card.

	Call **after** ``validate_charge_service_links`` so ``parent_service_charge`` is resolved.
	"""
	if not getattr(ro, "name", None) or getattr(ro, "is_new", lambda: False)():
		return

	jc_by_service = get_active_job_cards_by_service_charge_row(ro.name)
	if not jc_by_service:
		return

	before = None
	if hasattr(ro, "get_doc_before_save"):
		before = ro.get_doc_before_save()
	if before is None and frappe.db.exists("Repair Order", ro.name):
		before = frappe.get_doc("Repair Order", ro.name)

	before_by_name = (
		{r.name: r for r in (before.get("charges") or []) if getattr(r, "name", None)} if before else {}
	)

	for row in ro.get("charges") or []:
		t = (getattr(row, "service_item_type", None) or "").strip()
		if t not in ("Spareparts", "Overhead"):
			continue
		parent = (getattr(row, "parent_service_charge", None) or "").strip()
		if not parent or parent not in jc_by_service:
			continue
		jc = jc_by_service[parent]
		prev = before_by_name.get(row.name)
		prev_parent = (getattr(prev, "parent_service_charge", None) or "").strip() if prev else ""
		if not prev or prev_parent != parent:
			frappe.throw(
				_("Cannot link Spareparts or Overhead to a service locked by Job Card {0}.").format(
					frappe.bold(jc)
				),
				title=_("Charges Locked"),
			)


def _existing_sibling_job_cards(repair_order: str) -> list:
	"""Non-cancelled Job Cards already created for this Repair Order."""
	if not repair_order:
		return []
	return frappe.get_all(
		"Job Card",
		filters={
			"repair_order": repair_order,
			"status": ("!=", "Cancelled"),
		},
		fields=["name", "start_time", "end_time", "work_area", "service_charge_row", "technician"],
		order_by="start_time asc",
	)


def _seed_plan_from_existing_job_cards(repair_order: str, cursor, prior_planned: list, reserved_slots: list):
	"""Advance planning cursor / capacity from sibling Job Cards on the same RO."""
	for jc in _existing_sibling_job_cards(repair_order):
		start, end = job_card_schedule_window(jc)
		if not start or not end:
			continue
		work_area = jc.get("work_area") if isinstance(jc, dict) else getattr(jc, "work_area", None)
		prior_planned.append(
			{
				"work_area": work_area,
				"planned_start": start,
				"planned_end": end,
			},
		)
		if end > cursor:
			cursor = end
		technician = jc.get("technician") if isinstance(jc, dict) else getattr(jc, "technician", None)
		if technician:
			reserved_slots.append((technician, start, end))
	return cursor


def _filter_service_charge_rows(ro, selected_charge_rows=None):
	rows = sorted(_service_charge_rows(ro), key=lambda r: r.idx or 0)
	if not selected_charge_rows:
		return rows
	selected = {str(n).strip() for n in selected_charge_rows if str(n).strip()}
	if not selected:
		return rows
	by_name = {r.name: r for r in rows}
	unknown = selected - set(by_name)
	if unknown:
		frappe.throw(_("Invalid service charge row(s): {0}").format(", ".join(sorted(unknown))))
	return [by_name[name] for name in (row.name for row in rows) if name in selected]


def _service_line_description(row) -> str:
	desc = (row.description or "").strip() or (row.item_name or "").strip() or (row.item or "").strip()
	return desc or _("Service line")


def _vehicle_header_for_ro(ro) -> dict:
	"""Vehicle context for the job card service selection modal."""
	year = getattr(ro, "vehicle_year_model", None)
	make = (getattr(ro, "vehicle_make", None) or "").strip()
	model = (getattr(ro, "vehicle_model", None) or "").strip()
	vehicle_image = None

	if ro.vehicle_unit:
		vu = frappe.db.get_value(
			"Vehicle Unit",
			ro.vehicle_unit,
			["image", "make", "model", "year_model"],
			as_dict=True,
		)
		if vu:
			vehicle_image = vu.get("image")
			if not year:
				year = vu.get("year_model")
			if not make:
				make = (vu.get("make") or "").strip()
			if not model:
				model = (vu.get("model") or "").strip()

	title_parts = []
	if year:
		title_parts.append(str(year))
	if make:
		title_parts.append(make)
	if model:
		title_parts.append(model)
	vehicle_title = " ".join(title_parts).strip()

	repair_date = ro.repair_date
	return {
		"vehicle_unit": ro.vehicle_unit,
		"vehicle_image": vehicle_image,
		"vehicle_title": vehicle_title,
		"plate_no": (ro.plate_no or "").strip(),
		"repair_date": str(repair_date) if repair_date else "",
		"customer": ro.customer,
	}


def build_service_selection(ro) -> dict:
	"""Return Service charge lines on a Repair Order for the job card selection modal."""
	if not ro.name:
		frappe.throw(_("Save the Repair Order before planning job cards"))

	settings = _planning_settings()
	slot_hours = flt(getattr(settings, "planning_slot_hours", None)) or 2.0
	if slot_hours <= 0:
		slot_hours = 2.0

	service_rows = sorted(_service_charge_rows(ro), key=lambda r: r.idx or 0)
	item_codes = list({(r.item or "").strip() for r in service_rows if (r.item or "").strip()})
	item_images = {}
	if item_codes:
		for item_row in frappe.get_all(
			"Item",
			filters={"name": ("in", item_codes)},
			fields=["name", "image"],
		):
			image = item_row.get("image") if isinstance(item_row, dict) else getattr(item_row, "image", None)
			name = item_row.get("name") if isinstance(item_row, dict) else getattr(item_row, "name", None)
			if image and name:
				item_images[name] = image

	services = []
	for row in service_rows:
		if not row.name:
			frappe.throw(_("Save charge lines before planning job cards"))
		item_code = (row.item or "").strip()
		services.append(
			{
				"name": row.name,
				"idx": row.idx or 0,
				"item": row.item,
				"description": (getattr(row, "description", None) or "").strip()[:200],
				"standard_hours": _charge_labor_hours(row, slot_hours),
				"existing_job_card": _existing_job_card_for_charge_row(ro.name, row.name),
				"item_image": item_images.get(item_code),
			},
		)

	vehicle_header = _vehicle_header_for_ro(ro)
	return {
		"repair_order": ro.name,
		"services": services,
		"service_line_count": len(services),
		**vehicle_header,
	}


def _charge_labor_hours(row, default: float) -> float:
	"""Planned labor duration for a Service charge row."""
	std = flt(getattr(row, "standard_hours", None))
	if std:
		return std
	hours = flt(getattr(row, "hours", None))
	if hours:
		return hours
	return default


def _resolve_work_area(service_type: str | None, settings) -> str | None:
	if not getattr(settings, "auto_assign_work_area", None):
		return None
	if service_type:
		wa = frappe.db.get_value("Service Type", service_type, "default_work_area")
		if wa:
			return wa
	return getattr(settings, "planning_default_work_area", None) or None


def _resolve_skills_group(service_type: str | None, settings) -> str | None:
	if service_type:
		sg = frappe.db.get_value("Service Type", service_type, "default_technician_skills_group")
		if sg:
			return sg
	return getattr(settings, "planning_default_technician_skills_group", None) or None


def _work_area_vehicle_load(work_area: str, on_date) -> int:
	if not work_area or not on_date:
		return 0
	return int(
		frappe.db.sql(
			"""
			SELECT COUNT(DISTINCT COALESCE(NULLIF(vehicle_unit, ''), repair_order))
			FROM `tabJob Card`
			WHERE work_area = %s
			  AND repair_date = %s
			  AND status NOT IN ('Completed', 'Cancelled')
			""",
			(work_area, on_date),
		)[0][0]
		or 0
	)


def _ro_has_job_in_bay_on_date(ro_name: str, work_area: str, on_date) -> bool:
	if not work_area or not on_date:
		return False
	return bool(
		frappe.db.exists(
			"Job Card",
			{
				"repair_order": ro_name,
				"work_area": work_area,
				"repair_date": on_date,
				"status": ("not in", ("Completed", "Cancelled")),
			},
		)
	)


def _vehicle_increment_for_ro(ro_name: str, work_area: str | None, on_date, prior_planned: list) -> int:
	"""Extra distinct-vehicle count this RO adds for (work_area, on_date) in the plan batch."""
	if not work_area or not on_date:
		return 0
	if _ro_has_job_in_bay_on_date(ro_name, work_area, on_date):
		return 0
	for pl in prior_planned:
		if pl.get("work_area") == work_area and getdate(pl.get("planned_start")) == on_date:
			return 0
	return 1


def _technician_open_jobs(employee: str, on_date) -> int:
	if not employee or not on_date:
		return 0
	return frappe.db.count(
		"Job Card",
		{
			"technician": employee,
			"repair_date": on_date,
			"status": ("not in", ("Completed", "Cancelled")),
		},
	)


def _intervals_overlap(a0, a1, b0, b1) -> bool:
	a0, a1 = get_datetime(a0), get_datetime(a1)
	b0, b1 = get_datetime(b0), get_datetime(b1)
	if a0 > a1:
		a0, a1 = a1, a0
	if b0 > b1:
		b0, b1 = b1, b0
	return a0 < b1 and a1 > b0


def _technician_time_overlap(
	employee: str,
	start_dt,
	end_dt,
	exclude_jc: str | None = None,
	reserved_intervals: list | None = None,
) -> bool:
	if not employee or not start_dt or not end_dt:
		return False
	for emp, rs, re in reserved_intervals or []:
		if emp == employee and _intervals_overlap(start_dt, end_dt, rs, re):
			return True
	filters = [
		["Job Card", "technician", "=", employee],
		["Job Card", "repair_date", "=", getdate(start_dt)],
		["Job Card", "status", "not in", ("Completed", "Cancelled")],
	]
	if exclude_jc:
		filters.append(["Job Card", "name", "!=", exclude_jc])
	jobs = frappe.get_all(
		"Job Card",
		filters=filters,
		fields=["name", "start_time", "end_time", "expected_completion_date"],
	)
	for j in jobs:
		js = j.start_time or j.expected_completion_date
		je = j.end_time or j.expected_completion_date
		if not js or not je:
			continue
		if _intervals_overlap(start_dt, end_dt, js, je):
			return True
	return False


def _day_open_close(on_date, opens_str: str, closes_str: str):
	day_open = get_datetime(f"{on_date} {opens_str}")
	day_close = get_datetime(f"{on_date} {closes_str}")
	if day_close <= day_open:
		day_close = add_to_date(day_open, hours=8)
	return day_open, day_close


def _allocate_slot(
	cursor,
	duration_hours: float,
	work_area: str | None,
	ro,
	settings,
	prior_planned: list,
) -> tuple[object, object, str | None, list]:
	"""Pick planned_start, planned_end, effective work_area (may be cleared), and warnings."""
	warnings: list = []
	base = getdate(ro.repair_date or today())
	max_extra = max(cint(getattr(settings, "planning_max_extra_days", None) or 0), 0)
	last_allowed = getdate(add_to_date(base, days=max_extra))
	can_slide = max_extra > 0

	opens = _time_field_to_str(getattr(settings, "planning_shop_opens", None))
	closes = _time_field_to_str(getattr(settings, "planning_shop_closes", None))
	respect_cap = bool(getattr(settings, "respect_work_area_capacity", None))
	wa_full = getattr(settings, "planning_work_area_full", None) or "warn_only"
	past_close = getattr(settings, "planning_past_shop_close", None) or "warn_only"

	candidate = get_datetime(cursor)
	day0_open = get_datetime(f"{base} {opens}")
	if candidate < day0_open:
		candidate = day0_open

	eff_wa = work_area
	max_iters = 500
	for _iter in range(max_iters):
		d = getdate(candidate)
		if d > last_allowed:
			frappe.throw(
				_(
					"No slot fits within {0} calendar day(s) after the repair date. Increase \"Max extra days for sliding slots\" or change planning rules in Service Settings."
				).format(max_extra + 1)
			)

		day_open, day_close = _day_open_close(d, opens, closes)
		if candidate < day_open:
			candidate = day_open
		if candidate > day_close:
			if past_close == "slide_next_day" and can_slide:
				nd = add_to_date(d, days=1)
				nd = getdate(nd)
				if nd > last_allowed:
					frappe.throw(
						_(
							"Start time is past shop close and cannot slide further. Increase \"Max extra days for sliding slots\" in Service Settings."
						)
					)
				candidate = get_datetime(f"{nd} {opens}")
				continue
			if past_close == "slide_next_day" and not can_slide:
				warnings.append(
					_(
						"Start time is past shop close; set \"Max extra days for sliding slots\" greater than 0 to continue on the next day."
					),
				)
			else:
				warnings.append(_("Start time past shop close; clamped to day open"))
			candidate = day_open

		slot_end = add_to_date(candidate, hours=duration_hours)

		if slot_end > day_close:
			if past_close == "slide_next_day" and can_slide:
				nd = add_to_date(d, days=1)
				nd = getdate(nd)
				if nd > last_allowed:
					frappe.throw(
						_(
							"Job would run past workshop close and cannot slide further. Increase \"Max extra days for sliding slots\" or extend workshop hours in Service Settings."
						)
					)
				candidate = get_datetime(f"{nd} {opens}")
				continue
			if past_close == "slide_next_day" and not can_slide:
				warnings.append(
					_(
						"Slot passes shop close; set \"Max extra days for sliding slots\" greater than 0 to continue on the next day."
					),
				)
			else:
				warnings.append(_("Planned window extends past workshop close ({0})").format(closes))

		if eff_wa and respect_cap:
			cap = frappe.db.get_value("Work Area", eff_wa, "capacity")
			if cap:
				used_db = _work_area_vehicle_load(eff_wa, d)
				inc = _vehicle_increment_for_ro(ro.name, eff_wa, d, prior_planned)
				if used_db + inc >= int(cap):
					if wa_full == "slide_next_day" and can_slide:
						nd = getdate(add_to_date(d, days=1))
						if nd > last_allowed:
							frappe.throw(
								_(
									"Work area is at capacity and cannot slide further. Increase \"Max extra days for sliding slots\" or choose another work area / Service Type default."
								)
							)
						candidate = get_datetime(f"{nd} {opens}")
						continue
					if wa_full == "slide_next_day" and not can_slide:
						warnings.append(
							_(
								"Work area {0} is at or over capacity ({1}) on {2}; increase \"Max extra days for sliding slots\" to move to another day."
							).format(eff_wa, cap, d),
						)
					elif wa_full == "omit_work_area":
						warnings.append(
							_("Work area {0} omitted — at vehicle capacity on {1}").format(eff_wa, d),
						)
						eff_wa = None
					elif wa_full == "warn_only":
						warnings.append(
							_("Work area {0} is at or over vehicle capacity ({1}) on {2}").format(
								eff_wa, cap, d
							),
						)

		return candidate, slot_end, eff_wa, warnings

	frappe.throw(_("Could not allocate a planning slot"))


def _pick_technician(
	skills_group: str | None,
	planned_start,
	planned_end,
	settings,
	reserved_intervals: list | None = None,
) -> str | None:
	if not getattr(settings, "auto_assign_technician", None):
		return None
	allow_overlap = getattr(settings, "allow_overlapping_schedules", None)
	respect_load = getattr(settings, "respect_technician_load", None)
	overlap_mode = getattr(settings, "planning_technician_overlap", None) or "warn_only"

	candidates = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
	if not candidates:
		return None
	if skills_group:
		experienced = {
			r
			for r in frappe.get_all(
				"Job Card",
				filters={"technician_skills_group": skills_group, "technician": ("is", "set")},
				pluck="technician",
			)
			if r
		}
		if experienced:
			filtered = [e for e in candidates if e in experienced]
			if filtered:
				candidates = filtered

	def score(emp):
		return _technician_open_jobs(emp, getdate(planned_start))

	best_strict = None
	best_strict_score = None
	if not allow_overlap and respect_load:
		for emp in sorted(candidates, key=score):
			if not _technician_time_overlap(emp, planned_start, planned_end, None, reserved_intervals):
				s = score(emp)
				if best_strict is None or s < best_strict_score:
					best_strict, best_strict_score = emp, s

	if best_strict is not None:
		return best_strict

	# No technician without overlap (or overlap allowed / respect_load off)
	if allow_overlap or not respect_load:
		return min(candidates, key=score)

	if overlap_mode == "omit_technician":
		return None
	if overlap_mode == "block_plan":
		frappe.throw(
			_(
				"No active technician is free in the planned window. Adjust times, enable \"Allow overlapping schedules\", or set \"When every technician overlaps\" to Warn in Service Settings."
			)
		)

	best = None
	best_score = None
	for emp in sorted(candidates, key=score):
		s = score(emp)
		if best is None or s < best_score:
			best, best_score = emp, s
	return best


def build_plan(ro, selected_charge_rows=None) -> dict:
	"""Return planned Job Cards for selected Service charge lines on a Repair Order."""
	if not ro.name:
		frappe.throw(_("Save the Repair Order before planning job cards"))

	settings = _planning_settings()
	base = getdate(ro.repair_date or today())
	opens = _time_field_to_str(getattr(settings, "planning_shop_opens", None))
	slot_hours = flt(getattr(settings, "planning_slot_hours", None)) or 2.0
	if slot_hours <= 0:
		slot_hours = 2.0

	cursor = get_datetime(f"{base} {opens}")
	lines = []
	reserved_slots: list[tuple[str, object, object]] = []
	prior_planned: list = []
	cursor = _seed_plan_from_existing_job_cards(ro.name, cursor, prior_planned, reserved_slots)
	service_rows = _filter_service_charge_rows(ro, selected_charge_rows)

	if not service_rows:
		return {
			"repair_order": ro.name,
			"repair_date": str(base),
			"lines": [],
			"service_line_count": 0,
			"settings": planning_settings_payload(settings),
			**_vehicle_header_for_ro(ro),
		}

	for row in service_rows:
		if not row.name:
			frappe.throw(_("Save charge lines before planning job cards"))

		desc = _service_line_description(row)
		hours = _charge_labor_hours(row, slot_hours)
		duration = max(hours, slot_hours)
		resolved_wa = _resolve_work_area(row.service_type, settings)
		planned_start, planned_end, eff_wa, slot_warnings = _allocate_slot(
			cursor, duration, resolved_wa, ro, settings, prior_planned
		)
		warnings = list(slot_warnings)

		skills_group = _resolve_skills_group(row.service_type, settings)
		technician = _pick_technician(skills_group, planned_start, planned_end, settings, reserved_slots)

		overlap_mode = getattr(settings, "planning_technician_overlap", None) or "warn_only"
		if (
			technician
			and not getattr(settings, "allow_overlapping_schedules", None)
			and getattr(settings, "respect_technician_load", None)
			and overlap_mode == "warn_only"
			and _technician_time_overlap(technician, planned_start, planned_end, None, None)
		):
			warnings.append(
				_("Technician {0} may overlap existing jobs in the system.").format(technician),
			)

		if technician:
			reserved_slots.append((technician, planned_start, planned_end))

		existing_job_card = _existing_job_card_for_charge_row(ro.name, row.name)
		work_details = [
			{
				"charge_row": row.name,
				"description": desc[:140],
				"standard_hours": hours,
			},
		]
		line_dict = {
			"seq": len(lines) + 1,
			"charge_row": row.name,
			"charge_rows": [row.name],
			"item": row.item,
			"description": desc[:200],
			"standard_hours": hours,
			"hours": hours,
			"work_area": eff_wa,
			"technician_skills_group": skills_group,
			"technician": technician,
			"planned_start": str(planned_start),
			"planned_end": str(planned_end),
			"assignment_date": str(getdate(planned_start)),
			"warnings": warnings,
			"existing_job_card": existing_job_card,
			"work_details": work_details,
		}
		lines.append(line_dict)
		prior_planned.append(
			{
				"work_area": eff_wa,
				"planned_start": planned_start,
				"planned_end": planned_end,
			},
		)
		cursor = planned_end

	return {
		"repair_order": ro.name,
		"repair_date": str(base),
		"lines": lines,
		"service_line_count": len(service_rows),
		"settings": planning_settings_payload(settings),
		**_vehicle_header_for_ro(ro),
	}


def create_job_cards(ro, selected_charge_rows=None) -> dict:
	"""Insert one Job Card per selected Service charge line; skip lines that already have a Job Card."""
	if not ro.name:
		frappe.throw(_("Save the Repair Order before creating job cards"))
	ro.check_permission("write")
	frappe.has_permission("Job Card", "create", throw=True)
	require_entry_gate_pass(
		vehicle_unit=ro.vehicle_unit,
		repair_order=ro.name,
		customer=ro.customer,
		context=_("Job Card creation"),
	)

	plan = build_plan(ro, selected_charge_rows)
	created = []
	skipped = []

	for line in plan["lines"]:
		if line.get("existing_job_card"):
			skipped.append(
				{"charge_row": line.get("charge_row") or "", "job_card": line["existing_job_card"]},
			)
			continue

		jc = frappe.new_doc("Job Card")
		jc.repair_order = ro.name
		jc.customer = ro.customer
		jc.vehicle_unit = ro.vehicle_unit
		jc.plate_no = ro.plate_no
		ps = get_datetime(line["planned_start"])
		pe = get_datetime(line["planned_end"])
		jc.repair_date = getdate(ps)
		jc.start_time = ps
		jc.end_time = pe
		jc.repair_type = ro.repair_type
		jc.status = "Open"
		jc.service_charge_row = line.get("charge_row") or ""
		jc.work_area = line.get("work_area")
		jc.technician_skills_group = line.get("technician_skills_group")
		jc.technician = line.get("technician")
		summary_bits = [str(getdate(ps)), f"{ps.strftime('%H:%M')}–{pe.strftime('%H:%M')}"]
		if line.get("work_area"):
			summary_bits.append(line["work_area"])
		if line.get("technician"):
			summary_bits.append(line["technician"])
		jc.planning_summary = " · ".join(summary_bits)[:240]

		for detail in line.get("work_details") or []:
			jc.append(
				"work_details",
				{
					"work_description": (detail.get("description") or _("Service"))[:140],
					"status": "Pending",
					"hours_spent": 0,
					"standard_hours": detail.get("standard_hours") or 0,
				},
			)

		jc.insert()
		created.append(jc.name)

	return {"created": created, "skipped": skipped, "plan": plan}


def planning_settings_payload(settings) -> dict:
	return {
		"auto_assign_work_area": bool(getattr(settings, "auto_assign_work_area", None)),
		"auto_assign_technician": bool(getattr(settings, "auto_assign_technician", None)),
		"respect_work_area_capacity": bool(getattr(settings, "respect_work_area_capacity", None)),
		"respect_technician_load": bool(getattr(settings, "respect_technician_load", None)),
		"allow_overlapping_schedules": bool(getattr(settings, "allow_overlapping_schedules", None)),
		"planning_max_extra_days": cint(getattr(settings, "planning_max_extra_days", None) or 0),
		"planning_work_area_full": getattr(settings, "planning_work_area_full", None) or "warn_only",
		"planning_past_shop_close": getattr(settings, "planning_past_shop_close", None) or "warn_only",
		"planning_technician_overlap": getattr(settings, "planning_technician_overlap", None) or "warn_only",
	}
