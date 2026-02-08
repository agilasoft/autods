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
		{"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 140},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "unit_count", "label": _("Units"), "fieldtype": "Int", "width": 80},
		{"fieldname": "total_inventory_value", "label": _("Total Inventory Value"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "total_accessory_value", "label": _("Total Accessory Cost"), "fieldtype": "Currency", "width": 140},
	]


def get_data(filters):
	conditions = []
	values = {}
	if filters.get("warehouse"):
		conditions.append("v.warehouse = %(warehouse)s")
		values["warehouse"] = filters["warehouse"]
	if filters.get("status"):
		conditions.append("v.status = %(status)s")
		values["status"] = filters["status"]
	where = " and ".join(conditions) if conditions else "1=1"
	query = (
		"select v.warehouse, v.status, count(*) as unit_count, "
		"sum(ifnull(v.current_cost, 0)) as total_inventory_value, "
		"sum(ifnull(v.total_accessory_cost, 0)) as total_accessory_value "
		"from `tabVehicle Unit` v where " + where + " "
		"group by v.warehouse, v.status order by total_inventory_value desc"
	)
	return frappe.db.sql(query, values, as_dict=1)
