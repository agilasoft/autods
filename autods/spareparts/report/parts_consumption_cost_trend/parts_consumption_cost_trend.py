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
		{"fieldname": "repair_order_count", "label": _("Repair Orders"), "fieldtype": "Int", "width": 110},
		{"fieldname": "total_parts_amount", "label": _("Total Parts Cost"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_qty", "label": _("Total Qty"), "fieldtype": "Float", "width": 100},
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
	period = filters.get("period") or "Monthly"
	if period == "Yearly":
		group_expr = "year(r.repair_date)"
	else:
		group_expr = "date_format(r.repair_date, '%%Y-%%m')"
	query = f"""
		select
			{group_expr} as period,
			count(distinct p.parent) as repair_order_count,
			sum(ifnull(p.amount, 0)) as total_parts_amount,
			sum(p.qty) as total_qty
		from `tabRepair Order Parts` p
		inner join `tabRepair Order` r on r.name = p.parent
		where {where}
		group by {group_expr}
		order by period desc
	"""
	return frappe.db.sql(query, values, as_dict=1)
