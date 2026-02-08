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
			"fieldname": "order_number",
			"label": _("Order Number"),
			"fieldtype": "Link",
			"options": "Repair Order",
			"width": 150
		},
		{
			"fieldname": "repair_date",
			"label": _("Repair Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "service_item",
			"label": _("Service Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 150
		},
		{
			"fieldname": "service_category",
			"label": _("Service Category"),
			"fieldtype": "Link",
			"options": "Service Category",
			"width": 150
		},
		{
			"fieldname": "technician",
			"label": _("Technician"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120
		},
		{
			"fieldname": "hours",
			"label": _("Hours"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "rate",
			"label": _("Rate"),
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"fieldname": "amount",
			"label": _("Amount"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "bill_type",
			"label": _("Bill Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "revenue_per_hour",
			"label": _("Revenue per Hour"),
			"fieldtype": "Currency",
			"width": 120
		}
	]


def get_data(filters):
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT 
			ro.name as order_number,
			ro.repair_date,
			rosi.service_item,
			rosi.service_category,
			COALESCE(rosi.technician, rosi.technician_painter) as technician,
			rosi.hours,
			rosi.rate,
			rosi.amount,
			rosi.bill_type,
			ro.customer,
			CASE 
				WHEN rosi.hours > 0 THEN rosi.amount / rosi.hours 
				ELSE 0 
			END as revenue_per_hour
		FROM `tabRepair Order` ro
		INNER JOIN `tabRepair Order Service Items` rosi ON rosi.parent = ro.name
		WHERE {conditions}
		ORDER BY ro.repair_date DESC, ro.name DESC, rosi.service_item
	"""
	
	return frappe.db.sql(query, as_dict=1)


def get_conditions(filters):
	conditions = ["ro.docstatus = 1"]
	
	if filters.get("from_date"):
		conditions.append(f"ro.repair_date >= '{filters.get('from_date')}'")
	
	if filters.get("to_date"):
		conditions.append(f"ro.repair_date <= '{filters.get('to_date')}'")
	
	if filters.get("service_item"):
		conditions.append(f"rosi.service_item = '{filters.get('service_item')}'")
	
	if filters.get("service_category"):
		conditions.append(f"rosi.service_category = '{filters.get('service_category')}'")
	
	if filters.get("technician"):
		conditions.append(f"(rosi.technician = '{filters.get('technician')}' OR rosi.technician_painter = '{filters.get('technician')}')")
	
	if filters.get("customer"):
		conditions.append(f"ro.customer = '{filters.get('customer')}'")
	
	return " AND ".join(conditions) if conditions else "1=1"
