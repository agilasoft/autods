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
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 160},
		{"fieldname": "customer_name", "label": _("Customer Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "order_count", "label": _("Repair Orders"), "fieldtype": "Int", "width": 110},
		{"fieldname": "grand_total", "label": _("Total Revenue"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "avg_order_value", "label": _("Avg Order Value"), "fieldtype": "Currency", "width": 120},
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
	if filters.get("customer"):
		conditions.append("r.customer = %(customer)s")
		values["customer"] = filters["customer"]
	values["limit"] = int(filters.get("top_n") or 20)
	where = " and ".join(conditions)
	query = (
		"select r.customer, c.customer_name, count(*) as order_count, "
		"sum(ifnull(r.grand_total, 0)) as grand_total, round(avg(ifnull(r.grand_total, 0)), 2) as avg_order_value "
		"from `tabRepair Order` r left join `tabCustomer` c on c.name = r.customer "
		"where " + where + " group by r.customer order by grand_total desc limit %(limit)s"
	)
	return frappe.db.sql(query, values, as_dict=1)
