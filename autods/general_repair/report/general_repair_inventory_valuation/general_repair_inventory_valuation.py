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
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 120
		},
		{
			"fieldname": "quantity_consumed",
			"label": _("Quantity Consumed"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "avg_rate",
			"label": _("Average Rate"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "total_value",
			"label": _("Total Value"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "order_count",
			"label": _("Number of Orders"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "last_used_date",
			"label": _("Last Used Date"),
			"fieldtype": "Date",
			"width": 120
		}
	]


def get_data(filters):
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT 
			rop.item as item_code,
			rop.item_name,
			rop.item_type,
			rop.warehouse,
			SUM(rop.qty) as quantity_consumed,
			AVG(rop.rate) as avg_rate,
			SUM(rop.amount) as total_value,
			COUNT(DISTINCT ro.name) as order_count,
			MAX(ro.repair_date) as last_used_date
		FROM `tabRepair Order` ro
		INNER JOIN `tabRepair Order Parts` rop ON rop.parent = ro.name
		WHERE {conditions}
		GROUP BY rop.item, rop.item_name, rop.item_type, rop.warehouse
		ORDER BY total_value DESC
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
	
	return " AND ".join(conditions) if conditions else "1=1"
