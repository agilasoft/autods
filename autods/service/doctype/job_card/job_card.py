# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, flt, get_datetime, getdate, now, time_diff_in_hours

from autods.service.charge_service_row import (
	service_line_index_for_charge_row_name,
	sparepart_rows_for_material_request,
)
from autods.service.gate_pass_utils import require_entry_gate_pass


class JobCard(Document):
	def before_insert(self):
		self.populate_spareparts_from_charges()

	def validate(self):
		self.sync_expected_completion_from_repair_order()
		self.calculate_total_hours()
		self.set_work_details_total_hours()
		self.set_completion_timestamps()
		self.validate_entry_gate_pass()
		self.validate_vehicle_schedule()

	def sync_expected_completion_from_repair_order(self):
		if not self.repair_order:
			return
		if self.expected_completion_date and self.has_value_changed("expected_completion_date"):
			return
		if not self.expected_completion_date or self.has_value_changed("repair_order"):
			completion = frappe.db.get_value(
				"Repair Order", self.repair_order, "expected_completion_date"
			)
			if completion:
				self.expected_completion_date = completion

	def populate_spareparts_from_charges(self, ro=None):
		"""Copy Repair Order sparepart charge lines (scoped to service_charge_row) into spareparts_requests."""
		if not self.repair_order or not self.service_charge_row:
			return
		if self.spareparts_requests:
			return
		if ro is None:
			ro = frappe.get_doc("Repair Order", self.repair_order)
		for charge_row in sparepart_rows_for_material_request(ro, self.service_charge_row, None):
			row = charge_row_to_jc_spareparts_request_row(charge_row, self.technician)
			if row:
				self.append("spareparts_requests", row)

	def set_work_details_total_hours(self):
		total = 0.0
		for row in self.work_details or []:
			total += flt(row.hours_spent)
		self.work_details_total_hours = total

	def set_completion_timestamps(self):
		if self.status != "Completed":
			return
		if not self.actual_completion_date:
			self.actual_completion_date = now()
		if not self.end_time:
			self.end_time = self.actual_completion_date

	def validate_entry_gate_pass(self):
		if self.status in ("Completed", "Cancelled"):
			return
		if not (self.vehicle_unit or self.customer):
			return
		require_entry_gate_pass(
			vehicle_unit=self.vehicle_unit,
			repair_order=self.repair_order,
			customer=self.customer,
			context=_("Job Card work"),
		)

	def validate_vehicle_schedule(self):
		if self.status in ("Completed", "Cancelled"):
			return
		vehicle_key = self.vehicle_unit or self.plate_no
		if not vehicle_key or not self.repair_date:
			return

		filters = [
			["Job Card", "status", "not in", ("Completed", "Cancelled")],
			["Job Card", "repair_date", "=", getdate(self.repair_date)],
		]
		if self.name:
			filters.append(["Job Card", "name", "!=", self.name])
		if self.vehicle_unit:
			filters.append(["Job Card", "vehicle_unit", "=", self.vehicle_unit])
		else:
			filters.append(["Job Card", "plate_no", "=", self.plate_no])

		existing = frappe.get_all(
			"Job Card",
			filters=filters,
			fields=["name", "start_time", "end_time", "expected_completion_date"],
			limit_page_length=50,
		)
		if not existing:
			return

		start_dt, end_dt = job_card_window(self)
		if not start_dt or not end_dt:
			frappe.throw(
				_("An active Job Card already exists for this vehicle on {0}: {1}").format(
					getdate(self.repair_date),
					frappe.bold(existing[0].name),
				),
			)

		for row in existing:
			row_start, row_end = row_window(row, getdate(self.repair_date))
			if not row_start or not row_end or intervals_overlap(start_dt, end_dt, row_start, row_end):
				frappe.throw(
					_("Job Card {0} already covers this vehicle in the selected repair window.").format(
						frappe.bold(row.name),
					),
				)

	@frappe.whitelist()
	def calculate_total_hours(self):
		"""Calculate total hours from start and end time"""
		if self.start_time and self.end_time:
			start = get_datetime(self.start_time)
			end = get_datetime(self.end_time)
			if end > start:
				self.total_hours = time_diff_in_hours(end, start)
			else:
				frappe.throw(_("End Time must be greater than Start Time"))

	def on_submit(self):
		if self.status != "Completed":
			frappe.db.set_value("Job Card", self.name, "status", "Completed")
			self.status = "Completed"
		if not self.actual_completion_date:
			completed_at = now()
			frappe.db.set_value("Job Card", self.name, "actual_completion_date", completed_at)
			self.actual_completion_date = completed_at
		if not self.end_time:
			frappe.db.set_value("Job Card", self.name, "end_time", self.actual_completion_date)
			self.end_time = self.actual_completion_date

	def on_cancel(self):
		frappe.db.set_value("Job Card", self.name, "status", "Cancelled")
		self.status = "Cancelled"

	@frappe.whitelist()
	def assign_technician_by_skills(self):
		"""Rank active employees by skill coverage, same-skills-group history, bay presence, and daily load."""
		if not self.technician_skills_group:
			frappe.throw(_("Please select Required Skills Group first"))

		skills_group = frappe.get_doc("Technician Skills Group", self.technician_skills_group)
		required_skills = [(skill.skill_name or "").strip() for skill in (skills_group.skills or []) if (skill.skill_name or "").strip()]

		if not required_skills:
			frappe.msgprint(_("No skills defined in the selected skills group"))
			return []

		return rank_technicians_for_job_card(self, required_skills)

	@frappe.whitelist()
	def get_material_request_candidates(self):
		"""Spareparts lines for MR: scoped to this Job Card's service line when possible, else full RO list."""
		if not self.repair_order:
			return {
				"mode": "none",
				"lines": [],
				"fallback_lines": [],
				"message": _("Repair Order is not set on this Job Card."),
			}

		ro = frappe.get_doc("Repair Order", self.repair_order)
		all_spare = sparepart_rows_for_material_request(ro, None, None)
		all_payload = _material_request_line_payloads(ro, all_spare)

		if self.service_charge_row:
			idx = service_line_index_for_charge_row_name(ro, self.service_charge_row)
			if idx is None:
				return {
					"mode": "invalid_service_line",
					"lines": [],
					"fallback_lines": all_payload,
					"message": _(
						"This Job Card's service line is not on the Repair Order. Pick sparepart lines manually or relink the Job Card."
					),
				}
			scoped = sparepart_rows_for_material_request(ro, self.service_charge_row, None)
			scoped_payload = _material_request_line_payloads(ro, scoped)
			if not scoped_payload and all_payload:
				return {
					"mode": "scoped_empty",
					"lines": [],
					"fallback_lines": all_payload,
					"message": _("No spareparts are linked to this Job Card's service line on the Repair Order."),
				}
			return {"mode": "scoped", "lines": scoped_payload, "fallback_lines": [], "message": None}

		return {
			"mode": "picker",
			"lines": all_payload,
			"fallback_lines": [],
			"message": None,
		}

	@frappe.whitelist()
	def create_material_request(self, charge_row_names=None):
		"""Create Material Request (Material Issue) from Job Card. Items from Repair Order spareparts.

		``charge_row_names``: optional list of ``Repair Order Charges`` row names (Spareparts) to include.
		When omitted, spareparts are scoped to :py:attr:`service_charge_row` when set, otherwise all RO spareparts.
		"""
		if not self.name:
			frappe.throw(_("Please save the Job Card first"))
		if not self.repair_order:
			frappe.throw(_("Repair Order is required to create a Material Request"))

		ro = frappe.get_doc("Repair Order", self.repair_order)
		spareparts = resolve_sparepart_charge_rows(ro, self.service_charge_row, charge_row_names)

		if not spareparts:
			frappe.throw(_("Add sparepart lines in the Repair Order Charges table first, or link parts to this service line."))

		material_request = _create_material_request_from_repair_order(
			repair_order=self.repair_order,
			job_card=self.name,
			items=spareparts,
		)
		frappe.msgprint(_("Material Request {0} created for issue.").format(
			frappe.bold(material_request.name)
		))
		return {"doctype": material_request.doctype, "name": material_request.name}

	@frappe.whitelist()
	def create_shopfloor_schedule(self):
		"""Create ShopFloor Schedule from Job Card"""
		if not self.name:
			frappe.throw(_("Please save the Job Card first"))
		if not self.work_area:
			frappe.throw(_("Please select Work Area first"))
		if not self.repair_date:
			frappe.throw(_("Please select Repair Date first"))

		shopfloor_schedule = frappe.new_doc("ShopFloor Schedule")
		shopfloor_schedule.job_card = self.name
		shopfloor_schedule.repair_order = self.repair_order
		shopfloor_schedule.work_area = self.work_area
		shopfloor_schedule.vehicle_unit = self.vehicle_unit
		shopfloor_schedule.plate_no = self.plate_no
		shopfloor_schedule.technician = self.technician
		shopfloor_schedule.scheduled_date = self.repair_date

		start_dt, end_dt = job_card_window(self)
		if start_dt and end_dt:
			shopfloor_schedule.scheduled_date = getdate(start_dt)
			shopfloor_schedule.scheduled_start_time = start_dt.time()
			shopfloor_schedule.scheduled_end_time = end_dt.time()

		shopfloor_schedule.status = "Scheduled"
		shopfloor_schedule.insert()

		frappe.msgprint(_("ShopFloor Schedule {0} created").format(
			frappe.bold(shopfloor_schedule.name)
		))
		return {"doctype": shopfloor_schedule.doctype, "name": shopfloor_schedule.name}

	@frappe.whitelist()
	def check_technician_availability(self, technician, start_date, end_date):
		"""Check if technician is available for the given time period"""
		return check_technician_availability(technician, start_date, end_date, self.name)

	@frappe.whitelist()
	def complete_job_card(self):
		"""Close this Job Card by marking it and its pending work rows Completed."""
		if not self.name:
			frappe.throw(_("Please save the Job Card first"))
		self.status = "Completed"
		if not self.actual_completion_date:
			self.actual_completion_date = now()
		if not self.end_time:
			self.end_time = self.actual_completion_date
		for row in self.work_details or []:
			if row.status != "Completed":
				row.status = "Completed"
		self.save()
		frappe.msgprint(_("Job Card {0} completed.").format(frappe.bold(self.name)))
		return {"doctype": self.doctype, "name": self.name}


