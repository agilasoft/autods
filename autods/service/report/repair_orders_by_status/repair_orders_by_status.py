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
	labels = [d.get("status") or _("(Not Set)") for d in data]
	counts = [d.get("order_count") or 0 for d in data]
	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Repair Orders"), "values": counts}],
		},
		"type": "donut",
		"height": 300,
	}


def get_columns():
	return [
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "order_count", "label": _("Repair Orders"), "fieldtype": "Int", "width": 120},
		{"fieldname": "total_value", "label": _("Total Value"), "fieldtype": "Currency", "width": 120},
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
	if filters.get("status"):
		conditions.append("r.status = %(status)s")
		values["status"] = filters["status"]
	where = " and ".join(conditions)
	query = (
		"select r.status, count(*) as order_count, sum(ifnull(r.grand_total, 0)) as total_value "
		"from `tabRepair Order` r where " + where + " group by r.status order by order_count desc"
	)
	return frappe.db.sql(query, values, as_dict=1)
