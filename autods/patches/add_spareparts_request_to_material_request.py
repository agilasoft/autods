# Copyright (c) 2026, Agilasoft Technologies Inc.
# Add Repair Order link to Material Request and Stock Entry for referencing (Job Card + Repair Order).

import frappe


def execute():
	"""Add custom fields repair_order on Material Request and Stock Entry if missing."""
	if not frappe.db.exists("Custom Field", "Material Request-repair_order"):
		frappe.get_doc({
			"doctype": "Custom Field",
			"dt": "Material Request",
			"fieldname": "repair_order",
			"label": "Repair Order",
			"fieldtype": "Link",
			"options": "Repair Order",
			"insert_after": "job_card",
			"read_only": 1,
			"print_hide": 1,
		}).insert()

	if not frappe.db.exists("Custom Field", "Stock Entry-repair_order"):
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
