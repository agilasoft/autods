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
			"fieldname": "vehicle_id_no",
			"label": _("Vehicle ID No"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "repair_date",
			"label": _("Repair Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "repair_type",
			"label": _("Repair Type"),
			"fieldtype": "Link",
			"options": "Repair Type",
			"width": 120
		},
		{
			"fieldname": "item_type",
			"label": _("Item Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "item_code",
			"label": _("Item/Service"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 150
		},
		{
			"fieldname": "item_name",
			"label": _("Item Name"),
			"fieldtype": "Data",
			"width": 200
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
			"fieldname": "qty",
			"label": _("Qty"),
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
			"fieldname": "bill_to",
			"label": _("Bill To"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 120
		}
	]


def get_data(filters):
	data = []
	conditions = get_conditions(filters)
	
	# Get orders
	orders = frappe.db.sql(f"""
		SELECT 
			ro.name as order_number,
			ro.customer,
			ro.vehicle_unit,
			ro.plate_no,
			ro.vehicle_id_no,
			ro.repair_date,
			ro.repair_type
		FROM `tabRepair Order` ro
		WHERE {conditions}
		ORDER BY ro.repair_date DESC, ro.name DESC
	""", as_dict=1)
	
	for order in orders:
		# Service Items
		service_items = frappe.db.sql("""
			SELECT 
				service_item as item_code,
				(SELECT item_name FROM `tabItem` WHERE name = service_item) as item_name,
				service_category,
				COALESCE(technician, technician_painter) as technician,
				hours,
				1 as qty,
				rate,
				amount,
				bill_type,
				bill_to,
				NULL as warehouse,
				'Service Item' as item_type
			FROM `tabRepair Order Service Items`
			WHERE parent = %s
		""", (order.order_number,), as_dict=1)
		
		# Parts
		parts = frappe.db.sql("""
			SELECT 
				item as item_code,
				item_name,
				NULL as service_category,
				NULL as technician,
				NULL as hours,
				qty,
				rate,
				amount,
				bill_type,
				bill_to,
				warehouse,
				item_type
			FROM `tabRepair Order Parts`
			WHERE parent = %s
		""", (order.order_number,), as_dict=1)
		
		# Sundry Items
		sundry_items = frappe.db.sql("""
			SELECT 
				item as item_code,
				item_name,
				NULL as service_category,
				NULL as technician,
				NULL as hours,
				qty,
				rate,
				amount,
				bill_type,
				bill_to,
				NULL as warehouse,
				'Sundry Item' as item_type
			FROM `tabRepair Order Sundry Items`
			WHERE parent = %s
		""", (order.order_number,), as_dict=1)
		
		# Combine all items
		all_items = service_items + parts + sundry_items
		
		if all_items:
			for item in all_items:
				row = {
					**order,
					**item
				}
				data.append(row)
		else:
			# If no items, still show the order
			data.append(order)
	
	return data


def get_conditions(filters):
	conditions = ["ro.docstatus != 2"]
	
	if filters.get("order_number"):
		conditions.append(f"ro.name = '{filters.get('order_number')}'")
	
	if filters.get("from_date"):
		conditions.append(f"ro.repair_date >= '{filters.get('from_date')}'")
	
	if filters.get("to_date"):
		conditions.append(f"ro.repair_date <= '{filters.get('to_date')}'")
	
	if filters.get("customer"):
		conditions.append(f"ro.customer = '{filters.get('customer')}'")
	
	if filters.get("repair_type"):
		conditions.append(f"ro.repair_type = '{filters.get('repair_type')}'")
	
	if filters.get("bill_type"):
		conditions.append(f"""
			(ro.name IN (SELECT parent FROM `tabRepair Order Service Items` WHERE bill_type = '{filters.get('bill_type')}')
			OR ro.name IN (SELECT parent FROM `tabRepair Order Parts` WHERE bill_type = '{filters.get('bill_type')}')
			OR ro.name IN (SELECT parent FROM `tabRepair Order Sundry Items` WHERE bill_type = '{filters.get('bill_type')}'))
		""")
	
	return " AND ".join(conditions) if conditions else "1=1"
