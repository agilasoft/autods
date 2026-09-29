# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe

from autods.principal_portal.web import get_claim, require_any_role, require_login

no_cache = 1


def get_context(context):
	require_login("/principal-portal")
	require_any_role("Principal Portal User", "System Manager")
	name = frappe.form_dict.get("name")
	doc = get_claim(name)
	context.no_cache = 1
	context.show_sidebar = False
	context.title = doc.name
	context.doc = doc
	context.back_href = "/principal-portal"
