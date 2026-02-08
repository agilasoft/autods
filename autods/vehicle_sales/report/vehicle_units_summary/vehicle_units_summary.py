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
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "make", "label": _("Make"), "fieldtype": "Link", "options": "Vehicle Make", "width": 120},
		{"fieldname": "model", "label": _("Model"), "fieldtype": "Link", "options": "Vehicle Model", "width": 120},
		{"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 140},
		{"fieldname": "unit_count", "label": _("Count"), "fieldtype": "Int", "width": 80},
		{"fieldname": "total_cost", "label": _("Total Cost"), "fieldtype": "Currency", "width": 120},
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
	where = " and " + " and ".join(conditions) if conditions else ""
	query = f"""
		select
			v.status,
			v.make,
			v.model,
			v.warehouse,
			count(*) as unit_count,
			sum(ifnull(v.total_unit_cost, ifnull(v.current_cost, 0))) as total_cost
		from `tabVehicle Unit` v
		where 1=1 {where}
		group by v.status, v.make, v.model, v.warehouse
		order by v.status, v.make, v.model
	"""
	return frappe.db.sql(query, values, as_dict=1)
