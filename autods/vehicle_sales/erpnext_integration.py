# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# Integrate Vehicle Unit with ERPNext Purchase Receipt, Delivery Note, Sales Invoice.
# Auto-set Vehicle Unit accounting dimension from serial numbers for P&L and inventory tracking.

import frappe
from frappe.utils import flt

DIMENSION_FIELD = "vehicle_unit"


def on_sales_invoice_validate(doc, event=None):
	"""Ensure serial numbers from Delivery Note are reflected on Sales Invoice when stock was issued in DN."""
	if doc.docstatus != 0:
		return
	for row in doc.get("items") or []:
		if not row.get("delivery_note") or not row.get("dn_detail"):
			continue
		# Already has serial info
		if (row.get("serial_no") or "").strip() or row.get("serial_and_batch_bundle"):
			continue
		# Copy from Delivery Note Item so serial number is reflected even when issuance was in DN
		dn_item = frappe.db.get_value(
			"Delivery Note Item",
			row.dn_detail,
			["serial_no", "serial_and_batch_bundle"],
			as_dict=True,
		)
		if not dn_item:
			continue
		if (dn_item.get("serial_no") or "").strip():
			row.serial_no = dn_item.serial_no
		if dn_item.get("serial_and_batch_bundle"):
			row.serial_and_batch_bundle = dn_item.serial_and_batch_bundle
	_set_vehicle_unit_dimension_from_serial_nos(doc, "items")
	# When SI is from Repair Order, set Vehicle Unit dimension from the order
	_set_vehicle_unit_from_repair_order(doc)


def on_purchase_receipt_submit(doc, event=None):
	"""Link Vehicle Unit to Purchase Receipt and set purchase date/price from PR."""
	if doc.docstatus != 1:
		return
	serial_nos = _get_serial_nos_from_items(doc, "items")
	if not serial_nos:
		return
	# Get valuation from first item row that has serial no (simplified; PR can have multiple items)
	posting_date = doc.posting_date
	for row in doc.items or []:
		if not row.serial_no:
			continue
		for serial in (row.serial_no or "").strip().split("\n"):
			serial = serial.strip()
			if not serial:
				continue
			unit = frappe.db.get_value(
				"Vehicle Unit",
				{"code": serial},
				["name", "purchase_receipt"],
				as_dict=True,
			)
			if not unit:
				continue
			if unit.purchase_receipt and unit.purchase_receipt != doc.name:
				continue
			# Update Vehicle Unit: link PR, set purchase_date and purchase_price from PR
			valuation = flt(row.valuation_rate) or flt(row.base_net_amount) / (flt(row.qty) or 1)
			frappe.db.set_value(
				"Vehicle Unit",
				unit.name,
				{
					"purchase_receipt": doc.name,
					"purchase_date": posting_date,
					"purchase_price": valuation,
				},
			)


def on_delivery_note_submit(doc, event=None):
	"""Link Vehicle Unit to Delivery Note and Sales Invoice; set Vehicle Unit status to Sold."""
	if doc.docstatus != 1:
		return
	serial_nos = _get_serial_nos_from_items(doc, "items")
	if not serial_nos:
		return
	sales_invoice = (doc.get("against_sales_invoice") or "").strip() or None
	if not sales_invoice and doc.get("items"):
		for row in doc.items:
			if row.against_sales_invoice:
				sales_invoice = row.against_sales_invoice
				break
	first_vehicle_unit = None
	for serial in serial_nos:
		unit = frappe.db.get_value("Vehicle Unit", {"code": serial}, "name")
		if not unit:
			continue
		if first_vehicle_unit is None:
			first_vehicle_unit = unit
		upd = {"delivery_note": doc.name, "status": "Sold"}
		if sales_invoice:
			upd["sales_invoice"] = sales_invoice
		frappe.db.set_value("Vehicle Unit", unit, upd)
	# Set Vehicle Unit reference on Delivery Note and Sales Invoice (custom fields)
	if first_vehicle_unit and _custom_field_exists("Delivery Note", "custom_vehicle_unit"):
		frappe.db.set_value("Delivery Note", doc.name, "custom_vehicle_sales", 1)
		frappe.db.set_value("Delivery Note", doc.name, "custom_vehicle_unit", first_vehicle_unit)
	if first_vehicle_unit and sales_invoice and _custom_field_exists("Sales Invoice", "custom_vehicle_unit"):
		frappe.db.set_value("Sales Invoice", sales_invoice, "custom_vehicle_sales", 1)
		frappe.db.set_value("Sales Invoice", sales_invoice, "custom_vehicle_unit", first_vehicle_unit)


def on_sales_invoice_submit(doc, event=None):
	"""Set Vehicle Unit reference on Sales Invoice from item serial nos if not already set."""
	if doc.docstatus != 1:
		return
	if _custom_field_exists("Sales Invoice", "custom_vehicle_unit") and doc.get("custom_vehicle_unit"):
		return
	serial_nos = _get_serial_nos_from_items(doc, "items")
	if not serial_nos:
		return
	for serial in serial_nos:
		unit = frappe.db.get_value("Vehicle Unit", {"code": serial}, "name")
		if unit:
			frappe.db.set_value("Sales Invoice", doc.name, "custom_vehicle_sales", 1)
			frappe.db.set_value("Sales Invoice", doc.name, "custom_vehicle_unit", unit)
			break


