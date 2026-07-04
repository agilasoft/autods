# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	return columns, data, None, chart


def get_chart(data):
	if not data:
		return None
	labels = [d.get("bill_type") or _("(Not Set)") for d in data]
	values = [float(d.get("total_amount") or 0) for d in data]
	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Total Amount"), "values": values}],
		},
		"type": "donut",
		"height": 300,
	}


def get_columns():
	return [
		{"fieldname": "bill_type", "label": _("Bill Type"), "fieldtype": "Data", "width": 120},
		{"fieldname": "order_count", "label": _("Repair Orders"), "fieldtype": "Int", "width": 110},
		{"fieldname": "total_qty", "label": _("Total Qty"), "fieldtype": "Float", "width": 100},
		{"fieldname": "total_amount", "label": _("Total Amount"), "fieldtype": "Currency", "width": 120},
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
	if filters.get("bill_type"):
		conditions.append("p.bill_type = %(bill_type)s")
		values["bill_type"] = filters["bill_type"]
	where = " and ".join(conditions)
	query = f"""
		select
			p.bill_type,
			count(distinct p.parent) as order_count,
			sum(p.qty) as total_qty,
			sum(ifnull(p.amount, 0)) as total_amount
		from `tabRepair Order Charges` p
		inner join `tabRepair Order` r on r.name = p.parent
		where p.service_item_type = 'Spareparts' and {where}
		group by p.bill_type
		order by total_amount desc
	"""
	return frappe.db.sql(query, values, as_dict=1)
