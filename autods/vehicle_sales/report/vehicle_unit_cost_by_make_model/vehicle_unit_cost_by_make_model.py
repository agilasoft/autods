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
		{"fieldname": "make", "label": _("Make"), "fieldtype": "Link", "options": "Vehicle Make", "width": 120},
		{"fieldname": "model", "label": _("Model"), "fieldtype": "Link", "options": "Vehicle Model", "width": 120},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "unit_count", "label": _("Units"), "fieldtype": "Int", "width": 80},
		{"fieldname": "total_inventory_cost", "label": _("Total Inventory Cost"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "total_accessory_cost", "label": _("Total Accessory Cost"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "total_unit_cost", "label": _("Total Unit Cost"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "avg_unit_cost", "label": _("Avg Unit Cost"), "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = []
	values = {}
	if filters.get("status"):
		conditions.append("v.status = %(status)s")
		values["status"] = filters["status"]
	if filters.get("make"):
		conditions.append("v.make = %(make)s")
		values["make"] = filters["make"]
	if filters.get("warehouse"):
		conditions.append("v.warehouse = %(warehouse)s")
		values["warehouse"] = filters["warehouse"]
	where = " and ".join(conditions) if conditions else "1=1"
	query = f"""
		select
			v.make,
			v.model,
			v.status,
			count(*) as unit_count,
			sum(ifnull(v.current_cost, 0)) as total_inventory_cost,
			sum(ifnull(v.total_accessory_cost, 0)) as total_accessory_cost,
			sum(ifnull(v.total_unit_cost, ifnull(v.current_cost, 0))) as total_unit_cost,
			round(avg(ifnull(v.total_unit_cost, ifnull(v.current_cost, 0))), 2) as avg_unit_cost
		from `tabVehicle Unit` v
		where {where}
		group by v.make, v.model, v.status
		order by v.make, v.model, total_unit_cost desc
	"""
	return frappe.db.sql(query, values, as_dict=1)
