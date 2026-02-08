# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import date


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "name", "label": _("Repair Order"), "fieldtype": "Link", "options": "Repair Order", "width": 130},
		{"fieldname": "repair_date", "label": _("Repair Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "days_open", "label": _("Days Open"), "fieldtype": "Int", "width": 90},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 140},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "repair_type", "label": _("Repair Type"), "fieldtype": "Link", "options": "Repair Type", "width": 100},
		{"fieldname": "expected_completion_date", "label": _("Expected Completion"), "fieldtype": "Datetime", "width": 140},
		{"fieldname": "grand_total", "label": _("Grand Total"), "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = ["r.docstatus in (0, 1)", "r.status not in ('Completed', 'Cancelled')"]
	values = {}
	if filters.get("customer"):
		conditions.append("r.customer = %(customer)s")
		values["customer"] = filters["customer"]
	if filters.get("min_days"):
		conditions.append("r.repair_date <= date_sub(curdate(), interval %(min_days)s day)")
		values["min_days"] = int(filters["min_days"])
	where = " and ".join(conditions)
	query = f"""
		select
			r.name,
			r.repair_date,
			datediff(curdate(), r.repair_date) as days_open,
			r.customer,
			r.status,
			r.repair_type,
			r.expected_completion_date,
			r.grand_total
		from `tabRepair Order` r
		where {where}
		order by days_open desc, r.repair_date asc
	"""
	return frappe.db.sql(query, values, as_dict=1)
