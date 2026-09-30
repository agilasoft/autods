# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, nowdate


def execute(filters=None):
	filters = filters or {}
	columns = [
		{
			"fieldname": "vehicle_unit",
			"label": _("Vehicle"),
			"fieldtype": "Link",
			"options": "Vehicle Unit",
			"width": 140,
		},
		{
			"fieldname": "make",
			"label": _("Make"),
			"fieldtype": "Link",
			"options": "Vehicle Make",
			"width": 120,
		},
		{
			"fieldname": "model",
			"label": _("Model"),
			"fieldtype": "Link",
			"options": "Vehicle Model",
			"width": 120,
		},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 140,
		},
		{"fieldname": "received_on", "label": _("Received On"), "fieldtype": "Date", "width": 110},
		{"fieldname": "days_in_stock", "label": _("Days in Stock"), "fieldtype": "Int", "width": 110},
		{"fieldname": "age_bucket", "label": _("Bucket"), "fieldtype": "Data", "width": 90},
		{"fieldname": "current_cost", "label": _("Cost"), "fieldtype": "Currency", "width": 120},
	]
	data = get_data(filters)
	return columns, data, None, get_chart(data)


def bucket_for(days):
	if days <= 30:
		return "0-30"
	if days <= 60:
		return "31-60"
	if days <= 90:
		return "61-90"
	return "90+"


def get_data(filters):
	conditions = ["v.status in ('Available', 'Reserved')"]
	values = {}
	if filters.get("warehouse"):
		conditions.append("v.warehouse = %(warehouse)s")
		values["warehouse"] = filters["warehouse"]
	if filters.get("make"):
		conditions.append("v.make = %(make)s")
		values["make"] = filters["make"]
	rows = frappe.db.sql(
		"""
		select v.name as vehicle_unit, v.make, v.model, v.status, v.warehouse, v.current_cost,
			coalesce(min(r.posting_date), v.purchase_date) as received_on
		from `tabVehicle Unit` v
		left join `tabVehicle Receiving` r on r.vehicle_unit = v.name and r.docstatus = 1
		where {where}
		group by v.name
		""".format(where=" and ".join(conditions)),
		values,
		as_dict=True,
	)
	today = getdate(nowdate())
	for row in rows:
		received = getdate(row.received_on) if row.received_on else today
		row.days_in_stock = date_diff(today, received)
		row.age_bucket = bucket_for(max(row.days_in_stock, 0))
		row.current_cost = flt(row.current_cost)
	return rows


def get_chart(data):
	order = ["0-30", "31-60", "61-90", "90+"]
	counts = {label: 0 for label in order}
	for row in data:
		counts[row.age_bucket] += 1
	return {
		"data": {
			"labels": order,
			"datasets": [{"name": _("Units"), "values": [counts[label] for label in order]}],
		},
		"type": "bar",
		"height": 280,
	}
