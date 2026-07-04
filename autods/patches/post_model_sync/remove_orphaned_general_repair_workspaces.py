# Copyright (c) 2025, Agilasoft Technologies Inc.
# Remove orphaned Body Repair, General Repair, and Repair Workspace pages.
# Fixes SessionBootFailed when Module Def was removed but Workspace records remained.

from __future__ import annotations

import frappe


def execute():
	"""Remove Workspace pages that reference removed Body Repair / General Repair / Repair modules."""
	modules_to_remove = ["Body Repair", "General Repair", "Repair"]
	for workspace_name in frappe.get_all(
		"Workspace",
		filters={"module": ["in", modules_to_remove]},
		pluck="name",
	):
		if frappe.db.exists("Workspace", workspace_name):
			frappe.delete_doc("Workspace", workspace_name, force=True)
	frappe.db.commit()
