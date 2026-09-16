# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from autods.principal_portal.permissions import apply_party_filters
from autods.principal_portal.utils import user_roles


def require_login(redirect_to):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = f"/login?redirect-to={redirect_to}"
		raise frappe.Redirect


def require_any_role(*roles):
	current = user_roles()
	if "System Manager" in current:
		return
	if not any(role in current for role in roles):
		frappe.throw(_("You do not have access to this portal."), frappe.PermissionError)


def list_orders(limit=20):
	filters = apply_party_filters({"docstatus": ["<", 2]})
	return frappe.get_all(
		"Principal Order",
		filters=filters,
		fields=[
			"name",
			"order_date",
			"order_type",
			"status",
			"net_total",
			"principal",
			"dealer",
			"sync_status",
		],
		order_by="modified desc",
		limit=limit,
	)


def list_claims(limit=20):
	filters = apply_party_filters({"docstatus": ["<", 2]})
	return frappe.get_all(
		"Warranty Claim",
		filters=filters,
		fields=["name", "claim_date", "status", "vin", "claim_amount", "principal", "dealer", "sync_status"],
		order_by="modified desc",
		limit=limit,
	)


def list_circulars(limit=10):
	filters = {"published": 1}
	return frappe.get_all(
		"Dealer Circular",
		filters=filters,
		fields=["name", "title", "published_on"],
		order_by="published_on desc",
		limit=limit,
	)


def get_order(name):
	if not name:
		frappe.throw(_("Order is required."))
	doc = frappe.get_doc("Principal Order", name)
	doc.check_permission("read")
	return doc


def get_claim(name):
	if not name:
		frappe.throw(_("Claim is required."))
	doc = frappe.get_doc("Warranty Claim", name)
	doc.check_permission("read")
	return doc
