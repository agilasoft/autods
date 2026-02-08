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
		{"fieldname": "unit_count", "label": _("Units"), "fieldtype": "Int", "width": 80},
		{"fieldname": "total_accessory_cost", "label": _("Total Accessory Cost"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "avg_accessory_per_unit", "label": _("Avg per Unit"), "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = []
	values = {}
	if filters.get("make"):
		conditions.append("v.make = %(make)s")
		values["make"] = filters["make"]
	where = " and ".join(conditions) if conditions else "1=1"
	query = (
		"select v.make, v.model, count(*) as unit_count, "
		"sum(ifnull(v.total_accessory_cost, 0)) as total_accessory_cost, "
		"round(avg(ifnull(v.total_accessory_cost, 0)), 2) as avg_accessory_per_unit "
		"from `tabVehicle Unit` v where " + where + " "
		"group by v.make, v.model having total_accessory_cost > 0 order by total_accessory_cost desc"
	)
	return frappe.db.sql(query, values, as_dict=1)
