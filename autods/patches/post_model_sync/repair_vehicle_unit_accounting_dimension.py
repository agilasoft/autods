# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt
#
# The Vehicle Unit Accounting Dimension was previously registered (see
# autods/patches/add_vehicle_unit_accounting_dimension.py) but on some sites
# the auto-injection of the `vehicle_unit` column did not reach every relevant
# doctype - in particular Budget. This patch re-runs
# ``make_dimension_in_accounting_doctypes`` so the column is created everywhere
# ERPNext expects it (Budget, GL Entry, etc.). Without this, Sales Invoice
# submit fails with "Unknown column 'vehicle_unit' in 'SELECT'" inside the
# ERPNext Budget controller.

import frappe


def execute():
	if not frappe.db.exists("DocType", "Accounting Dimension"):
		return
	dim_name = frappe.db.get_value(
		"Accounting Dimension", {"document_type": "Vehicle Unit"}, "name"
	)
	if not dim_name:
		return
	try:
		from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
			make_dimension_in_accounting_doctypes,
		)
	except Exception:
		# ERPNext not available or function moved; nothing we can do here.
		return
	try:
		dim = frappe.get_doc("Accounting Dimension", dim_name)
		make_dimension_in_accounting_doctypes(dim)
		frappe.db.commit()
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			"AutoDS: repair_vehicle_unit_accounting_dimension failed",
		)
