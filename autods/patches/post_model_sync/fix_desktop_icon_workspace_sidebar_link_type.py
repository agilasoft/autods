# Copyright (c) 2026, Agilasoft Technologies Inc.
# Desktop icons must use link_type "Workspace Sidebar" so the desk home page can
# resolve a route from Workspace Sidebar items (see frappe/desk/page/desktop/desktop.js get_route).

from __future__ import annotations

import frappe

from frappe.desk.doctype.desktop_icon.desktop_icon import clear_desktop_icons_cache


def execute():
	"""Fix invalid Desktop Icon link_type values stored as Workspace."""
	# Historical exports used "Workspace"; Frappe only supports Workspace Sidebar / External.
	for row in frappe.get_all(
		"Desktop Icon",
		filters={"link_type": "Workspace"},
		fields=["name"],
	):
		frappe.db.set_value("Desktop Icon", row.name, "link_type", "Workspace Sidebar")
	clear_desktop_icons_cache()
	frappe.db.commit()
