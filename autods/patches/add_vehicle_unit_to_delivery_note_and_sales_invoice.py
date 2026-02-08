# Copyright (c) 2026, Agilasoft Technologies Inc.
# Add Vehicle Sales and Vehicle Unit references to Delivery Note and Sales Invoice.

import frappe


def execute():
	for dt in ("Delivery Note", "Sales Invoice"):
		_add_vehicle_sales_field(dt)
		_add_vehicle_unit_field(dt)


def _add_vehicle_sales_field(dt):
	fieldname = "custom_vehicle_sales"
	if frappe.db.exists("Custom Field", f"{dt}-{fieldname}"):
		return
	frappe.get_doc({
		"doctype": "Custom Field",
		"dt": dt,
		"fieldname": fieldname,
		"label": "Vehicle Sales",
		"fieldtype": "Check",
		"insert_after": "customer_name",
		"in_standard_filter": 1,
		"module": "Vehicle Sales",
	}).insert()


def _add_vehicle_unit_field(dt):
	fieldname = "custom_vehicle_unit"
	if frappe.db.exists("Custom Field", f"{dt}-{fieldname}"):
		return
	frappe.get_doc({
		"doctype": "Custom Field",
		"dt": dt,
		"fieldname": fieldname,
		"label": "Vehicle Unit",
		"fieldtype": "Link",
		"options": "Vehicle Unit",
		"insert_after": "custom_vehicle_sales",
		"depends_on": "eval:doc.custom_vehicle_sales",
		"in_standard_filter": 1,
		"module": "Vehicle Sales",
	}).insert()
