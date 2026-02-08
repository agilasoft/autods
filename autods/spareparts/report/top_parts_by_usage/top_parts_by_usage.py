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
		{"fieldname": "item", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 140},
		{"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 200},
		{"fieldname": "total_qty", "label": _("Total Qty"), "fieldtype": "Float", "width": 100},
		{"fieldname": "total_amount", "label": _("Total Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "order_count", "label": _("Repair Orders"), "fieldtype": "Int", "width": 110},
		{"fieldname": "rank", "label": _("Rank"), "fieldtype": "Int", "width": 70},
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
	limit = int(filters.get("top_n") or 25)
	where = " and ".join(conditions)
	query = """
		select
			p.item,
			max(p.item_name) as item_name,
			sum(p.qty) as total_qty,
			sum(ifnull(p.amount, 0)) as total_amount,
			count(distinct p.parent) as order_count
		from `tabRepair Order Parts` p
		inner join `tabRepair Order` r on r.name = p.parent
		where """ + where + """
		group by p.item
		order by total_qty desc, total_amount desc
		limit %(limit)s
	"""
	values["limit"] = limit
	rows = frappe.db.sql(query, values, as_dict=1)
	for i, r in enumerate(rows, 1):
		r.rank = i
	return rows
