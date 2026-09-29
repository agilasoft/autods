# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from autods.principal_portal.utils import ROLES

USER_CUSTOM_FIELDS = {
	"User": [
		{
			"fieldname": "custom_portal_party_section",
			"label": "Principal / Dealer Portal",
			"fieldtype": "Section Break",
			"insert_after": "roles",
			"collapsible": 1,
		},
		{
			"fieldname": "custom_dealer",
			"label": "Dealer",
			"fieldtype": "Link",
			"options": "Dealer",
			"insert_after": "custom_portal_party_section",
			"description": "Scopes Dealer Portal User logins to this dealer on a principal site.",
		},
		{
			"fieldname": "custom_principal",
			"label": "Principal",
			"fieldtype": "Link",
			"options": "Principal",
			"insert_after": "custom_dealer",
			"description": "Scopes Principal Portal User logins to this principal on a dealer site.",
		},
	]
}

DEFAULT_SETTINGS = {
	"enqueue_on_submit": "1",
	"max_sync_retries": "5",
	"principal_order_naming_series": "POR-.YYYY.-",
	"warranty_claim_naming_series": "WCL-.YYYY.-",
	"dealer_circular_naming_series": "CIR-.YYYY.-",
}


def ensure_roles():
	for role_name in ROLES:
		if frappe.db.exists("Role", role_name):
			if role_name == "Portal Sync User":
				frappe.db.set_value("Role", role_name, "desk_access", 0)
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 0 if role_name == "Portal Sync User" else 1,
			}
		)
		doc.insert(ignore_permissions=True)


def install_custom_fields():
	if not frappe.db.exists("DocType", "User"):
		return
	create_custom_fields(USER_CUSTOM_FIELDS, ignore_validate=True, update=True)


def initialize_settings():
	if not frappe.db.exists("DocType", "Principal Dealer Settings"):
		return
	try:
		for fieldname, default in DEFAULT_SETTINGS.items():
			existing = frappe.db.sql(
				"SELECT value FROM tabSingles WHERE doctype=%s AND field=%s",
				("Principal Dealer Settings", fieldname),
			)
			if not existing:
				frappe.db.sql(
					"INSERT INTO tabSingles (doctype, field, value) VALUES (%s, %s, %s)",
					("Principal Dealer Settings", fieldname, default),
				)
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "AutoDS: principal portal initialize_settings failed")


def after_install():
	ensure_roles()
	try:
		install_custom_fields()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "AutoDS: principal portal install_custom_fields failed")
	initialize_settings()


def after_migrate():
	after_install()
