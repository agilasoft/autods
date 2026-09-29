# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

ROLES = (
	"Principal Portal User",
	"Dealers Portal User",
	"Dealer Portal User",
	"Portal Sync User",
)

ORDER_STATUSES = (
	"Draft",
	"Submitted",
	"Confirmed",
	"Partially Delivered",
	"Delivered",
	"Closed",
	"Cancelled",
)

CLAIM_STATUSES = (
	"Draft",
	"Submitted",
	"Under Review",
	"Approved",
	"Rejected",
	"Settled",
)

SYNCABLE_DOCTYPES = ("Principal Order", "Warranty Claim", "Dealer Circular")


def get_settings():
	"""Return Principal Dealer Settings singleton, or None if the DocType is missing."""
	if not frappe.db.exists("DocType", "Principal Dealer Settings"):
		return None
	try:
		return frappe.get_cached_doc("Principal Dealer Settings")
	except Exception:
		return None


def get_site_role():
	settings = get_settings()
	return (settings.site_role if settings else "") or ""


def get_party_code():
	settings = get_settings()
	return (settings.party_code if settings else "") or ""


def get_default_principal():
	settings = get_settings()
	return (settings.default_principal if settings else "") or ""


def enqueue_on_submit_enabled():
	settings = get_settings()
	if not settings:
		return True
	return bool(settings.enqueue_on_submit)


def max_sync_retries():
	settings = get_settings()
	try:
		return int(settings.max_sync_retries) if settings and settings.max_sync_retries else 5
	except (TypeError, ValueError):
		return 5


def get_user_dealer(user=None):
	user = user or frappe.session.user
	if user in ("Guest", "Administrator"):
		return None
	try:
		return frappe.db.get_value("User", user, "custom_dealer")
	except Exception:
		return None


def get_user_principal(user=None):
	user = user or frappe.session.user
	if user in ("Guest",):
		return None
	try:
		return frappe.db.get_value("User", user, "custom_principal")
	except Exception:
		return None


def require_site_role(expected):
	role = get_site_role()
	if role and role != expected:
		frappe.throw(_("This action is only available when Site Role is {0}.").format(expected))


def user_roles(user=None):
	user = user or frappe.session.user
	try:
		return set(frappe.get_roles(user))
	except Exception:
		return set()


def is_system_manager(user=None):
	return "System Manager" in user_roles(user)


def is_sync_user(user=None):
	return "Portal Sync User" in user_roles(user)


def party_code_for(doctype, name):
	if not doctype or not name:
		return None
	return frappe.db.get_value(doctype, name, "code")
