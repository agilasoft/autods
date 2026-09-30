# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, nowdate

BUCKETS = ("0-3", "4-7", "8-14", "15+")
STATUSES = ("Open", "Waiting Parts", "In Progress", "Paint", "QC", "Ready")


def execute(filters=None):
	columns = [
		{"fieldname": "bucket", "label": _("Age (Days)"), "fieldtype": "Data", "width": 100},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "order_count", "label": _("Repair Orders"), "fieldtype": "Int", "width": 120},
	]
	data = get_data()
	return columns, data, None, get_chart(data)


def bucket_for(days):
	if days <= 3:
		return "0-3"
	if days <= 7:
		return "4-7"
	if days <= 14:
		return "8-14"
	return "15+"


def get_data():
	rows = frappe.db.sql(
		"""
		select status, repair_date
		from `tabRepair Order`
		where docstatus < 2 and status not in ('Completed', 'Cancelled')
		""",
		as_dict=True,
	)
	today = getdate(nowdate())
	counts = {(bucket, status): 0 for bucket in BUCKETS for status in STATUSES}
	for row in rows:
		status = row.status if row.status in STATUSES else "Open"
		days = date_diff(today, getdate(row.repair_date)) if row.repair_date else 0
		counts[(bucket_for(max(days, 0)), status)] += 1
	return [
		{"bucket": bucket, "status": status, "order_count": counts[(bucket, status)]}
		for bucket in BUCKETS
		for status in STATUSES
		if counts[(bucket, status)]
	]


def get_chart(data):
	if not data:
		return None
	series = {status: {bucket: 0 for bucket in BUCKETS} for status in STATUSES}
	for row in data:
		series[row["status"]][row["bucket"]] = row["order_count"]
	return {
		"data": {
			"labels": list(BUCKETS),
			"datasets": [
				{"name": _(status), "values": [series[status][bucket] for bucket in BUCKETS]}
				for status in STATUSES
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
		"height": 300,
	}
