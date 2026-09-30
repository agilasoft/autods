# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = [
		{
			"fieldname": "salesperson",
			"label": _("Sales Person"),
			"fieldtype": "Link",
			"options": "Sales Person",
			"width": 160,
		},
		{"fieldname": "quotes", "label": _("Quotes"), "fieldtype": "Int", "width": 90},
		{"fieldname": "orders", "label": _("Orders"), "fieldtype": "Int", "width": 90},
		{"fieldname": "deliveries", "label": _("Deliveries"), "fieldtype": "Int", "width": 100},
		{"fieldname": "quote_to_order", "label": _("Quote to Order %"), "fieldtype": "Percent", "width": 140},
		{
			"fieldname": "order_to_delivery",
			"label": _("Order to Delivery %"),
			"fieldtype": "Percent",
			"width": 150,
		},
	]
	data = get_data(filters)
	return columns, data, None, get_chart(data)


def get_data(filters):
	values = {}
	q_cond = ["docstatus = 1", "status != 'Cancelled'"]
	o_cond = ["docstatus = 1", "status != 'Cancelled'"]
	d_cond = ["d.docstatus = 1"]
	if filters.get("from_date"):
		q_cond.append("transaction_date >= %(from_date)s")
		o_cond.append("transaction_date >= %(from_date)s")
		d_cond.append("d.posting_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		q_cond.append("transaction_date <= %(to_date)s")
		o_cond.append("transaction_date <= %(to_date)s")
		d_cond.append("d.posting_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	quotes = frappe.db.sql(
		"select ifnull(salesperson, '') as salesperson, count(*) as quotes from `tabVehicle Sales Quote` where "
		+ " and ".join(q_cond)
		+ " group by salesperson",
		values,
		as_dict=True,
	)
	orders = frappe.db.sql(
		"select ifnull(salesperson, '') as salesperson, count(*) as orders from `tabVehicle Sales Order` where "
		+ " and ".join(o_cond)
		+ " group by salesperson",
		values,
		as_dict=True,
	)
	deliveries = frappe.db.sql(
		"""
		select ifnull(o.salesperson, '') as salesperson, count(*) as deliveries
		from `tabVehicle Delivery Note` d
		left join `tabVehicle Sales Order` o on o.name = d.vehicle_sales_order
		where """
		+ " and ".join(d_cond)
		+ " group by salesperson",
		values,
		as_dict=True,
	)
	people = {}
	for row in quotes:
		people.setdefault(
			row.salesperson,
			{"salesperson": row.salesperson or None, "quotes": 0, "orders": 0, "deliveries": 0},
		)
		people[row.salesperson]["quotes"] = row.quotes
	for row in orders:
		people.setdefault(
			row.salesperson,
			{"salesperson": row.salesperson or None, "quotes": 0, "orders": 0, "deliveries": 0},
		)
		people[row.salesperson]["orders"] = row.orders
	for row in deliveries:
		people.setdefault(
			row.salesperson,
			{"salesperson": row.salesperson or None, "quotes": 0, "orders": 0, "deliveries": 0},
		)
		people[row.salesperson]["deliveries"] = row.deliveries
	data = []
	for row in people.values():
		row["quote_to_order"] = round(100 * row["orders"] / row["quotes"], 1) if row["quotes"] else 0
		row["order_to_delivery"] = round(100 * row["deliveries"] / row["orders"], 1) if row["orders"] else 0
		data.append(row)
	return data


def get_chart(data):
	if not data:
		return None
	labels = [row["salesperson"] or _("Unassigned") for row in data]
	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Quotes"), "values": [row["quotes"] for row in data]},
				{"name": _("Orders"), "values": [row["orders"] for row in data]},
				{"name": _("Deliveries"), "values": [row["deliveries"] for row in data]},
			],
		},
		"type": "bar",
		"height": 280,
	}
