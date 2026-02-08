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
			"fieldname": "name",
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
			"fieldname": "plate_no",
			"label": _("Plate No"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "repair_date",
			"label": _("Repair Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "repair_type",
			"label": _("Repair Type"),
			"fieldtype": "Link",
			"options": "Repair Type",
			"width": 150
		},
		{
			"fieldname": "docstatus",
			"label": _("Status"),
			"fieldtype": "Int",
			"width": 80
		},
		{
			"fieldname": "total_service_items_amount",
			"label": _("Service Items Amount"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "total_parts_amount",
			"label": _("Parts Amount"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "total_sundry_items_amount",
			"label": _("Sundry Items Amount"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "grand_total",
			"label": _("Grand Total"),
			"fieldtype": "Currency",
			"width": 150
		}
	]


def get_data(filters):
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT 
			ro.name,
			ro.customer,
			ro.plate_no,
			ro.repair_date,
			ro.repair_type,
			ro.docstatus,
			COALESCE(SUM(rosi.amount), 0) as total_service_items_amount,
			COALESCE(SUM(rop.amount), 0) as total_parts_amount,
			COALESCE(SUM(rosu.amount), 0) as total_sundry_items_amount,
			(COALESCE(SUM(rosi.amount), 0) + 
			 COALESCE(SUM(rop.amount), 0) + 
			 COALESCE(SUM(rosu.amount), 0)) as grand_total
		FROM `tabRepair Order` ro
		LEFT JOIN `tabRepair Order Service Items` rosi ON rosi.parent = ro.name
		LEFT JOIN `tabRepair Order Parts` rop ON rop.parent = ro.name
		LEFT JOIN `tabRepair Order Sundry Items` rosu ON rosu.parent = ro.name
		WHERE {conditions}
		GROUP BY ro.name
		ORDER BY ro.repair_date DESC, ro.name DESC
	"""
	
	return frappe.db.sql(query, as_dict=1)


def get_conditions(filters):
	conditions = ["ro.docstatus != 2"]  # Exclude cancelled
	
	if filters.get("from_date"):
		conditions.append(f"ro.repair_date >= '{filters.get('from_date')}'")
	
	if filters.get("to_date"):
		conditions.append(f"ro.repair_date <= '{filters.get('to_date')}'")
	
	if filters.get("customer"):
		conditions.append(f"ro.customer = '{filters.get('customer')}'")
	
	if filters.get("repair_type"):
		conditions.append(f"ro.repair_type = '{filters.get('repair_type')}'")
	
	if filters.get("status"):
		if filters.get("status") == "Draft":
			conditions.append("ro.docstatus = 0")
		elif filters.get("status") == "Submitted":
			conditions.append("ro.docstatus = 1")
		elif filters.get("status") == "Cancelled":
			conditions.append("ro.docstatus = 2")
	
	if filters.get("plate_no"):
		conditions.append(f"ro.plate_no LIKE '%{filters.get('plate_no')}%'")
	
	return " AND ".join(conditions) if conditions else "1=1"