def resolve_sparepart_charge_rows(ro, service_charge_row, charge_row_names=None):
	"""Return Repair Order Spareparts charge rows for MR or Job Card spareparts_requests."""
	explicit = _parse_charge_row_names(charge_row_names)
	if explicit is not None:
		if not explicit:
			frappe.throw(_("Select at least one sparepart line."))
		_validate_explicit_sparepart_rows(ro, explicit)
		return sparepart_rows_for_material_request(ro, None, explicit)
	if service_charge_row:
		if service_line_index_for_charge_row_name(ro, service_charge_row) is None:
			frappe.throw(
				_(
					"This Job Card's service line is missing on the Repair Order. Select sparepart lines explicitly or fix the Job Card link."
				)
			)
	return sparepart_rows_for_material_request(ro, service_charge_row, None)


def charge_row_to_jc_spareparts_request_row(charge_row, technician=None):
	"""Map a Repair Order Spareparts charge row to a Job Card Spareparts Request child row."""
	item_code = getattr(charge_row, "item", None)
	if not item_code:
		return None
	item_name = getattr(charge_row, "item_name", None)
	if not item_name:
		item_name = frappe.db.get_value("Item", item_code, "item_name")
	uom = getattr(charge_row, "uom", None) or frappe.db.get_value("Item", item_code, "stock_uom")
	return {
		"item_code": item_code,
		"item_name": item_name,
		"qty": flt(getattr(charge_row, "qty", None)) or 1,
		"uom": uom,
		"requested_by": technician,
		"requested_date": now(),
		"status": "Requested",
	}


