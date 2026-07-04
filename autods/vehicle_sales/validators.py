# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# Validators that route vehicle-tagged items (`Item.custom_vehicle_item = 1`) away
# from the standard ERPNext Selling/Buying flow into the dedicated Vehicle Sales
# pipeline (Vehicle Sales Quote / Order / Delivery Note / Receiving). Mirrors how
# `is_fixed_asset` blocks stock movements in ERPNext.

import frappe
from frappe import _


def _block_enabled():
	"""Return True if blocking vehicle items in the standard flow is enabled. Defaults ON."""
	try:
		val = frappe.db.get_single_value(
			"Vehicle Sales Settings", "block_vehicle_items_in_standard_flow"
		)
		# None means the singleton has never been saved; treat as ON (the default)
		if val is None:
			return True
		return bool(val)
	except Exception:
		return True


def _vehicle_items_in_doc(doc):
	"""Return list of (idx, item_code) for vehicle-tagged items in the doc's items table."""
	out = []
	for row in doc.get("items") or []:
		if not row.get("item_code"):
			continue
		if frappe.db.get_value("Item", row.item_code, "custom_vehicle_item"):
			out.append((row.idx, row.item_code))
	return out


def validate_vehicle_item(doc, event=None):
	"""
	Item validation: a vehicle item must not be a stock item (we manage stock per-VIN
	via Vehicle Receiving / Vehicle Delivery Note) and must not have batch tracking.
	Serial No tracking is allowed (the VIN is the serial).
	"""
	if not doc.get("custom_vehicle_item"):
		return
	if doc.get("is_stock_item"):
		frappe.throw(
			_("Vehicle Item must have 'Maintain Stock' unchecked - vehicle inventory is tracked separately via Vehicle Receiving/Delivery.")
		)
	if doc.get("has_batch_no"):
		frappe.throw(_("Vehicle Item cannot use batch tracking."))


def block_vehicle_items_in_standard(doc, event=None):
	"""
	Reject Quotation / Sales Order / Delivery Note containing vehicle-tagged items.
	"""
	if not _block_enabled():
		return
	hits = _vehicle_items_in_doc(doc)
	if not hits:
		return
	first = hits[0][1]
	target = {
		"Quotation": "Vehicle Sales Quote",
		"Sales Order": "Vehicle Sales Order",
		"Delivery Note": "Vehicle Delivery Note",
	}.get(doc.doctype, "Vehicle Sales document")
	frappe.throw(
		_("Item {0} is tagged as a Vehicle Item and cannot be used in {1}. Please use {2} instead.").format(
			frappe.bold(first), doc.doctype, frappe.bold(target)
		)
	)


def block_vehicle_items_in_pr(doc, event=None):
	"""Reject Purchase Receipt containing vehicle-tagged items - they must be received via Vehicle Receiving."""
	if not _block_enabled():
		return
	hits = _vehicle_items_in_doc(doc)
	if not hits:
		return
	first = hits[0][1]
	frappe.throw(
		_("Item {0} is tagged as a Vehicle Item and cannot be received via Purchase Receipt. Please use {1} instead.").format(
			frappe.bold(first), frappe.bold("Vehicle Receiving")
		)
	)


def flag_vehicle_po(doc, event=None):
	"""On Purchase Order validate, auto-set is_vehicle_po if any item is a vehicle item."""
	if not doc.meta.has_field("is_vehicle_po"):
		return
	any_vehicle = any(
		frappe.db.get_value("Item", row.item_code, "custom_vehicle_item")
		for row in (doc.get("items") or [])
		if row.get("item_code")
	)
	doc.is_vehicle_po = 1 if any_vehicle else 0
	if not any_vehicle:
		return
	# Recompute receiving status from submitted Vehicle Receiving docs
	if doc.docstatus == 1 and doc.meta.has_field("vehicle_receiving_status"):
		received = frappe.db.count(
			"Vehicle Receiving",
			filters={"purchase_order": doc.name, "docstatus": 1},
		)
		expected = sum(1 for row in doc.get("items") or [] if frappe.db.get_value(
			"Item", row.item_code, "custom_vehicle_item"
		))
		if received == 0:
			doc.vehicle_receiving_status = "Pending"
		elif received < expected:
			doc.vehicle_receiving_status = "Partially Received"
		else:
			doc.vehicle_receiving_status = "Fully Received"
