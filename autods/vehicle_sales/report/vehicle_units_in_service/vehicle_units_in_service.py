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
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 140},
		{"fieldname": "total_unit_cost", "label": _("Total Unit Cost"), "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = ["v.status = 'In Service'"]
	values = {}
	if filters.get("make"):
		conditions.append("v.make = %(make)s")
		values["make"] = filters["make"]
	where = " and ".join(conditions)
	query = (
		"select v.name, v.code, v.make, v.model, v.customer, v.total_unit_cost "
		"from `tabVehicle Unit` v where " + where + " order by v.modified desc"
	)
	return frappe.db.sql(query, values, as_dict=1)
