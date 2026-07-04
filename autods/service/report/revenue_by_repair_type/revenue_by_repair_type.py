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
	labels = [d.get("repair_type") or _("(Not Set)") for d in data]
	values = [float(d.get("grand_total") or 0) for d in data]
	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Total Revenue"), "values": values}],
		},
		"type": "bar",
		"axisOptions": {"shortenYAxisNumbers": 1},
		"height": 300,
		"colors": ["#29cd42"],
	}


def get_columns():
	return [
		{"fieldname": "repair_type", "label": _("Repair Type"), "fieldtype": "Link", "options": "Repair Type", "width": 140},
		{"fieldname": "order_count", "label": _("Orders"), "fieldtype": "Int", "width": 80},
		{"fieldname": "grand_total", "label": _("Total Revenue"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "avg_order_value", "label": _("Avg Order Value"), "fieldtype": "Currency", "width": 120},
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
	if filters.get("repair_type"):
		conditions.append("r.repair_type = %(repair_type)s")
		values["repair_type"] = filters["repair_type"]
	where = " and ".join(conditions)
	query = (
		"select r.repair_type, count(*) as order_count, sum(ifnull(r.grand_total, 0)) as grand_total, "
		"round(avg(ifnull(r.grand_total, 0)), 2) as avg_order_value from `tabRepair Order` r "
		"where " + where + " group by r.repair_type order by grand_total desc"
	)
	return frappe.db.sql(query, values, as_dict=1)
