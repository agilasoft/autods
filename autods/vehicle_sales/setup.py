# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# Setup module: creates / updates the custom fields and property setters that
# integrate the standard ERPNext doctypes (Item, Sales Invoice, Purchase Order)
# with the Vehicle Sales pipeline. Idempotent; safe to run on every migrate.

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


CUSTOM_FIELDS = {
	"Item": [
		{
			"fieldname": "custom_vehicle_item",
			"label": "Vehicle Item",
			"fieldtype": "Check",
			"insert_after": "is_fixed_asset",
			"description": (
				"If checked, this Item is routed through the Vehicle Sales pipeline "
				"(Vehicle Sales Quote / Order / Delivery Note / Receiving) instead of the standard "
				"Quotation / Sales Order / Delivery Note / Purchase Receipt."
			),
		},
	],
	"Sales Invoice": [
		{
			"fieldname": "custom_vehicle_sales_section",
			"label": "Vehicle Sales",
			"fieldtype": "Section Break",
			"insert_after": "more_info",
			"collapsible": 1,
		},
		{
			"fieldname": "custom_vehicle_sales",
			"label": "Vehicle Sales",
			"fieldtype": "Check",
			"insert_after": "custom_vehicle_sales_section",
			"description": "Auto-set when this invoice is for a Vehicle Sales transaction.",
		},
		{
			"fieldname": "vehicle_unit",
			"label": "Vehicle Unit",
			"fieldtype": "Link",
			"options": "Vehicle Unit",
			"insert_after": "custom_vehicle_sales",
		},
		{
			"fieldname": "custom_vehicle_sales_col",
			"fieldtype": "Column Break",
			"insert_after": "vehicle_unit",
		},
		{
			"fieldname": "vehicle_sales_order",
			"label": "Vehicle Sales Order",
			"fieldtype": "Link",
			"options": "Vehicle Sales Order",
			"insert_after": "custom_vehicle_sales_col",
		},
		{
			"fieldname": "vehicle_delivery_note",
			"label": "Vehicle Delivery Note",
			"fieldtype": "Link",
			"options": "Vehicle Delivery Note",
			"insert_after": "vehicle_sales_order",
		},
	],
	"Purchase Order": [
		{
			"fieldname": "custom_vehicle_po_section",
			"label": "Vehicle Sales",
			"fieldtype": "Section Break",
			"insert_after": "more_info",
			"collapsible": 1,
		},
		{
			"fieldname": "is_vehicle_po",
			"label": "Vehicle Purchase Order",
			"fieldtype": "Check",
			"insert_after": "custom_vehicle_po_section",
			"description": "Auto-flagged when items on this PO have 'Vehicle Item' enabled. Receive via Vehicle Receiving.",
			"read_only": 1,
		},
		{
			"fieldname": "vehicle_receiving_status",
			"label": "Vehicle Receiving Status",
			"fieldtype": "Select",
			"options": "\nPending\nPartially Received\nFully Received",
			"insert_after": "is_vehicle_po",
			"read_only": 1,
		},
	],
}


def install_custom_fields():
	"""Idempotently create / update all Vehicle Sales-related custom fields."""
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True, update=True)


DEFAULT_FLAGS = {
	"block_vehicle_items_in_standard_flow": "1",
	"auto_post_je": "1",
	"auto_create_vehicle_unit": "1",
}

DEFAULT_NAMING = {
	"vehicle_quote_naming_series": "VSQ-.YYYY.-",
	"vehicle_sales_order_naming_series": "VSO-.YYYY.-",
	"vehicle_delivery_naming_series": "VDN-.YYYY.-",
	"vehicle_receiving_naming_series": "VRC-.YYYY.-",
	"vehicle_cost_ledger_naming_series": "VCL-.YYYY.-",
}


def initialize_settings():
	"""Ensure the Vehicle Sales Settings singleton has the expected default values.

	Writes directly to ``tabSingles`` so that ``frappe.db.get_single_value(...)``
	returns the right defaults even before a user has opened the form.
	Idempotent: only fills in fields that have no value yet.
	"""
	if not frappe.db.exists("DocType", "Vehicle Sales Settings"):
		return
	try:
		for fieldname, default in {**DEFAULT_FLAGS, **DEFAULT_NAMING}.items():
			existing = frappe.db.sql(
				"SELECT value FROM tabSingles WHERE doctype=%s AND field=%s",
				("Vehicle Sales Settings", fieldname),
			)
			if not existing:
				frappe.db.sql(
					"INSERT INTO tabSingles (doctype, field, value) VALUES (%s, %s, %s)",
					("Vehicle Sales Settings", fieldname, default),
				)
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "AutoDS: initialize_settings failed")


def after_migrate():
	"""Run on every ``bench migrate`` to keep custom fields and settings in sync."""
	try:
		install_custom_fields()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "AutoDS: install_custom_fields failed")
	initialize_settings()


def after_install():
	install_custom_fields()
	initialize_settings()
