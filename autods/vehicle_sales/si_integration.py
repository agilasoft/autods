# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# Sales Invoice integration for the Vehicle Sales pipeline.
#
# Standard Sales Invoice is kept (no Vehicle Sales Invoice doctype). When SI
# carries a vehicle (set via the `vehicle_unit`, `vehicle_sales_order` or
# `vehicle_delivery_note` custom field), this module:
#   - normalizes the cross-references (SI <-> VSO <-> VDN), regardless of which
#     was created first;
#   - requires `update_stock = 0` (vehicle stock is managed by Vehicle Receiving
#     and Vehicle Delivery Note, not the SI);
#   - sets `custom_vehicle_sales = 1`;
#   - on submit, writes back the SI link onto the Vehicle Unit and triggers the
#     Vehicle Sales Order billing-status recompute.

import frappe
from frappe import _


def _meta_has(dt, field):
	try:
		return frappe.get_meta(dt, cached=True).has_field(field)
	except Exception:
		return False


def _has_vehicle_sale_markers(doc):
	"""True when this invoice was created as a vehicle sale, not only tagged with a vehicle unit."""
	return bool(
		doc.get("custom_vehicle_sales")
		or doc.get("vehicle_sales_order")
		or doc.get("vehicle_delivery_note")
	)


def _is_repair_service_invoice(doc):
	return bool(doc.get("repair_order") or doc.get("custom_repair_bill_type"))


def _is_vehicle_sale(doc):
	"""Return True if this SI is part of a Vehicle Sales transaction.

	A Repair Order invoice also carries vehicle_unit (the car being repaired). That
	must not write the service invoice onto Vehicle Unit.sales_invoice.
	"""
	if _is_repair_service_invoice(doc) and not _has_vehicle_sale_markers(doc):
		return False
	if doc.get("custom_vehicle_sales"):
		return True
	if doc.get("vehicle_unit") or doc.get("vehicle_sales_order") or doc.get("vehicle_delivery_note"):
		return True
	# Any line item with a vehicle-tagged item?
	for row in doc.get("items") or []:
		if not row.get("item_code"):
			continue
		if frappe.db.get_value("Item", row.item_code, "custom_vehicle_item"):
			return True
	return False


def set_vehicle_links(doc, event=None):
	"""
	Validate hook: derive missing vehicle links (VSO <-> VDN <-> Vehicle Unit) and
	enforce ``update_stock = 0`` for vehicle sales.

	Repair Order invoices get vehicle_unit from the order when it is empty, then
	stop. They are not vehicle sales.
	"""
	from autods.service.repair_order_invoice import (
		apply_repair_order_dimensions,
		validate_single_repair_invoice,
	)

	apply_repair_order_dimensions(doc)
	if _is_repair_service_invoice(doc) and not _has_vehicle_sale_markers(doc):
		validate_single_repair_invoice(doc)
		return

	if not _is_vehicle_sale(doc):
		return

	if _meta_has("Sales Invoice", "custom_vehicle_sales"):
		doc.custom_vehicle_sales = 1

	# Derive vehicle_unit from VSO or VDN if not set
	if _meta_has("Sales Invoice", "vehicle_unit"):
		if not doc.get("vehicle_unit"):
			if doc.get("vehicle_sales_order"):
				doc.vehicle_unit = frappe.db.get_value(
					"Vehicle Sales Order", doc.vehicle_sales_order, "vehicle_unit"
				)
			elif doc.get("vehicle_delivery_note"):
				doc.vehicle_unit = frappe.db.get_value(
					"Vehicle Delivery Note", doc.vehicle_delivery_note, "vehicle_unit"
				)

	# Derive VSO from VDN
	if _meta_has("Sales Invoice", "vehicle_sales_order") and not doc.get("vehicle_sales_order"):
		if doc.get("vehicle_delivery_note"):
			doc.vehicle_sales_order = frappe.db.get_value(
				"Vehicle Delivery Note", doc.vehicle_delivery_note, "vehicle_sales_order"
			)

	# Stock posting must be off for vehicle SIs (stock is handled by Vehicle Delivery Note)
	if doc.get("update_stock"):
		frappe.throw(
			_("Sales Invoice for a Vehicle Sale must have 'Update Stock' unchecked. Stock movement is handled by the Vehicle Delivery Note.")
		)


def on_si_submit(doc, event=None):
	"""On submit: write the SI link onto Vehicle Unit / Vehicle Delivery Note and recompute VSO billing."""
	if not _is_vehicle_sale(doc):
		return

	# Update Vehicle Unit
	if doc.get("vehicle_unit") and frappe.db.exists("Vehicle Unit", doc.vehicle_unit):
		frappe.db.set_value("Vehicle Unit", doc.vehicle_unit, "sales_invoice", doc.name)

	# Update Vehicle Delivery Note (if any) with SI link
	if doc.get("vehicle_delivery_note") and frappe.db.exists("Vehicle Delivery Note", doc.vehicle_delivery_note):
		current = frappe.db.get_value("Vehicle Delivery Note", doc.vehicle_delivery_note, "sales_invoice")
		if not current:
			frappe.db.set_value("Vehicle Delivery Note", doc.vehicle_delivery_note, "sales_invoice", doc.name)

	# Trigger VSO billing recompute
	if doc.get("vehicle_sales_order") and frappe.db.exists("Vehicle Sales Order", doc.vehicle_sales_order):
		try:
			vso = frappe.get_doc("Vehicle Sales Order", doc.vehicle_sales_order)
			vso.update_billing_status()
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Vehicle SI submit: VSO status update failed")


def on_si_cancel(doc, event=None):
	"""On cancel: clear the SI link on Vehicle Unit / Vehicle Delivery Note and recompute VSO billing."""
	if not _is_vehicle_sale(doc):
		return

	if doc.get("vehicle_unit"):
		current = frappe.db.get_value("Vehicle Unit", doc.vehicle_unit, "sales_invoice")
		if current == doc.name:
			frappe.db.set_value("Vehicle Unit", doc.vehicle_unit, "sales_invoice", None)

	if doc.get("vehicle_delivery_note"):
		current = frappe.db.get_value("Vehicle Delivery Note", doc.vehicle_delivery_note, "sales_invoice")
		if current == doc.name:
			frappe.db.set_value("Vehicle Delivery Note", doc.vehicle_delivery_note, "sales_invoice", None)

	if doc.get("vehicle_sales_order") and frappe.db.exists("Vehicle Sales Order", doc.vehicle_sales_order):
		try:
			vso = frappe.get_doc("Vehicle Sales Order", doc.vehicle_sales_order)
			vso.update_billing_status()
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Vehicle SI cancel: VSO status update failed")
