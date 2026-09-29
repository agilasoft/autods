# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def _charge_rows(ro):
	return list(getattr(ro, "charges", None) or [])


def iter_service_charge_rows(ro):
	"""Repair Order charge rows with Service item type, in document order."""
	for r in _charge_rows(ro):
		if (r.service_item_type or "").strip() == "Service":
			yield r


def service_line_index_for_charge_row_name(ro, charge_row_name: str | None) -> int | None:
	"""1-based index among Service lines for the charge child row `name`."""
	if not charge_row_name:
		return None
	for i, r in enumerate(iter_service_charge_rows(ro), start=1):
		if r.name == charge_row_name:
			return i
	return None


def service_row_index(value) -> int | None:
	"""Parse the leading service index from a charges `service_row` value.

	Accepts legacy values like ``\"1\"`` and labeled values like ``\"1: Oil change\"``.
	"""
	s = (value or "").strip()
	if not s:
		return None
	i = 0
	while i < len(s) and s[i].isdigit():
		i += 1
	if i == 0:
		return None
	return int(s[:i])


def _service_row_label(doc, service_row, index: int) -> str:
	nm = (getattr(service_row, "item_name", None) or getattr(service_row, "item", None) or "").strip()
	if not nm:
		nm = _("Service {0}").format(index)
	return f"{index}: {nm}"


def sync_service_row_label(doc, row) -> None:
	"""Update ``service_row`` display label from ``parent_service_charge``."""
	parent = (getattr(row, "parent_service_charge", None) or "").strip()
	if not parent:
		return
	for i, svc in enumerate(iter_service_charge_rows(doc), start=1):
		if svc.name == parent:
			row.service_row = _service_row_label(doc, svc, i)
			return


def bind_charge_service_link(row, services, n_svc: int) -> None:
	"""Bind a Spareparts/Overhead row to a Service line.

	Prefer a valid ``parent_service_charge`` (stable across Service reorder) and
	refresh the ``service_row`` label from that parent. Only parse/bind from the
	``service_row`` ordinal when parent is missing or orphaned.
	"""
	if n_svc < 1:
		frappe.throw(_("Add at least one Service line before Spareparts or Overhead."))

	parent = (getattr(row, "parent_service_charge", None) or "").strip()
	if parent:
		for i, svc in enumerate(services, start=1):
			if svc.name == parent:
				row.service_row = _service_row_label(None, svc, i)
				return

	sr = (getattr(row, "service_row", None) or "").strip()
	if not sr:
		frappe.throw(_("Service is required for Spareparts and Overhead lines."))
	idx = service_row_index(sr)
	if idx is None:
		frappe.throw(_("Service must start with a number between 1 and {0}.").format(max(n_svc, 1)))
	if idx < 1 or idx > n_svc:
		frappe.throw(_("Service must be between 1 and {0} (Service lines in this document).").format(n_svc))
	row.parent_service_charge = services[idx - 1].name
	row.service_row = _service_row_label(None, services[idx - 1], idx)


def resolve_charge_parent_service_links(doc) -> None:
	"""Resolve ``service_row`` index values to ``parent_service_charge`` and refresh labels."""
	services = list(iter_service_charge_rows(doc))
	n_svc = len(services)
	if not n_svc:
		return
	for row in _charge_rows(doc):
		t = (row.service_item_type or "").strip()
		if t not in ("Spareparts", "Overhead"):
			continue
		has_sr = bool((getattr(row, "service_row", None) or "").strip())
		has_parent = bool((getattr(row, "parent_service_charge", None) or "").strip())
		if not has_sr and not has_parent:
			continue
		try:
			bind_charge_service_link(row, services, n_svc)
		except frappe.ValidationError:
			continue


def persist_charge_service_links(doc, child_doctype: str) -> None:
	"""Write resolved service links on charge child rows (after insert name finalization)."""
	resolve_charge_parent_service_links(doc)
	for row in _charge_rows(doc):
		t = (row.service_item_type or "").strip()
		if t not in ("Spareparts", "Overhead") or not row.name:
			continue
		frappe.db.set_value(
			child_doctype,
			row.name,
			{
				"parent_service_charge": getattr(row, "parent_service_charge", None) or "",
				"service_row": getattr(row, "service_row", None) or "",
			},
			update_modified=False,
		)


def validate_charge_service_links(doc) -> None:
	"""Validate unified charges: sparepart/overhead service links."""
	services = list(iter_service_charge_rows(doc))
	n_svc = len(services)

	for row in _charge_rows(doc):
		t = (row.service_item_type or "").strip()
		if t == "Service":
			row.service_row = ""
			row.parent_service_charge = ""
			continue
		if t not in ("Spareparts", "Overhead"):
			continue
		bind_charge_service_link(row, services, n_svc)


def sparepart_linked_to_service(spare_row, service_charge_row_name: str | None, service_idx: int | None) -> bool:
	"""Whether a sparepart row belongs to the given service line."""
	parent = (getattr(spare_row, "parent_service_charge", None) or "").strip()
	if parent and service_charge_row_name:
		return parent == service_charge_row_name
	if service_idx is not None:
		return service_row_index(getattr(spare_row, "service_row", None)) == service_idx
	return False


def sparepart_rows_for_material_request(
	ro,
	service_charge_row_name: str | None = None,
	explicit_charge_row_names: list[str] | None = None,
):
	"""Return Repair Order charge rows (Spareparts) to put on a Material Request.

	- If ``explicit_charge_row_names`` is set, only those rows (must be Spareparts on ``ro``).
	- Else if ``service_charge_row_name`` is set, only spareparts linked to that service line.
	- Else all Spareparts lines on the document (legacy behaviour).
	"""
	spare = [r for r in _charge_rows(ro) if (r.service_item_type or "").strip() == "Spareparts"]
	if explicit_charge_row_names:
		want = {str(x) for x in explicit_charge_row_names if x}
		return [r for r in spare if r.name in want]
	idx = service_line_index_for_charge_row_name(ro, service_charge_row_name)
	if service_charge_row_name or idx is not None:
		return [
			r
			for r in spare
			if sparepart_linked_to_service(r, service_charge_row_name, idx)
		]
	return spare
