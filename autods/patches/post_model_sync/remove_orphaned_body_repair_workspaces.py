# Copyright (c) 2025, Agilasoft Technologies Inc.
# Catch-all for Body Repair workspaces if Module Def was removed without workspace cleanup.

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
