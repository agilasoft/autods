# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import formatdate


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "period",
			"label": _("Period"),
			"fieldtype": "Data",
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
			"label": _("Customer/Insurance Company"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "service_items_amount",
			"label": _("Service Items Amount"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "parts_amount",
			"label": _("Parts Amount"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "sundry_items_amount",
			"label": _("Sundry Items Amount"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "total_amount",
			"label": _("Total Amount"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "order_count",
			"label": _("Order Count"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "percentage",
			"label": _("Percentage of Total"),
			"fieldtype": "Percent",
			"width": 120
		}
	]


def get_data(filters):
	group_by = filters.get("group_by", "Bill Type")
	conditions = get_conditions(filters)
	
	# Get total for percentage calculation
	total_query = f"""
		SELECT 
			SUM(COALESCE(rosi.amount, 0) + COALESCE(rop.amount, 0) + COALESCE(rosu.amount, 0)) as total
		FROM `tabRepair Order` ro
		LEFT JOIN `tabRepair Order Service Items` rosi ON rosi.parent = ro.name
		LEFT JOIN `tabRepair Order Parts` rop ON rop.parent = ro.name
		LEFT JOIN `tabRepair Order Sundry Items` rosu ON rosu.parent = ro.name
		WHERE {conditions}
	"""
	total_result = frappe.db.sql(total_query, as_dict=1)
	total_revenue = total_result[0].total if total_result and total_result[0].total else 1
	
	if group_by == "Date":
		group_by_clause = "DATE(ro.repair_date)"
		select_clause = f"{group_by_clause} as period"
		order_by = "period DESC"
	else:
		group_by_clause = "COALESCE(rosi.bill_type, rop.bill_type, rosu.bill_type, 'Customer')"
		select_clause = f"{group_by_clause} as period"
		order_by = "period"
	
	query = f"""
		SELECT 
			{select_clause},
			COALESCE(rosi.bill_type, rop.bill_type, rosu.bill_type, 'Customer') as bill_type,
			COALESCE(rosi.bill_to, rop.bill_to, rosu.bill_to, ro.customer) as bill_to,
			SUM(COALESCE(rosi.amount, 0)) as service_items_amount,
			SUM(COALESCE(rop.amount, 0)) as parts_amount,
			SUM(COALESCE(rosu.amount, 0)) as sundry_items_amount,
			SUM(COALESCE(rosi.amount, 0) + COALESCE(rop.amount, 0) + COALESCE(rosu.amount, 0)) as total_amount,
			COUNT(DISTINCT ro.name) as order_count,
			(SUM(COALESCE(rosi.amount, 0) + COALESCE(rop.amount, 0) + COALESCE(rosu.amount, 0)) / {total_revenue}) * 100 as percentage
		FROM `tabRepair Order` ro
		LEFT JOIN `tabRepair Order Service Items` rosi ON rosi.parent = ro.name
		LEFT JOIN `tabRepair Order Parts` rop ON rop.parent = ro.name
		LEFT JOIN `tabRepair Order Sundry Items` rosu ON rosu.parent = ro.name
		WHERE {conditions}
		GROUP BY {group_by_clause}, bill_type, bill_to
		ORDER BY {order_by}
	"""
	
	data = frappe.db.sql(query, as_dict=1)
	
	# Format period if it's a date
	for row in data:
		if group_by == "Date" and row.period:
			try:
				row.period = formatdate(row.period)
			except:
				pass
	
	return data


def get_conditions(filters):
	conditions = ["ro.docstatus = 1"]
	
	if filters.get("from_date"):
		conditions.append(f"ro.repair_date >= '{filters.get('from_date')}'")
	
	if filters.get("to_date"):
		conditions.append(f"ro.repair_date <= '{filters.get('to_date')}'")
	
	if filters.get("bill_type"):
		conditions.append(f"""
			(rosi.bill_type = '{filters.get('bill_type')}' 
			OR rop.bill_type = '{filters.get('bill_type')}' 
			OR rosu.bill_type = '{filters.get('bill_type')}')
		""")
	
	if filters.get("customer"):
		conditions.append(f"""
			(rosi.bill_to = '{filters.get('customer')}' 
			OR rop.bill_to = '{filters.get('customer')}' 
			OR rosu.bill_to = '{filters.get('customer')}' 
			OR ro.customer = '{filters.get('customer')}')
		""")
	
	return " AND ".join(conditions) if conditions else "1=1"