def _parse_charge_row_names(charge_row_names):
	if charge_row_names is None or charge_row_names == "":
		return None
	if isinstance(charge_row_names, str):
		charge_row_names = frappe.parse_json(charge_row_names)
	if not isinstance(charge_row_names, (list, tuple)):
		frappe.throw(_("charge_row_names must be a list of Repair Order charge row names."))
	return [str(x) for x in charge_row_names if x]


def _validate_explicit_sparepart_rows(ro, names: list[str]):
	if not names:
		frappe.throw(_("Select at least one sparepart line."))
	valid = {
		r.name
		for r in (ro.get("charges") or [])
		if (getattr(r, "service_item_type", None) or "").strip() == "Spareparts"
	}
	bad = set(names) - valid
	if bad:
		frappe.throw(_("Invalid sparepart row(s): {0}").format(", ".join(sorted(bad))))


def _material_request_line_payloads(ro, rows):
	payloads = []
	for r in rows:
		item_code = getattr(r, "item", None)
		item_name = getattr(r, "item_name", None)
		if not item_name and item_code:
			item_name = frappe.db.get_value("Item", item_code, "item_name")
		payloads.append(
			{
				"name": r.name,
				"item_code": item_code,
				"item_name": item_name,
				"qty": flt(getattr(r, "qty", None)),
				"service_row": getattr(r, "service_row", None) or "",
				"warehouse": getattr(r, "warehouse", None) or "",
			}
		)
	return payloads


