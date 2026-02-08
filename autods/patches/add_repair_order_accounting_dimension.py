# Copyright (c) 2026, Agilasoft Technologies Inc.
# Add Repair Order as an Accounting Dimension so revenue and costs can be tracked
# per repair order. Sales Invoice, Stock Entry, and Journal Entry (labor/standard costs)
# are tagged with Repair Order and Vehicle Unit dimensions.

import frappe


def execute():
	if frappe.db.exists("Accounting Dimension", {"document_type": "Repair Order"}):
		return
	dim = frappe.new_doc("Accounting Dimension")
	dim.document_type = "Repair Order"
	dim.label = "Repair Order"
	dim.fieldname = "repair_order"
	dim.insert()
