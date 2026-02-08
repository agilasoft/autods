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
		{"fieldname": "name", "label": _("Repair Order"), "fieldtype": "Link", "options": "Repair Order", "width": 130},
		{"fieldname": "repair_date", "label": _("Repair Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 140},
		{"fieldname": "vehicle_unit", "label": _("Vehicle Unit"), "fieldtype": "Link", "options": "Vehicle Unit", "width": 130},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "service_order_type", "label": _("Order Type"), "fieldtype": "Link", "options": "Service Order Type", "width": 120},
		{"fieldname": "repair_type", "label": _("Repair Type"), "fieldtype": "Link", "options": "Repair Type", "width": 100},
		{"fieldname": "grand_total", "label": _("Grand Total"), "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = ["r.docstatus >= 0"]
	values = {}
	if filters.get("from_date"):
		conditions.append("r.repair_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("r.repair_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("customer"):
		conditions.append("r.customer = %(customer)s")
		values["customer"] = filters["customer"]
	if filters.get("status"):
		conditions.append("r.status = %(status)s")
		values["status"] = filters["status"]
	where = " and " + " and ".join(conditions)
	query = f"""
		select
			r.name,
			r.repair_date,
			r.customer,
			r.vehicle_unit,
			r.status,
			r.service_order_type,
			r.repair_type,
			r.grand_total
		from `tabRepair Order` r
		where {where}
		order by r.repair_date desc, r.modified desc
	"""
	return frappe.db.sql(query, values, as_dict=1)
