# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "name", "label": _("Job Card"), "fieldtype": "Link", "options": "Job Card", "width": 120},
		{"fieldname": "repair_order", "label": _("Repair Order"), "fieldtype": "Link", "options": "Repair Order", "width": 130},
		{"fieldname": "repair_date", "label": _("Repair Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 140},
		{"fieldname": "vehicle_unit", "label": _("Vehicle Unit"), "fieldtype": "Link", "options": "Vehicle Unit", "width": 130},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "technician", "label": _("Technician"), "fieldtype": "Link", "options": "Employee", "width": 120},
		{"fieldname": "work_area", "label": _("Work Area"), "fieldtype": "Link", "options": "Work Area", "width": 100},
	]


def get_data(filters):
	conditions = ["j.docstatus >= 0"]
	values = {}
	if filters.get("from_date"):
		conditions.append("j.repair_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("j.repair_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("status"):
		conditions.append("j.status = %(status)s")
		values["status"] = filters["status"]
	if filters.get("repair_order"):
		conditions.append("j.repair_order = %(repair_order)s")
		values["repair_order"] = filters["repair_order"]
	where = " and " + " and ".join(conditions)
	query = f"""
		select
			j.name,
			j.repair_order,
			j.repair_date,
			j.customer,
			j.vehicle_unit,
			j.status,
			j.technician,
			j.work_area
		from `tabJob Card` j
		where {where}
		order by j.repair_date desc, j.modified desc
	"""
	return frappe.db.sql(query, values, as_dict=1)
