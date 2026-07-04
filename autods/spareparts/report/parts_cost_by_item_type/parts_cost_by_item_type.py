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
		{"fieldname": "item_type", "label": _("Item Type"), "fieldtype": "Data", "width": 140},
		{"fieldname": "order_count", "label": _("Repair Orders"), "fieldtype": "Int", "width": 110},
		{"fieldname": "total_qty", "label": _("Total Qty"), "fieldtype": "Float", "width": 100},
		{"fieldname": "total_amount", "label": _("Total Amount"), "fieldtype": "Currency", "width": 120},
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
	if filters.get("item_type"):
		conditions.append("p.item_type = %(item_type)s")
		values["item_type"] = filters["item_type"]
	where = " and ".join(conditions)
	query = (
		"select p.item_type, count(distinct p.parent) as order_count, sum(p.qty) as total_qty, "
		"sum(ifnull(p.amount, 0)) as total_amount from `tabRepair Order Charges` p "
		"inner join `tabRepair Order` r on r.name = p.parent where p.service_item_type = 'Spareparts' and " + where + " "
		"group by p.item_type order by total_amount desc"
	)
	return frappe.db.sql(query, values, as_dict=1)
