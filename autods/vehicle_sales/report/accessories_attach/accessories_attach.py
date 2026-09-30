# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = [
		{
			"fieldname": "delivery_note",
			"label": _("Delivery"),
			"fieldtype": "Link",
			"options": "Vehicle Delivery Note",
			"width": 140,
		},
		{"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{
			"fieldname": "vehicle_unit",
			"label": _("Vehicle"),
			"fieldtype": "Link",
			"options": "Vehicle Unit",
			"width": 140,
		},
		{"fieldname": "base_price", "label": _("Base Price"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "accessories_total", "label": _("Accessories"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "attach_percent", "label": _("Attach %"), "fieldtype": "Percent", "width": 100},
	]
	conditions = ["docstatus = 1"]
	values = {}
	if filters.get("from_date"):
		conditions.append("posting_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("posting_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	rows = frappe.db.sql(
		"""
		select name as delivery_note, posting_date, vehicle_unit, base_price, accessories_total
		from `tabVehicle Delivery Note`
		where {where}
		order by posting_date desc
		""".format(where=" and ".join(conditions)),
		values,
		as_dict=True,
	)
	for row in rows:
		base = flt(row.base_price)
		row.attach_percent = round(100 * flt(row.accessories_total) / base, 1) if base else 0
	return columns, rows, None, get_chart(rows)


def get_chart(rows):
	if not rows:
		return None
	return {
		"data": {
			"labels": [_("Base"), _("Accessories")],
			"datasets": [
				{
					"name": _("Amount"),
					"values": [
						sum(flt(row.base_price) for row in rows),
						sum(flt(row.accessories_total) for row in rows),
					],
				}
			],
		},
		"type": "donut",
		"height": 280,
	}
