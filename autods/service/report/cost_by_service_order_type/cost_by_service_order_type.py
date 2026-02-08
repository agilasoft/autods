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
		{"fieldname": "service_order_type", "label": _("Service Order Type"), "fieldtype": "Link", "options": "Service Order Type", "width": 160},
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
	if filters.get("service_order_type"):
		conditions.append("r.service_order_type = %(service_order_type)s")
		values["service_order_type"] = filters["service_order_type"]
	where = " and ".join(conditions)
	query = f"""
		select
			r.service_order_type,
			count(*) as order_count,
			sum(ifnull(r.total_service_items_amount, 0)) as total_service,
			sum(ifnull(r.total_parts_amount, 0)) as total_parts,
			sum(ifnull(r.total_sundry_items_amount, 0)) as total_sundry,
			sum(ifnull(r.grand_total, 0)) as grand_total,
			round(avg(ifnull(r.grand_total, 0)), 2) as avg_order_value
		from `tabRepair Order` r
		where {where}
		group by r.service_order_type
		order by grand_total desc
	"""
	return frappe.db.sql(query, values, as_dict=1)
