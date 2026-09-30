# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, nowdate


def execute(filters=None):
	filters = filters or {}
	columns = [
		{
			"fieldname": "repair_order",
			"label": _("Repair Order"),
			"fieldtype": "Link",
			"options": "Repair Order",
			"width": 140,
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 160,
		},
		{
			"fieldname": "vehicle_unit",
			"label": _("Vehicle"),
			"fieldtype": "Link",
			"options": "Vehicle Unit",
			"width": 140,
		},
		{
			"fieldname": "service_advisor",
			"label": _("Service Advisor"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 140,
		},
		{
			"fieldname": "service_type",
			"label": _("Service Type"),
			"fieldtype": "Link",
			"options": "Service Type",
			"width": 120,
		},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 110},
		{
			"fieldname": "expected_completion_date",
			"label": _("Expected"),
			"fieldtype": "Datetime",
			"width": 150,
		},
		{"fieldname": "actual_completion_date", "label": _("Actual"), "fieldtype": "Datetime", "width": 150},
		{"fieldname": "on_time", "label": _("On Time"), "fieldtype": "Data", "width": 90},
		{"fieldname": "slip_days", "label": _("Slip Days"), "fieldtype": "Int", "width": 90},
	]
	data = get_data(filters)
	return columns, data, None, get_chart(data)


def get_data(filters):
	conditions = ["r.docstatus < 2", "r.expected_completion_date is not null"]
	values = {}
	if filters.get("from_date"):
		conditions.append("date(r.expected_completion_date) >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("date(r.expected_completion_date) <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("service_advisor"):
		conditions.append("r.service_advisor = %(service_advisor)s")
		values["service_advisor"] = filters["service_advisor"]
	if filters.get("service_type"):
		conditions.append("r.service_type = %(service_type)s")
		values["service_type"] = filters["service_type"]
	rows = frappe.db.sql(
		"""
		select r.name as repair_order, r.customer, r.vehicle_unit, r.service_advisor,
			r.service_type, r.status, r.expected_completion_date,
			max(j.actual_completion_date) as actual_completion_date
		from `tabRepair Order` r
		left join `tabJob Card` j on j.repair_order = r.name and j.docstatus < 2
		where {where}
		group by r.name
		order by r.expected_completion_date
		""".format(where=" and ".join(conditions)),
		values,
		as_dict=True,
	)
	today = getdate(nowdate())
	for row in rows:
		expected = getdate(row.expected_completion_date) if row.expected_completion_date else None
		actual = getdate(row.actual_completion_date) if row.actual_completion_date else None
		compare = actual or today
		row.on_time = "Yes" if expected and compare <= expected else "No"
		row.slip_days = (compare - expected).days if expected and compare > expected else 0
		row.week = expected.strftime("%Y-W%W") if expected else ""
	return rows


def get_chart(data):
	buckets = {}
	for row in data:
		week = row.get("week") or _("(No date)")
		bucket = buckets.setdefault(week, {"yes": 0, "total": 0})
		bucket["total"] += 1
		if row.get("on_time") == "Yes":
			bucket["yes"] += 1
	if not buckets:
		return None
	labels = sorted(buckets)
	values = [
		round(100 * buckets[label]["yes"] / buckets[label]["total"], 1) if buckets[label]["total"] else 0
		for label in labels
	]
	return {
		"data": {"labels": labels, "datasets": [{"name": _("On Time %"), "values": values}]},
		"type": "bar",
		"height": 280,
	}
