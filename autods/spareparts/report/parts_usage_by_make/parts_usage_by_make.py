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
		{"fieldname": "make", "label": _("Vehicle Make"), "fieldtype": "Link", "options": "Vehicle Make", "width": 140},
		{"fieldname": "total_qty", "label": _("Parts Qty Consumed"), "fieldtype": "Float", "width": 130},
		{"fieldname": "total_amount", "label": _("Parts Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "order_count", "label": _("Repair Orders"), "fieldtype": "Int", "width": 110},
	]


def get_data(filters):
	conditions = ["r.docstatus = 1"]
	values = {}
	if filters.get("from_date"):
		conditions.append("r.repair_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("r.repair_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("make"):
		conditions.append("v.make = %(make)s")
		values["make"] = filters["make"]
	where = " and ".join(conditions)
	query = (
		"select v.make, sum(p.qty) as total_qty, sum(ifnull(p.amount, 0)) as total_amount, "
		"count(distinct p.parent) as order_count from `tabRepair Order Charges` p "
		"inner join `tabRepair Order` r on r.name = p.parent "
		"inner join `tabVehicle Unit` v on v.name = r.vehicle_unit "
		"where p.service_item_type = 'Spareparts' and " + where + " group by v.make order by total_amount desc"
	)
	return frappe.db.sql(query, values, as_dict=1)
