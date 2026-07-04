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
		{"fieldname": "service_type", "label": _("Service Type"), "fieldtype": "Link", "options": "Service Type", "width": 120},
		{"fieldname": "repair_type", "label": _("Repair Type"), "fieldtype": "Link", "options": "Repair Type", "width": 100},
		{"fieldname": "total_service_amount", "label": _("Service Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_parts_amount", "label": _("Parts Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_sundry_amount", "label": _("Sundry Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "grand_total", "label": _("Grand Total"), "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = ["r.docstatus = 1"]
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
	if filters.get("repair_type"):
		conditions.append("r.repair_type = %(repair_type)s")
		values["repair_type"] = filters["repair_type"]
	if filters.get("service_type"):
		conditions.append("r.service_type = %(service_type)s")
		values["service_type"] = filters["service_type"]
	where = " and ".join(conditions)
	query = f"""
		select
			r.name,
			r.repair_date,
			r.customer,
			r.service_type,
			r.repair_type,
			ifnull(r.total_service_items_amount, 0) as total_service_amount,
			ifnull(r.total_parts_amount, 0) as total_parts_amount,
			ifnull(r.total_sundry_items_amount, 0) as total_sundry_amount,
			ifnull(r.grand_total, 0) as grand_total
		from `tabRepair Order` r
		where {where}
		order by r.repair_date desc, r.modified desc
	"""
	return frappe.db.sql(query, values, as_dict=1)
