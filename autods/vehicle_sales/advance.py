# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Sync Vehicle Sales Order.advance_paid from Payment Entry.

Counts three sources, without double-counting a deposit that was later allocated:

1. Allocations against Sales Invoices of the order.
2. Allocations whose reference is the Vehicle Sales Order itself.
3. Unallocated paid amount on a Payment Entry tagged with vehicle_sales_order.
"""

import frappe
from frappe.utils import flt


def on_payment_entry_update(doc, method=None):
	orders = _orders_touched_by_payment(doc)
	for name in orders:
		if frappe.db.exists("Vehicle Sales Order", name):
			update_order_advance(name)


def _orders_touched_by_payment(doc):
	orders = set()
	tagged = doc.get("vehicle_sales_order")
	if tagged:
		orders.add(tagged)
	for row in doc.get("references") or []:
		if row.reference_doctype == "Vehicle Sales Order" and row.reference_name:
			orders.add(row.reference_name)
		elif row.reference_doctype == "Sales Invoice" and row.reference_name:
			order = frappe.db.get_value("Sales Invoice", row.reference_name, "vehicle_sales_order")
			if order:
				orders.add(order)
	return orders


def update_order_advance(order_name):
	total = compute_advance_paid(order_name)
	frappe.db.set_value(
		"Vehicle Sales Order",
		order_name,
		"advance_paid",
		total,
		update_modified=False,
	)
	return total


def compute_advance_paid(order_name):
	if not order_name or not frappe.db.table_exists("Payment Entry"):
		return 0

	invoice_allocated = flt(
		frappe.db.sql(
			"""
			SELECT COALESCE(SUM(per.allocated_amount), 0)
			FROM `tabPayment Entry Reference` per
			INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent AND pe.docstatus = 1
			INNER JOIN `tabSales Invoice` si ON si.name = per.reference_name AND si.docstatus = 1
			WHERE per.reference_doctype = 'Sales Invoice'
				AND si.vehicle_sales_order = %s
			""",
			order_name,
		)[0][0]
	)

	order_allocated = 0
	if frappe.db.has_column("Payment Entry Reference", "reference_doctype"):
		order_allocated = flt(
			frappe.db.sql(
				"""
				SELECT COALESCE(SUM(per.allocated_amount), 0)
				FROM `tabPayment Entry Reference` per
				INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent AND pe.docstatus = 1
				WHERE per.reference_doctype = 'Vehicle Sales Order'
					AND per.reference_name = %s
				""",
				order_name,
			)[0][0]
		)

	unallocated_deposit = 0
	if frappe.db.has_column("Payment Entry", "vehicle_sales_order"):
		unallocated_deposit = flt(
			frappe.db.sql(
				"""
				SELECT COALESCE(SUM(
					pe.paid_amount - COALESCE((
						SELECT SUM(per.allocated_amount)
						FROM `tabPayment Entry Reference` per
						WHERE per.parent = pe.name
					), 0)
				), 0)
				FROM `tabPayment Entry` pe
				WHERE pe.docstatus = 1 AND pe.vehicle_sales_order = %s
				""",
				order_name,
			)[0][0]
		)
		if unallocated_deposit < 0:
			unallocated_deposit = 0

	return invoice_allocated + order_allocated + unallocated_deposit
