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
		{"fieldname": "period", "label": _("Period"), "fieldtype": "Data", "width": 120},
		{"fieldname": "units_sold", "label": _("Units Sold"), "fieldtype": "Int", "width": 100},
		{"fieldname": "total_cost", "label": _("Total Unit Cost"), "fieldtype": "Currency", "width": 130},
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
	where = " and ".join(conditions)
	query = (
		"select date_format(dn.posting_date, '%%Y-%%m') as period, count(*) as units_sold, "
		"sum(ifnull(v.total_unit_cost, v.current_cost)) as total_cost "
		"from `tabVehicle Unit` v inner join `tabDelivery Note` dn on dn.name = v.delivery_note "
		"where " + where + " group by period order by period desc"
	)
	return frappe.db.sql(query, values, as_dict=1)
