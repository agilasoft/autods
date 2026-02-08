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
		{"fieldname": "vehicle_make", "label": _("Vehicle Make"), "fieldtype": "Link", "options": "Vehicle Make", "width": 140},
		{"fieldname": "compatibility_count", "label": _("Compatibility Records"), "fieldtype": "Int", "width": 140},
		{"fieldname": "parts_count", "label": _("Distinct Parts"), "fieldtype": "Int", "width": 120},
	]


def get_data(filters):
	conditions = []
	values = {}
	if filters.get("vehicle_make"):
		conditions.append("p.vehicle_make = %(vehicle_make)s")
		values["vehicle_make"] = filters["vehicle_make"]
	where = " and ".join(conditions) if conditions else "1=1"
	query = (
		"select p.vehicle_make, count(*) as compatibility_count, count(distinct p.part) as parts_count "
		"from `tabParts Compatibility` p where " + where + " "
		"group by p.vehicle_make order by compatibility_count desc"
	)
	return frappe.db.sql(query, values, as_dict=1)
