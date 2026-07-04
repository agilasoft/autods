# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe


def execute():
	if frappe.db.exists("DocType", "Service Category"):
		frappe.delete_doc("DocType", "Service Category", force=True, ignore_on_trash=True)
	frappe.clear_cache()
