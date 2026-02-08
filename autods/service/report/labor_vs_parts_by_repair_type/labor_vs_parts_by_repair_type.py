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
		{"fieldname": "repair_type", "label": _("Repair Type"), "fieldtype": "Link", "options": "Repair Type", "width": 140},
		{"fieldname": "order_count", "label": _("Orders"), "fieldtype": "Int", "width": 80},
		{"fieldname": "total_service", "label": _("Total Service/Labor"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_parts", "label": _("Total Parts"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_sundry", "label": _("Total Sundry"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "grand_total", "label": _("Grand Total"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "service_pct", "label": _("Service %"), "fieldtype": "Percent", "width": 90},
		{"fieldname": "parts_pct", "label": _("Parts %"), "fieldtype": "Percent", "width": 90},
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
	query = f"""
		select
			r.repair_type,
			count(*) as order_count,
			sum(ifnull(r.total_service_items_amount, 0)) as total_service,
			sum(ifnull(r.total_parts_amount, 0)) as total_parts,
			sum(ifnull(r.total_sundry_items_amount, 0)) as total_sundry,
			sum(ifnull(r.grand_total, 0)) as grand_total
		from `tabRepair Order` r
		where {where}
		group by r.repair_type
		order by grand_total desc
	"""
	rows = frappe.db.sql(query, values, as_dict=1)
	for r in rows:
		gt = (r.grand_total or 0)
		r.service_pct = round(100 * (r.total_service or 0) / gt, 1) if gt else 0
		r.parts_pct = round(100 * (r.total_parts or 0) / gt, 1) if gt else 0
	return rows
