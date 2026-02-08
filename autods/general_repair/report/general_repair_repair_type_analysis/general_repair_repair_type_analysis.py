# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "repair_type",
			"label": _("Repair Type"),
			"fieldtype": "Link",
			"options": "Repair Type",
			"width": 150
		},
		{
			"fieldname": "order_count",
			"label": _("Order Count"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "total_revenue",
			"label": _("Total Revenue"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "avg_order_value",
			"label": _("Average Order Value"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "service_items_revenue",
			"label": _("Service Items Revenue"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "parts_revenue",
			"label": _("Parts Revenue"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "sundry_items_revenue",
			"label": _("Sundry Items Revenue"),
			"fieldtype": "Currency",
			"width": 150
		}
	]


def get_data(filters):
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT 
			ro.repair_type,
			COUNT(DISTINCT ro.name) as order_count,
			SUM(COALESCE(rosi.amount, 0) + COALESCE(rop.amount, 0) + COALESCE(rosu.amount, 0)) as total_revenue,
			SUM(COALESCE(rosi.amount, 0) + COALESCE(rop.amount, 0) + COALESCE(rosu.amount, 0)) / 
				NULLIF(COUNT(DISTINCT ro.name), 0) as avg_order_value,
			SUM(COALESCE(rosi.amount, 0)) as service_items_revenue,
			SUM(COALESCE(rop.amount, 0)) as parts_revenue,
			SUM(COALESCE(rosu.amount, 0)) as sundry_items_revenue
		FROM `tabRepair Order` ro
		LEFT JOIN `tabRepair Order Service Items` rosi ON rosi.parent = ro.name
		LEFT JOIN `tabRepair Order Parts` rop ON rop.parent = ro.name
		LEFT JOIN `tabRepair Order Sundry Items` rosu ON rosu.parent = ro.name
		WHERE {conditions}
		GROUP BY ro.repair_type
		ORDER BY total_revenue DESC
	"""
	
	return frappe.db.sql(query, as_dict=1)


def get_conditions(filters):
	conditions = ["ro.docstatus = 1", "ro.repair_type IS NOT NULL"]
	
	if filters.get("from_date"):
		conditions.append(f"ro.repair_date >= '{filters.get('from_date')}'")
	
	if filters.get("to_date"):
		conditions.append(f"ro.repair_date <= '{filters.get('to_date')}'")
	
	if filters.get("repair_type"):
		conditions.append(f"ro.repair_type = '{filters.get('repair_type')}'")
	
	return " AND ".join(conditions) if conditions else "1=1"
