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
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "vehicle_unit",
			"label": _("Vehicle Unit"),
			"fieldtype": "Link",
			"options": "Vehicle Unit",
			"width": 120
		},
		{
			"fieldname": "plate_no",
			"label": _("Plate No"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "total_orders",
			"label": _("Total Orders"),
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
			"fieldname": "last_repair_date",
			"label": _("Last Repair Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "first_repair_date",
			"label": _("First Repair Date"),
			"fieldtype": "Date",
			"width": 120
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
		},
		{
			"fieldname": "preferred_repair_type",
			"label": _("Preferred Repair Type"),
			"fieldtype": "Link",
			"options": "Repair Type",
			"width": 150
		}
	]


def get_data(filters):
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT 
			ro.customer,
			ro.vehicle_unit,
			ro.plate_no,
			COUNT(DISTINCT ro.name) as total_orders,
			SUM(COALESCE(rosi.amount, 0) + COALESCE(rop.amount, 0) + COALESCE(rosu.amount, 0)) as total_revenue,
			SUM(COALESCE(rosi.amount, 0) + COALESCE(rop.amount, 0) + COALESCE(rosu.amount, 0)) / 
				NULLIF(COUNT(DISTINCT ro.name), 0) as avg_order_value,
			MAX(ro.repair_date) as last_repair_date,
			MIN(ro.repair_date) as first_repair_date,
			SUM(COALESCE(rosi.amount, 0)) as service_items_revenue,
			SUM(COALESCE(rop.amount, 0)) as parts_revenue,
			SUM(COALESCE(rosu.amount, 0)) as sundry_items_revenue,
			(SELECT repair_type 
			 FROM `tabRepair Order` ro2 
			 WHERE ro2.customer = ro.customer 
			   AND ro2.docstatus = 1
			 GROUP BY repair_type 
			 ORDER BY COUNT(*) DESC 
			 LIMIT 1) as preferred_repair_type
		FROM `tabRepair Order` ro
		LEFT JOIN `tabRepair Order Service Items` rosi ON rosi.parent = ro.name
		LEFT JOIN `tabRepair Order Parts` rop ON rop.parent = ro.name
		LEFT JOIN `tabRepair Order Sundry Items` rosu ON rosu.parent = ro.name
		WHERE {conditions}
		GROUP BY ro.customer, ro.vehicle_unit, ro.plate_no
		ORDER BY total_revenue DESC
	"""
	
	return frappe.db.sql(query, as_dict=1)


def get_conditions(filters):
	conditions = ["ro.docstatus = 1"]
	
	if filters.get("customer"):
		conditions.append(f"ro.customer = '{filters.get('customer')}'")
	
	if filters.get("from_date"):
		conditions.append(f"ro.repair_date >= '{filters.get('from_date')}'")
	
	if filters.get("to_date"):
		conditions.append(f"ro.repair_date <= '{filters.get('to_date')}'")
	
	if filters.get("vehicle_unit"):
		conditions.append(f"ro.vehicle_unit = '{filters.get('vehicle_unit')}'")
	
	return " AND ".join(conditions) if conditions else "1=1"
