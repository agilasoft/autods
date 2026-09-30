# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "month", "label": _("Month"), "fieldtype": "Data", "width": 90},
		{"fieldname": "bill_type", "label": _("Bill To"), "fieldtype": "Data", "width": 110},
		{"fieldname": "service_item_type", "label": _("Line Type"), "fieldtype": "Data", "width": 110},
		{"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "width": 120},
	]
	data = get_data(filters)
	return columns, data, None, get_chart(data)


def get_data(filters):
	conditions = ["r.docstatus = 1"]
	values = {}
	if filters.get("from_date"):
		conditions.append("r.repair_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("r.repair_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("bill_type"):
		conditions.append("c.bill_type = %(bill_type)s")
		values["bill_type"] = filters["bill_type"]
	where = " and ".join(conditions)
	return frappe.db.sql(
		"""
		select date_format(r.repair_date, '%%Y-%%m') as month,
			c.bill_type, c.service_item_type, sum(ifnull(c.amount, 0)) as amount
		from `tabRepair Order Charges` c
		inner join `tabRepair Order` r on r.name = c.parent and c.parenttype = 'Repair Order'
		where """
		+ where
		+ """
		group by month, c.bill_type, c.service_item_type
		order by month, c.bill_type
		""",
		values,
		as_dict=True,
	)


def get_chart(data):
	if not data:
		return None
	months = []
	series = {"Customer": {}, "Insurance": {}, "Warranty": {}}
	for row in data:
		month = row.month or ""
		if month not in months:
			months.append(month)
		bill = row.bill_type if row.bill_type in series else "Customer"
		series[bill][month] = series[bill].get(month, 0) + flt(row.amount)
	return {
		"data": {
			"labels": months,
			"datasets": [
				{"name": _(name), "values": [series[name].get(month, 0) for month in months]}
				for name in ("Customer", "Insurance", "Warranty")
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
		"height": 280,
	}
