# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, nowdate


def execute(filters=None):
	columns = [
		{"fieldname": "document_type", "label": _("Document"), "fieldtype": "Data", "width": 160},
		{
			"fieldname": "document_name",
			"label": _("Name"),
			"fieldtype": "Dynamic Link",
			"options": "document_type",
			"width": 150,
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
			"fieldname": "salesperson",
			"label": _("Sales Person"),
			"fieldtype": "Link",
			"options": "Sales Person",
			"width": 140,
		},
		{"fieldname": "next_action", "label": _("Next Action"), "fieldtype": "Data", "width": 120},
		{"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "age_days", "label": _("Age (Days)"), "fieldtype": "Int", "width": 90},
	]
	data = get_data()
	return columns, data, None, get_chart(data)


def get_data():
	today = getdate(nowdate())
	rows = []
	quotes = frappe.db.sql(
		"""
		select name, party_name as customer, vehicle_unit, salesperson, grand_total, transaction_date, status
		from `tabVehicle Sales Quote`
		where docstatus = 1 and status in ('Open', 'Expired')
		""",
		as_dict=True,
	)
	for quote in quotes:
		rows.append(
			{
				"document_type": "Vehicle Sales Quote",
				"document_name": quote.name,
				"customer": quote.customer,
				"vehicle_unit": quote.vehicle_unit,
				"salesperson": quote.salesperson,
				"next_action": "Order",
				"amount": flt(quote.grand_total),
				"age_days": date_diff(today, getdate(quote.transaction_date))
				if quote.transaction_date
				else 0,
			}
		)
	orders = frappe.db.sql(
		"""
		select name, customer, vehicle_unit, salesperson, grand_total, transaction_date, status
		from `tabVehicle Sales Order`
		where docstatus = 1 and status not in ('Completed', 'Cancelled')
		""",
		as_dict=True,
	)
	for order in orders:
		action = "Deliver" if order.status in ("To Deliver", "To Deliver and Bill") else "Bill"
		if order.status == "To Bill":
			action = "Bill"
		rows.append(
			{
				"document_type": "Vehicle Sales Order",
				"document_name": order.name,
				"customer": order.customer,
				"vehicle_unit": order.vehicle_unit,
				"salesperson": order.salesperson,
				"next_action": action,
				"amount": flt(order.grand_total),
				"age_days": date_diff(today, getdate(order.transaction_date))
				if order.transaction_date
				else 0,
			}
		)
	return rows


def get_chart(data):
	if not data:
		return None
	counts = {}
	for row in data:
		counts[row["next_action"]] = counts.get(row["next_action"], 0) + 1
	labels = list(counts)
	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Documents"), "values": [counts[label] for label in labels]}],
		},
		"type": "donut",
		"height": 280,
	}
