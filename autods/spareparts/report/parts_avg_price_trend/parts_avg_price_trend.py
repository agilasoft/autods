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
		{"fieldname": "period", "label": _("Period"), "fieldtype": "Data", "width": 120},
		{"fieldname": "total_qty", "label": _("Total Qty"), "fieldtype": "Float", "width": 100},
		{"fieldname": "total_amount", "label": _("Total Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "avg_price", "label": _("Avg Price"), "fieldtype": "Currency", "width": 100},
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
	where = " and ".join(conditions)
	query = (
		"select date_format(r.repair_date, '%%Y-%%m') as period, sum(p.qty) as total_qty, "
		"sum(ifnull(p.amount, 0)) as total_amount, "
		"round(sum(ifnull(p.amount, 0)) / nullif(sum(p.qty), 0), 2) as avg_price "
		"from `tabRepair Order Parts` p inner join `tabRepair Order` r on r.name = p.parent "
		"where " + where + " group by period order by period desc"
	)
	return frappe.db.sql(query, values, as_dict=1)
