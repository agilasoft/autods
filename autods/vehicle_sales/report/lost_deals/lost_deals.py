# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = [
		{
			"fieldname": "name",
			"label": _("Quote"),
			"fieldtype": "Link",
			"options": "Vehicle Sales Quote",
			"width": 140,
		},
		{"fieldname": "transaction_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{
			"fieldname": "party_name",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 160,
		},
		{
			"fieldname": "make",
			"label": _("Make"),
			"fieldtype": "Link",
			"options": "Vehicle Make",
			"width": 120,
		},
		{
			"fieldname": "salesperson",
			"label": _("Sales Person"),
			"fieldtype": "Link",
			"options": "Sales Person",
			"width": 140,
		},
		{"fieldname": "lost_reason", "label": _("Lost Reason"), "fieldtype": "Data", "width": 200},
		{"fieldname": "competitor", "label": _("Competitor"), "fieldtype": "Data", "width": 140},
		{"fieldname": "grand_total", "label": _("Quoted Price"), "fieldtype": "Currency", "width": 120},
	]
	conditions = ["docstatus = 1", "status = 'Lost'"]
	values = {}
	if filters.get("from_date"):
		conditions.append("transaction_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("transaction_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("salesperson"):
		conditions.append("salesperson = %(salesperson)s")
		values["salesperson"] = filters["salesperson"]
	rows = frappe.db.sql(
		"""
		select name, transaction_date, party_name, make, salesperson, lost_reason, competitor, grand_total
		from `tabVehicle Sales Quote`
		where {where}
		order by transaction_date desc
		""".format(where=" and ".join(conditions)),
		values,
		as_dict=True,
	)
	return columns, rows, None, get_chart(rows)


def get_chart(rows):
	if not rows:
		return None
	counts = {}
	for row in rows:
		reason = (row.lost_reason or _("(No reason)"))[:40]
		counts[reason] = counts.get(reason, 0) + 1
	labels = list(counts)
	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Quotes"), "values": [counts[label] for label in labels]}],
		},
		"type": "bar",
		"height": 280,
	}
