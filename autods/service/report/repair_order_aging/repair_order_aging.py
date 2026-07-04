# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import date


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	return columns, data, None, chart


def get_chart(data):
	if not data:
		return None
	buckets = [
		(_("0-7 days"), lambda d: d <= 7),
		(_("8-14 days"), lambda d: 8 <= d <= 14),
		(_("15-30 days"), lambda d: 15 <= d <= 30),
		(_("31-60 days"), lambda d: 31 <= d <= 60),
		(_("60+ days"), lambda d: d > 60),
	]
	labels = [b[0] for b in buckets]
	values = [0] * len(buckets)
	for row in data:
		days = row.get("days_open") or 0
		for idx, (_label, predicate) in enumerate(buckets):
			if predicate(days):
				values[idx] += 1
				break
	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Open Orders"), "values": values}],
		},
		"type": "bar",
		"height": 300,
		"colors": ["#7575ff"],
	}


def get_columns():
	return [
		{"fieldname": "name", "label": _("Repair Order"), "fieldtype": "Link", "options": "Repair Order", "width": 130},
		{"fieldname": "repair_date", "label": _("Repair Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "days_open", "label": _("Days Open"), "fieldtype": "Int", "width": 90},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 140},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "repair_type", "label": _("Repair Type"), "fieldtype": "Link", "options": "Repair Type", "width": 100},
		{"fieldname": "expected_completion_date", "label": _("Expected Completion"), "fieldtype": "Datetime", "width": 140},
		{"fieldname": "grand_total", "label": _("Grand Total"), "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = ["r.docstatus in (0, 1)", "r.status not in ('Completed', 'Cancelled')"]
	values = {}
	if filters.get("customer"):
		conditions.append("r.customer = %(customer)s")
		values["customer"] = filters["customer"]
	if filters.get("min_days"):
		conditions.append("r.repair_date <= date_sub(curdate(), interval %(min_days)s day)")
		values["min_days"] = int(filters["min_days"])
	where = " and ".join(conditions)
	query = f"""
		select
			r.name,
			r.repair_date,
			datediff(curdate(), r.repair_date) as days_open,
			r.customer,
			r.status,
			r.repair_type,
			r.expected_completion_date,
			r.grand_total
		from `tabRepair Order` r
		where {where}
		order by days_open desc, r.repair_date asc
	"""
	return frappe.db.sql(query, values, as_dict=1)
