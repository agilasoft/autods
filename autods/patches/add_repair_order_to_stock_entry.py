# Copyright (c) 2026, Agilasoft Technologies Inc.
# Add Repair Order link to Stock Entry for Job Card / Repair Order referencing.

import frappe


def execute():
	"""Add custom field repair_order on Stock Entry if missing."""
	if frappe.db.exists("Custom Field", "Stock Entry-repair_order"):
		return
	frappe.get_doc({
		"doctype": "Custom Field",
		"dt": "Stock Entry",
		"fieldname": "repair_order",
		"label": "Repair Order",
		"fieldtype": "Link",
		"options": "Repair Order",
		"insert_after": "job_card",
		"read_only": 1,
		"print_hide": 1,
	}).insert()
