# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe

from autods.principal_portal.web import (
	list_circulars,
	list_claims,
	list_orders,
	require_any_role,
	require_login,
)

no_cache = 1


def get_context(context):
	require_login("/dealers-portal")
	require_any_role("Dealer Portal User", "Dealers Portal User", "System Manager")
	context.no_cache = 1
	context.show_sidebar = False
	context.title = "Dealers Portal"
	context.orders = list_orders()
	context.claims = list_claims()
	context.circulars = list_circulars()
	context.user = frappe.session.user
