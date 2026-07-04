# Copyright (c) 2025, Agilasoft Technologies Inc.
# Remove Body Repair module — consolidated into Service.
# Separate patch so sites that already ran remove_general_repair_and_repair_modules still execute this once.

from __future__ import annotations

import frappe


def execute():
	modules_to_remove = ["Body Repair"]

	for workspace_name in frappe.get_all(
		"Workspace",
		filters={"module": ["in", modules_to_remove]},
		pluck="name",
	):
		if frappe.db.exists("Workspace", workspace_name):
			frappe.delete_doc("Workspace", workspace_name, force=True)
	frappe.db.commit()

	for module_name in modules_to_remove:
		if frappe.db.exists("Module Def", module_name):
			frappe.delete_doc("Module Def", module_name, force=True)
			frappe.db.commit()
