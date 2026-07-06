# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Remove unused Item custom field custom_applicable_all_vehicle_units.

	Parts compatibility is handled via Parts Compatibility (applies_to_all_vehicles),
	not an Item-level checkbox. This field was never wired into link queries or validation.
	"""
	fieldname = "Item-custom_applicable_all_vehicle_units"
	if frappe.db.exists("Custom Field", fieldname):
		frappe.delete_doc("Custom Field", fieldname, force=True, ignore_on_trash=True)

	if frappe.db.has_column("Item", "custom_applicable_all_vehicle_units"):
		frappe.db.sql("ALTER TABLE `tabItem` DROP COLUMN `custom_applicable_all_vehicle_units`")

	frappe.clear_cache(doctype="Item")
