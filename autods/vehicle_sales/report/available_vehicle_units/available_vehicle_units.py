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
		{"fieldname": "name", "label": _("Vehicle Unit"), "fieldtype": "Link", "options": "Vehicle Unit", "width": 130},
		{"fieldname": "code", "label": _("Serial / VIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "make", "label": _("Make"), "fieldtype": "Link", "options": "Vehicle Make", "width": 100},
		{"fieldname": "model", "label": _("Model"), "fieldtype": "Link", "options": "Vehicle Model", "width": 100},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 90},
		{"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 120},
		{"fieldname": "current_cost", "label": _("Current Cost"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_unit_cost", "label": _("Total Unit Cost"), "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = []
	values = {}
	if filters.get("status"):
		conditions.append("v.status = %(status)s")
		values["status"] = filters["status"]
	else:
		conditions.append("v.status in ('Available', 'Reserved')")
	if filters.get("warehouse"):
		conditions.append("v.warehouse = %(warehouse)s")
		values["warehouse"] = filters["warehouse"]
	if filters.get("make"):
		conditions.append("v.make = %(make)s")
		values["make"] = filters["make"]
	if filters.get("model"):
		conditions.append("v.model = %(model)s")
		values["model"] = filters["model"]
	where = " and ".join(conditions)
	query = f"""
		select
			v.name,
			v.code,
			v.make,
			v.model,
			v.status,
			v.warehouse,
			v.current_cost,
			v.total_unit_cost
		from `tabVehicle Unit` v
		where {where}
		order by v.make, v.model, v.modified desc
	"""
	return frappe.db.sql(query, values, as_dict=1)
