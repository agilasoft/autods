# Copyright (c) 2025, Agilasoft Technologies Inc.
# Remove Body Repair, General Repair, and Repair modules — consolidated into Service.
# Must run before model sync so Frappe doesn't try to load deleted module folders.

from __future__ import annotations

import frappe


def execute():
	"""Remove orphaned Body Repair, General Repair, and Repair Module Defs and Workspace pages."""
	modules_to_remove = ["Body Repair", "General Repair", "Repair"]

	# Delete Workspace pages that reference removed modules (prevents SessionBootFailed)
	for workspace_name in frappe.get_all(
		"Workspace",
		filters={"module": ["in", modules_to_remove]},
		pluck="name",
	):
		if frappe.db.exists("Workspace", workspace_name):
			frappe.delete_doc("Workspace", workspace_name, force=True)
	frappe.db.commit()

	# Delete Module Defs
	for module_name in modules_to_remove:
		if frappe.db.exists("Module Def", module_name):
			frappe.delete_doc("Module Def", module_name, force=True)
			frappe.db.commit()