def _norm_skill(value: str | None) -> str:
	return (value or "").strip().lower()


def _open_job_count(employee: str, on_date, exclude_job_card: str | None) -> int:
	if not employee or not on_date:
		return 0
	q = """
		SELECT COUNT(*)
		FROM `tabJob Card`
		WHERE technician = %s
		  AND repair_date = %s
		  AND status NOT IN ('Completed', 'Cancelled')
	"""
	params: list = [employee, on_date]
	if exclude_job_card:
		q += " AND name != %s"
		params.append(exclude_job_card)
	return int(frappe.db.sql(q, tuple(params))[0][0] or 0)


def rank_technicians_for_job_card(jc_doc, required_skill_names: list[str]):
	"""Return active employees sorted by fit for ``jc_doc`` and ``required_skill_names``."""
	required_set = {_norm_skill(s) for s in required_skill_names}
	sg = jc_doc.technician_skills_group
	employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name"])
	if not employees:
		return []

	skill_rows = frappe.db.sql(
		"""
		SELECT employee, skill_name FROM `tabEmployee Service Skill`
		WHERE IFNULL(employee, '') != '' AND IFNULL(skill_name, '') != ''
		""",
		as_dict=True,
	)
	by_emp: dict[str, set[str]] = {}
	for sr in skill_rows:
		by_emp.setdefault(sr.employee, set()).add(_norm_skill(sr.skill_name))

	completed_rows = frappe.db.sql(
		"""
		SELECT technician, COUNT(*)
		FROM `tabJob Card`
		WHERE technician_skills_group = %s AND status = %s AND IFNULL(technician, '') != ''
		GROUP BY technician
		""",
		(sg, "Completed"),
	)
	completed = {r[0]: int(r[1] or 0) for r in completed_rows}

	any_group = set(
		frappe.get_all(
			"Job Card",
			filters={"technician_skills_group": sg, "technician": ("is", "set")},
			pluck="technician",
		)
	)

	rd = getdate(jc_doc.repair_date) if jc_doc.repair_date else None
	wa = jc_doc.work_area
	jc_name = jc_doc.name or ""

	bay_counts: dict[str, int] = {}
	if wa and rd:
		q = """
			SELECT technician, COUNT(*)
			FROM `tabJob Card`
			WHERE work_area = %s
			  AND repair_date = %s
			  AND status NOT IN ('Completed', 'Cancelled')
			  AND IFNULL(technician, '') != ''
		"""
		params: list = [wa, rd]
		if jc_name:
			q += " AND name != %s"
			params.append(jc_name)
		q += " GROUP BY technician"
		bay_counts = {r[0]: int(r[1] or 0) for r in frappe.db.sql(q, tuple(params))}

	ranked = []
	for emp in employees:
		eid = emp.name
		emp_skills = by_emp.get(eid, set())
		if required_set and emp_skills:
			coverage = len(required_set & emp_skills) / len(required_set)
		elif required_set:
			if completed.get(eid, 0) > 0:
				coverage = 0.85
			elif eid in any_group:
				coverage = 0.45
			else:
				coverage = 0.0
		else:
			coverage = 1.0

		open_jc = _open_job_count(eid, rd, jc_name) if rd else 0
		bay_other = int(bay_counts.get(eid, 0) or 0)
		score = (
			coverage * 1000.0
			+ min(completed.get(eid, 0), 20) * 5.0
			+ bay_other * 15.0
			- open_jc * 25.0
		)
		ranked.append(
			{
				"employee": eid,
				"employee_name": emp.employee_name or eid,
				"skills_match_pct": round(coverage * 100.0, 1),
				"open_jobs_today": open_jc,
				"bay_jobs_same_area": bay_other,
				"score": round(score, 2),
			}
		)

	ranked.sort(key=lambda r: (-r["score"], r["employee_name"], r["employee"]))
	return ranked


