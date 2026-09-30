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
		{"fieldname": "selling_price", "label": _("Selling Price"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "discount_amount", "label": _("Discount"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "cost", "label": _("Cost Ledger"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "gross", "label": _("Gross"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "gross_percent", "label": _("Gross %"), "fieldtype": "Percent", "width": 90},
	]
	data = get_data(filters)
	return columns, data, None, get_chart(data)


def get_data(filters):
	conditions = ["d.docstatus = 1"]
	values = {}
	if filters.get("from_date"):
		conditions.append("d.posting_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("d.posting_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("make"):
		conditions.append("d.make = %(make)s")
		values["make"] = filters["make"]
	if filters.get("salesperson"):
		conditions.append("o.salesperson = %(salesperson)s")
		values["salesperson"] = filters["salesperson"]
	rows = frappe.db.sql(
		"""
		select d.name as delivery_note, d.posting_date, d.vehicle_unit, d.make,
			o.salesperson, d.net_total, d.discount_amount,
			abs(ifnull(l.amount, 0)) as cost
		from `tabVehicle Delivery Note` d
		left join `tabVehicle Sales Order` o on o.name = d.vehicle_sales_order
		left join `tabVehicle Cost Ledger` l
			on l.voucher_type = 'Vehicle Delivery Note' and l.voucher_no = d.name
			and l.cost_type = 'COGS' and l.docstatus = 1
		where {where}
		order by d.posting_date desc
		""".format(where=" and ".join(conditions)),
		values,
		as_dict=True,
	)
	for row in rows:
		selling = flt(row.net_total) - flt(row.discount_amount)
		row.selling_price = selling
		row.gross = selling - flt(row.cost)
		row.gross_percent = round(100 * row.gross / selling, 1) if selling else 0
	return rows


def get_chart(data):
	if not data:
		return None
	by_make = {}
	for row in data:
		make = row.make or _("(No make)")
		by_make[make] = by_make.get(make, 0) + flt(row.gross)
	labels = list(by_make)
	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Gross"), "values": [by_make[label] for label in labels]}],
		},
		"type": "bar",
		"height": 280,
	}
