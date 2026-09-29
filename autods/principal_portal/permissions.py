# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.utils import cint

from autods.principal_portal.utils import (
	get_default_principal,
	get_site_role,
	get_user_dealer,
	get_user_principal,
	is_system_manager,
	user_roles,
)


def _escape(value):
	return frappe.db.escape(value)


def _is_privileged(user):
	roles = user_roles(user)
	return is_system_manager(user) or "Dealers Portal User" in roles


def _dealer_filter(table, user):
	dealer = get_user_dealer(user)
	if not dealer:
		return "1=0"
	return f"`tab{table}`.dealer = {_escape(dealer)}"


def _principal_filter(table, user):
	principal = get_user_principal(user) or get_default_principal()
	if not principal:
		return ""
	return f"`tab{table}`.principal = {_escape(principal)}"


def get_permission_query_conditions_for_order(user=None):
	return _transaction_conditions("Principal Order", user)


def get_permission_query_conditions_for_claim(user=None):
	return _transaction_conditions("Warranty Claim", user)


def _transaction_conditions(doctype, user=None):
	user = user or frappe.session.user
	if user == "Administrator" or _is_privileged(user):
		return ""
	roles = user_roles(user)
	site_role = get_site_role()
	if "Dealer Portal User" in roles:
		return _dealer_filter(doctype, user)
	if "Principal Portal User" in roles:
		if site_role == "Dealer":
			return _principal_filter(doctype, user)
		return _dealer_filter(doctype, user) if get_user_dealer(user) else ""
	if "Portal Sync User" in roles:
		return ""
	return "1=0"


def has_permission_transaction(doc, user=None, ptype=None, **kwargs):
	user = user or frappe.session.user
	if user == "Administrator" or _is_privileged(user):
		return True
	roles = user_roles(user)
	if "Portal Sync User" in roles:
		return True
	dealer = getattr(doc, "dealer", None)
	principal = getattr(doc, "principal", None)
	if "Dealer Portal User" in roles:
		mapped = get_user_dealer(user)
		return bool(mapped and dealer == mapped)
	if "Principal Portal User" in roles:
		if get_site_role() == "Dealer":
			mapped = get_user_principal(user) or get_default_principal()
			return (not mapped) or principal == mapped
		mapped = get_user_dealer(user)
		return (not mapped) or dealer == mapped
	return False


def get_permission_query_conditions_for_circular(user=None):
	user = user or frappe.session.user
	if user == "Administrator" or _is_privileged(user):
		return ""
	roles = user_roles(user)
	if "Principal Portal User" in roles and get_site_role() == "Dealer":
		return ""
	if "Dealer Portal User" in roles:
		dealer = get_user_dealer(user)
		if not dealer:
			return "1=0"
		escaped = _escape(dealer)
		return (
			"(`tabDealer Circular`.audience = 'All Dealers' or `tabDealer Circular`.name in "
			f"(select parent from `tabDealer Circular Recipient` where dealer = {escaped}))"
		)
	if "Portal Sync User" in roles:
		return ""
	return "1=0"


def has_permission_circular(doc, user=None, ptype=None, **kwargs):
	user = user or frappe.session.user
	if user == "Administrator" or _is_privileged(user):
		return True
	roles = user_roles(user)
	if "Portal Sync User" in roles or "Principal Portal User" in roles:
		return True
	if "Dealer Portal User" in roles:
		dealer = get_user_dealer(user)
		if not dealer:
			return False
		if doc.audience == "All Dealers":
			return True
		return any(row.dealer == dealer for row in (doc.get("recipients") or []))
	return False


def get_permission_query_conditions_for_connection(user=None):
	user = user or frappe.session.user
	if user == "Administrator" or is_system_manager(user) or "Dealers Portal User" in user_roles(user):
		return ""
	if "Principal Portal User" in user_roles(user):
		principal = get_user_principal(user) or get_default_principal()
		if not principal:
			return ""
		return f"(`tabPortal Connection`.party_type = 'Principal' and `tabPortal Connection`.party = {_escape(principal)})"
	return "1=0"


def has_permission_connection(doc, user=None, ptype=None, **kwargs):
	user = user or frappe.session.user
	if user == "Administrator" or is_system_manager(user) or "Dealers Portal User" in user_roles(user):
		return True
	if "Principal Portal User" in user_roles(user):
		principal = get_user_principal(user) or get_default_principal()
		if not principal:
			return True
		return doc.party_type == "Principal" and doc.party == principal
	return False


def get_permission_query_conditions_for_sync_log(user=None):
	user = user or frappe.session.user
	roles = user_roles(user)
	if (
		user == "Administrator"
		or is_system_manager(user)
		or "Dealers Portal User" in roles
		or "Principal Portal User" in roles
	):
		return ""
	return "1=0"


def has_permission_sync_log(doc, user=None, ptype=None, **kwargs):
	user = user or frappe.session.user
	roles = user_roles(user)
	if (
		user == "Administrator"
		or is_system_manager(user)
		or "Dealers Portal User" in roles
		or "Principal Portal User" in roles
	):
		return True
	return False


def apply_party_filters(filters, user=None):
	"""Restrict website/list queries the same way as desk permissions."""
	filters = dict(filters or {})
	user = user or frappe.session.user
	if user == "Administrator" or _is_privileged(user):
		return filters
	roles = user_roles(user)
	if "Dealer Portal User" in roles:
		dealer = get_user_dealer(user)
		if dealer:
			filters["dealer"] = dealer
		else:
			filters["name"] = "__no_match__"
	elif "Principal Portal User" in roles and get_site_role() == "Dealer":
		principal = get_user_principal(user) or get_default_principal()
		if principal:
			filters["principal"] = principal
	return filters
