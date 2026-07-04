# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Drop child DocTypes removed from Repair Order (replaced by Service Inspection flow)."""
	for name in (
		"Repair Order PreRepair Inspection",
		"Repair Order Diagnostic Inspection",
		"GR Order Diagnostic Inspection",
	):
		if frappe.db.exists("DocType", name):
			frappe.delete_doc("DocType", name, force=1)
