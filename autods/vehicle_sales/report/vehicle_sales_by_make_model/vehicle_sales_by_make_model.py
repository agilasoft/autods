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
		{"fieldname": "units_sold", "label": _("Units Sold"), "fieldtype": "Int", "width": 100},
		{"fieldname": "total_cost", "label": _("Total Unit Cost"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "avg_cost", "label": _("Avg Unit Cost"), "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = ["v.status = 'Sold'"]
	values = {}
	if filters.get("from_date"):
		conditions.append("dn.posting_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("dn.posting_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("make"):
		conditions.append("v.make = %(make)s")
		values["make"] = filters["make"]
	if filters.get("model"):
		conditions.append("v.model = %(model)s")
		values["model"] = filters["model"]
	where = " and ".join(conditions)
	query = (
		"select v.make, v.model, count(*) as units_sold, "
		"sum(ifnull(v.total_unit_cost, v.current_cost)) as total_cost, "
		"round(avg(ifnull(v.total_unit_cost, v.current_cost)), 2) as avg_cost "
		"from `tabVehicle Unit` v inner join `tabDelivery Note` dn on dn.name = v.delivery_note "
		"where " + where + " group by v.make, v.model order by units_sold desc, total_cost desc"
	)
	return frappe.db.sql(query, values, as_dict=1)
