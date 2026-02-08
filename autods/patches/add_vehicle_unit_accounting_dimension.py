# Copyright (c) 2026, Agilasoft Technologies Inc.
# Add Vehicle Unit as an Accounting Dimension so P&L, inventory cost and movements
# can be tracked per vehicle unit. The dimension is auto-populated from serial numbers.

import frappe


def execute():
	if frappe.db.exists("Accounting Dimension", {"document_type": "Vehicle Unit"}):
		return
	# Create Accounting Dimension; after_insert will add vehicle_unit field to all
	# doctypes in accounting_dimension_doctypes hook (Sales Invoice, Delivery Note,
	# Stock Entry, Purchase Receipt, GL Entry, etc.)
	dim = frappe.new_doc("Accounting Dimension")
	dim.document_type = "Vehicle Unit"
	dim.label = "Vehicle Unit"
	dim.fieldname = "vehicle_unit"
	dim.insert()
