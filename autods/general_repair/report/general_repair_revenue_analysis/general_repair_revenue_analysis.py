# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, formatdate


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	group_by = filters.get("group_by", "Date")
	
	columns = [
		{
			"fieldname": "period",
			"label": _("Period"),
			"fieldtype": "Data",
			"width": 120
		}
	]
	
	if group_by != "Customer":
		columns.append({
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		})
	
	if group_by != "Repair Type":
		columns.append({
			"fieldname": "repair_type",
			"label": _("Repair Type"),
			"fieldtype": "Link",
			"options": "Repair Type",
			"width": 150
		})
	
	if group_by != "Bill Type":
		columns.append({
			"fieldname": "bill_type",
			"label": _("Bill Type"),
			"fieldtype": "Data",
			"width": 100
		})
	
	columns.extend([
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
			"fieldname": "total_revenue",
			"label": _("Total Revenue"),
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
			"fieldname": "avg_order_value",
			"label": _("Avg Order Value"),
			"fieldtype": "Currency",
			"width": 120
		}
	])
	
	return columns


def get_data(filters):
	group_by = filters.get("group_by", "Date")
	conditions = get_conditions(filters)
	
	# Build GROUP BY clause
	group_by_clause = get_group_by_clause(group_by)
	
	query = f"""
		SELECT 
			{group_by_clause['select']} as period,
			{group_by_clause.get('customer', 'NULL')} as customer,
			{group_by_clause.get('repair_type', 'NULL')} as repair_type,
			{group_by_clause.get('bill_type', 'NULL')} as bill_type,
			COALESCE(SUM(CASE WHEN rosi.amount IS NOT NULL THEN rosi.amount ELSE 0 END), 0) as service_items_revenue,
			COALESCE(SUM(CASE WHEN rop.amount IS NOT NULL THEN rop.amount ELSE 0 END), 0) as parts_revenue,
			COALESCE(SUM(CASE WHEN rosu.amount IS NOT NULL THEN rosu.amount ELSE 0 END), 0) as sundry_items_revenue,
			(COALESCE(SUM(CASE WHEN rosi.amount IS NOT NULL THEN rosi.amount ELSE 0 END), 0) +
			 COALESCE(SUM(CASE WHEN rop.amount IS NOT NULL THEN rop.amount ELSE 0 END), 0) +
			 COALESCE(SUM(CASE WHEN rosu.amount IS NOT NULL THEN rosu.amount ELSE 0 END), 0)) as total_revenue,
			COUNT(DISTINCT ro.name) as order_count,
			(COALESCE(SUM(CASE WHEN rosi.amount IS NOT NULL THEN rosi.amount ELSE 0 END), 0) +
			 COALESCE(SUM(CASE WHEN rop.amount IS NOT NULL THEN rop.amount ELSE 0 END), 0) +
			 COALESCE(SUM(CASE WHEN rosu.amount IS NOT NULL THEN rosu.amount ELSE 0 END), 0)) / 
			NULLIF(COUNT(DISTINCT ro.name), 0) as avg_order_value
		FROM `tabRepair Order` ro
		LEFT JOIN `tabRepair Order Service Items` rosi ON rosi.parent = ro.name
		LEFT JOIN `tabRepair Order Parts` rop ON rop.parent = ro.name
		LEFT JOIN `tabRepair Order Sundry Items` rosu ON rosu.parent = ro.name
		WHERE {conditions}
		GROUP BY {group_by_clause['group_by']}
		ORDER BY period DESC
	"""
	
	data = frappe.db.sql(query, as_dict=1)
	
	# Format period based on group_by
	for row in data:
		if group_by == "Date" and row.period:
			row.period = formatdate(row.period)
	
	return data


def get_group_by_clause(group_by):
	if group_by == "Date":
		return {
			"select": "DATE(ro.repair_date)",
			"group_by": "DATE(ro.repair_date)"
		}
	elif group_by == "Customer":
		return {
			"select": "ro.customer",
			"customer": "ro.customer",
			"group_by": "ro.customer"
		}
	elif group_by == "Repair Type":
		return {
			"select": "ro.repair_type",
			"repair_type": "ro.repair_type",
			"group_by": "ro.repair_type"
		}
	elif group_by == "Bill Type":
		return {
			"select": "COALESCE(rosi.bill_type, rop.bill_type, rosu.bill_type, 'Customer')",
			"bill_type": "COALESCE(rosi.bill_type, rop.bill_type, rosu.bill_type, 'Customer')",
			"group_by": "COALESCE(rosi.bill_type, rop.bill_type, rosu.bill_type, 'Customer')"
		}
	else:
		return {
			"select": "DATE(ro.repair_date)",
			"group_by": "DATE(ro.repair_date)"
		}


def get_conditions(filters):
	conditions = ["ro.docstatus = 1"]  # Only submitted orders
	
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
			(rosi.bill_type = '{filters.get('bill_type')}' 
			OR rop.bill_type = '{filters.get('bill_type')}' 
			OR rosu.bill_type = '{filters.get('bill_type')}')
		""")
	
	return " AND ".join(conditions) if conditions else "1=1"