def _get_serial_nos_from_items(doc, child_table):
	"""Collect all serial numbers from a document's item table (serial_no and serial_and_batch_bundle)."""
	serial_nos = []
	for row in (doc.get(child_table) or []):
		# From serial_no field (legacy / use_serial_batch_fields)
		row_serials = []
		for serial in (row.get("serial_no") or "").strip().split("\n"):
			serial = serial.strip()
			if serial:
				row_serials.append(serial)
		# From serial_and_batch_bundle when this row has no serial_no
		if not row_serials and row.get("serial_and_batch_bundle"):
			row_serials = _get_serial_nos_from_bundle(row.serial_and_batch_bundle)
		serial_nos.extend(row_serials)
	return serial_nos


def _get_serial_nos_from_bundle(bundle_id):
	"""Return list of serial numbers from a Serial and Batch Bundle, if any."""
	if not bundle_id or not frappe.db.exists("Serial and Batch Bundle", bundle_id):
		return []
	try:
		from erpnext.stock.serial_batch_bundle import get_serial_nos_from_bundle
		return get_serial_nos_from_bundle(bundle_id) or []
	except Exception:
		return []


def _set_vehicle_unit_dimension_from_serial_nos(doc, child_table="items"):
	"""
	Set Vehicle Unit accounting dimension on doc and child rows from serial numbers.
	Enables P&L, inventory cost and movement tracking per vehicle unit. Only runs
	if the dimension field exists (created by Accounting Dimension for Vehicle Unit).
	"""
	if not _has_dimension_field(doc.doctype):
		return
	meta = frappe.get_meta(doc.doctype, cached=True)
	child_doctype = meta.get_options(child_table) if meta.get_field(child_table) else None
	child_has_dimension = child_doctype and _has_dimension_field(child_doctype)
	first_unit = None
	for row in doc.get(child_table) or []:
		row_serials = _get_serial_nos_from_row(row)
		unit = _vehicle_unit_from_serials(row_serials)
		if unit:
			if child_has_dimension:
				row.set(DIMENSION_FIELD, unit)
			if first_unit is None:
				first_unit = unit
	if first_unit:
		doc.set(DIMENSION_FIELD, first_unit)


def _get_serial_nos_from_row(row):
	"""Get list of serial numbers from a single item row (serial_no or bundle)."""
	out = []
	for s in (row.get("serial_no") or "").strip().split("\n"):
		s = s.strip()
		if s:
			out.append(s)
	if not out and row.get("serial_and_batch_bundle"):
		out = _get_serial_nos_from_bundle(row.serial_and_batch_bundle)
	return out


def _vehicle_unit_from_serials(serial_nos):
	"""Return first Vehicle Unit name whose code is in serial_nos, or None."""
	for serial in serial_nos or []:
		unit = frappe.db.get_value("Vehicle Unit", {"code": serial}, "name")
		if unit:
			return unit
	return None


def _has_dimension_field(doctype):
	"""Return True if doctype has the Vehicle Unit accounting dimension field."""
	if not doctype:
		return False
	meta = frappe.get_meta(doctype, cached=True)
	return meta.has_field(DIMENSION_FIELD)


def on_delivery_note_validate(doc, event=None):
	"""Auto-set Vehicle Unit accounting dimension from serial numbers on items."""
	_set_vehicle_unit_dimension_from_serial_nos(doc, "items")


def on_stock_entry_validate(doc, event=None):
	"""Auto-set Vehicle Unit accounting dimension from serial numbers or from Repair Order."""
	_set_vehicle_unit_dimension_from_serial_nos(doc, "items")
	_set_vehicle_unit_from_repair_order(doc)


def on_purchase_receipt_validate(doc, event=None):
	"""Auto-set Vehicle Unit accounting dimension from serial numbers on items."""
	_set_vehicle_unit_dimension_from_serial_nos(doc, "items")


def _set_vehicle_unit_from_repair_order(doc):
	"""When doc has repair_order, set vehicle_unit from Repair Order (for P&L and cost tracking per RO and vehicle)."""
	if not doc.get("repair_order"):
		return
	if not _has_dimension_field(doc.doctype):
		return
	vehicle_unit = frappe.db.get_value("Repair Order", doc.repair_order, "vehicle_unit")
	if vehicle_unit:
		doc.set(DIMENSION_FIELD, vehicle_unit)


def on_journal_entry_validate(doc, event=None):
	"""Set Repair Order and Vehicle Unit dimensions on JE and each account row when linked to a Repair Order."""
	if not doc.get("repair_order") or doc.docstatus != 0:
		return
	ro_vehicle_unit = frappe.db.get_value("Repair Order", doc.repair_order, "vehicle_unit")
	# Set on header so default/round-off logic can use it
	if _has_dimension_field(doc.doctype):
		doc.set(DIMENSION_FIELD, ro_vehicle_unit)
	# Set on each account row so GL entries get both dimensions (revenue/cost per Repair Order and Vehicle Unit)
	meta = frappe.get_meta("Journal Entry Account", cached=True)
	has_repair_order = meta.has_field("repair_order")
	has_vehicle_unit = meta.has_field(DIMENSION_FIELD)
	if not (has_repair_order or has_vehicle_unit):
		return
	for row in doc.get("accounts") or []:
		if has_repair_order:
			row.set("repair_order", doc.repair_order)
		if has_vehicle_unit and ro_vehicle_unit:
			row.set(DIMENSION_FIELD, ro_vehicle_unit)


def _custom_field_exists(dt, fieldname):
	"""Return True if the custom field exists for the doctype."""
	return frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname})
