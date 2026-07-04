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
	labels = [d.get("service_type") or _("(Not Set)") for d in data]
	service = [float(d.get("total_service") or 0) for d in data]
	parts = [float(d.get("total_parts") or 0) for d in data]
	sundry = [float(d.get("total_sundry") or 0) for d in data]
	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Service"), "values": service},
				{"name": _("Parts"), "values": parts},
				{"name": _("Sundry"), "values": sundry},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
		"axisOptions": {"shortenYAxisNumbers": 1},
		"height": 300,
	}


def get_columns():
	return [
		{"fieldname": "service_type", "label": _("Service Type"), "fieldtype": "Link", "options": "Service Type", "width": 160},
		{"fieldname": "order_count", "label": _("Orders"), "fieldtype": "Int", "width": 80},
		{"fieldname": "total_service", "label": _("Total Service"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_parts", "label": _("Total Parts"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_sundry", "label": _("Total Sundry"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "grand_total", "label": _("Grand Total"), "fieldtype": "Currency", "width": 120},
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
	if filters.get("service_type"):
		conditions.append("r.service_type = %(service_type)s")
		values["service_type"] = filters["service_type"]
	where = " and ".join(conditions)
	query = f"""
		select
			r.service_type,
			count(*) as order_count,
			sum(ifnull(r.total_service_items_amount, 0)) as total_service,
			sum(ifnull(r.total_parts_amount, 0)) as total_parts,
			sum(ifnull(r.total_sundry_items_amount, 0)) as total_sundry,
			sum(ifnull(r.grand_total, 0)) as grand_total,
			round(avg(ifnull(r.grand_total, 0)), 2) as avg_order_value
		from `tabRepair Order` r
		where {where}
		group by r.service_type
		order by grand_total desc
	"""
	return frappe.db.sql(query, values, as_dict=1)
