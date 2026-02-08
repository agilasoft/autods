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
			"fieldname": "item_code",
			"label": _("Item Code"),
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
			"fieldname": "item_type",
			"label": _("Item Type"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "qty",
			"label": _("Quantity"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "uom",
			"label": _("UOM"),
			"fieldtype": "Link",
			"options": "UOM",
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
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
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
		}
	]


def get_data(filters):
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT 
			ro.name as order_number,
			ro.repair_date,
			rop.item as item_code,
			rop.item_name,
			rop.item_type,
			rop.qty,
			rop.uom,
			rop.rate,
			rop.amount,
			rop.warehouse,
			rop.bill_type,
			ro.customer
		FROM `tabRepair Order` ro
		INNER JOIN `tabRepair Order Parts` rop ON rop.parent = ro.name
		WHERE {conditions}
		ORDER BY ro.repair_date DESC, ro.name DESC, rop.item
	"""
	
	return frappe.db.sql(query, as_dict=1)


def get_conditions(filters):
	conditions = ["ro.docstatus = 1"]
	
	if filters.get("from_date"):
		conditions.append(f"ro.repair_date >= '{filters.get('from_date')}'")
	
	if filters.get("to_date"):
		conditions.append(f"ro.repair_date <= '{filters.get('to_date')}'")
	
	if filters.get("item"):
		conditions.append(f"rop.item = '{filters.get('item')}'")
	
	if filters.get("item_type"):
		conditions.append(f"rop.item_type = '{filters.get('item_type')}'")
	
	if filters.get("warehouse"):
		conditions.append(f"rop.warehouse = '{filters.get('warehouse')}'")
	
	if filters.get("customer"):
		conditions.append(f"ro.customer = '{filters.get('customer')}'")
	
	return " AND ".join(conditions) if conditions else "1=1"
