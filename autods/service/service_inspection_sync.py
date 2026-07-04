# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe

SI_RO_FIELDS = ["name", "inspection_name", "status", "inspection_date", "inspected_by", "remarks"]


def map_si_status_to_ro(status):
	status = (status or "").strip()
	if status == "Draft":
		return "Pending"
	if status in ("Pending", "In Progress", "Completed", "Rejected"):
		return status
	return "Pending"


def map_user_to_employee(user):
	if not user:
		return None
	if frappe.db.exists("Employee", user):
		return user
	return frappe.db.get_value("Employee", {"user_id": user}, "name")


def get_ro_row_values_from_si(si_doc):
	"""Map Service Inspection fields to Repair Order quality_inspections row values."""
	inspected_by = map_user_to_employee(getattr(si_doc, "inspected_by", None))
	return {
		"inspection_name": (si_doc.inspection_name or "").strip(),
		"quality_inspection": si_doc.name,
		"status": map_si_status_to_ro(si_doc.status),
		"inspection_date": si_doc.inspection_date,
		"inspected_by": inspected_by,
		"remarks": si_doc.remarks,
	}


def find_service_inspection(repair_order, inspection_name):
	if not repair_order or not inspection_name:
		return None
	inspection_name = (inspection_name or "").strip()
	if not inspection_name:
		return None
	si = frappe.db.get_value(
		"Service Inspection",
		{"repair_order": repair_order, "inspection_name": inspection_name},
		SI_RO_FIELDS,
		as_dict=True,
	)
	if not si:
		return None
	si.status = map_si_status_to_ro(si.status)
	si.inspected_by = map_user_to_employee(si.inspected_by)
	return si


def apply_si_to_ro_row(row, si):
	if not si:
		return
	row.quality_inspection = si.name
	row.status = map_si_status_to_ro(si.status)
	if si.inspection_date:
		row.inspection_date = si.inspection_date
	employee = map_user_to_employee(getattr(si, "inspected_by", None))
	if employee:
		row.inspected_by = employee
	if si.remarks:
		row.remarks = si.remarks


def sync_repair_order_inspection_links(repair_order_doc):
	"""Match quality_inspections rows to Service Inspection docs by inspection_name."""
	if not repair_order_doc.name or frappe.flags.in_service_inspection_ro_sync:
		return

	inspections = frappe.get_all(
		"Service Inspection",
		filters={"repair_order": repair_order_doc.name},
		fields=SI_RO_FIELDS,
	)
	by_name = {si.inspection_name: si for si in inspections if si.inspection_name}

	for row in repair_order_doc.quality_inspections or []:
		if not row.inspection_name:
			continue
		si = by_name.get(row.inspection_name)
		if si:
			apply_si_to_ro_row(row, si)


def link_service_inspection_to_repair_order(si_doc):
	"""Update or create the matching quality_inspections row on the Repair Order."""
	if frappe.flags.in_service_inspection_ro_sync:
		return
	if not si_doc.repair_order or not si_doc.inspection_name:
		return

	frappe.flags.in_service_inspection_ro_sync = True
	try:
		values = get_ro_row_values_from_si(si_doc)
		child = frappe.db.get_value(
			"Repair Order Service Inspection",
			{
				"parent": si_doc.repair_order,
				"parenttype": "Repair Order",
				"inspection_name": values["inspection_name"],
			},
			"name",
		)
		if child:
			frappe.db.set_value(
				"Repair Order Service Inspection",
				child,
				values,
				update_modified=False,
			)
		else:
			ro = frappe.get_doc("Repair Order", si_doc.repair_order)
			ro.append("quality_inspections", values)
			ro.flags.ignore_validate = True
			ro.save(ignore_permissions=True)
	finally:
		frappe.flags.in_service_inspection_ro_sync = False