def _create_material_request_from_repair_order(repair_order, job_card, items):
	"""Create Material Request (Material Issue) from Repair Order spareparts. References: job_card, repair_order."""
	from frappe.utils import getdate, nowdate
	try:
		import erpnext
	except ImportError:
		erpnext = None

	material_request = frappe.new_doc("Material Request")
	material_request.material_request_type = "Material Issue"
	material_request.job_card = job_card
	material_request.repair_order = repair_order
	material_request.schedule_date = getdate(nowdate())

	default_warehouse = frappe.db.get_single_value("Service Settings", "default_warehouse")

	# Company from item warehouses so MR company matches (avoid InvalidWarehouseCompany)
	company = None
	companies = set()
	for row in items:
		wh = getattr(row, "warehouse", None) or default_warehouse
		if wh:
			wh_company = frappe.db.get_value("Warehouse", wh, "company")
			if wh_company:
				companies.add(wh_company)
				if company is None:
					company = wh_company
	if len(companies) > 1:
		frappe.throw(_("All item warehouses must belong to the same company. Found: {0}").format(", ".join(companies)))
	if not company:
		company = erpnext.get_default_company() if erpnext else frappe.db.get_single_value("Global Defaults", "default_company")
	if company:
		material_request.company = company

	for row in items:
		item_code = getattr(row, "item", None)
		if not item_code:
			continue
		warehouse = getattr(row, "warehouse", None) or default_warehouse
		if not warehouse and frappe.db.get_value("Item", item_code, "is_stock_item"):
			frappe.throw(
				_("Warehouse is required for stock item {0}. Set a Warehouse on the Repair Order sparepart line or Default Warehouse in Service Settings.").format(
					frappe.bold(item_code),
				),
			)
		uom = getattr(row, "uom", None) or frappe.db.get_value("Item", item_code, "stock_uom")
		material_request.append("items", {
			"item_code": item_code,
			"qty": row.qty or 1,
			"uom": uom,
			"warehouse": warehouse,
			"schedule_date": material_request.schedule_date,
		})

	material_request.insert()
	return material_request


@frappe.whitelist()
def check_technician_availability(technician, start_date, end_date, docname=None):
	"""Check if technician is available for the given time period (module-level for RPC)."""
	if not technician or not start_date or not end_date:
		return {"available": True, "overlapping_jobs": []}

	start_dt = get_datetime(start_date)
	end_dt = get_datetime(end_date)
	if end_dt <= start_dt:
		return {"available": False, "overlapping_jobs": []}

	filters = [
		["Job Card", "technician", "=", technician],
		["Job Card", "repair_date", "=", getdate(start_dt)],
		["Job Card", "status", "not in", ("Completed", "Cancelled")],
	]
	if docname:
		filters.append(["Job Card", "name", "!=", docname])
	jobs = frappe.get_all(
		"Job Card",
		filters=filters,
		fields=["name", "status", "start_time", "end_time", "expected_completion_date"],
	)
	overlapping = []
	for job in jobs:
		job_start, job_end = row_window(job, getdate(start_dt))
		if not job_start or not job_end:
			continue
		if intervals_overlap(start_dt, end_dt, job_start, job_end):
			overlapping.append((job.name, job.status))

	return {
		"available": len(overlapping) == 0,
		"overlapping_jobs": overlapping
	}


def job_card_window(doc):
	if doc.start_time and doc.end_time:
		return get_datetime(doc.start_time), get_datetime(doc.end_time)
	if doc.start_time and doc.expected_completion_date:
		return get_datetime(doc.start_time), get_datetime(doc.expected_completion_date)
	if doc.repair_date and doc.expected_completion_date:
		return get_datetime(f"{getdate(doc.repair_date)} 00:00:00"), get_datetime(doc.expected_completion_date)
	if doc.repair_date:
		start = get_datetime(f"{getdate(doc.repair_date)} 09:00:00")
		return start, add_to_date(start, hours=1)
	return None, None


def row_window(row, repair_date=None):
	if row.start_time and row.end_time:
		return get_datetime(row.start_time), get_datetime(row.end_time)
	if row.start_time and row.expected_completion_date:
		return get_datetime(row.start_time), get_datetime(row.expected_completion_date)
	if repair_date and row.expected_completion_date:
		return get_datetime(f"{getdate(repair_date)} 00:00:00"), get_datetime(row.expected_completion_date)
	return None, None


def intervals_overlap(a0, a1, b0, b1):
	if a0 > a1:
		a0, a1 = a1, a0
	if b0 > b1:
		b0, b1 = b1, b0
	return a0 < b1 and a1 > b0
