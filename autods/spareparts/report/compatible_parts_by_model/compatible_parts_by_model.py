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
		{"fieldname": "vehicle_make", "label": _("Vehicle Make"), "fieldtype": "Link", "options": "Vehicle Make", "width": 120},
		{"fieldname": "vehicle_model", "label": _("Vehicle Model"), "fieldtype": "Link", "options": "Vehicle Model", "width": 120},
		{"fieldname": "parts_count", "label": _("Compatible Parts"), "fieldtype": "Int", "width": 120},
	]


def get_data(filters):
	conditions = []
	values = {}
	if filters.get("vehicle_make"):
		conditions.append("p.vehicle_make = %(vehicle_make)s")
		values["vehicle_make"] = filters["vehicle_make"]
	if filters.get("vehicle_model"):
		conditions.append("p.vehicle_model = %(vehicle_model)s")
		values["vehicle_model"] = filters["vehicle_model"]
	where = " and ".join(conditions) if conditions else "1=1"
	query = (
		"select p.vehicle_make, p.vehicle_model, count(distinct p.part) as parts_count "
		"from `tabParts Compatibility` p where " + where + " "
		"group by p.vehicle_make, p.vehicle_model order by parts_count desc"
	)
	return frappe.db.sql(query, values, as_dict=1)
