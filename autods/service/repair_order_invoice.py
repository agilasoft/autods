# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# Build one Sales Invoice per payer (Customer, Insurance, Warranty) from a Repair Order.
# Parts stock is already issued by Material Issue, so these invoices do not update stock.
# repair_order and vehicle_unit are accounting dimensions; they are set when those fields exist.

import frappe
from frappe import _


class RepairInvoiceError(Exception):
	"""Raised when a Repair Order cannot be turned into a Sales Invoice."""


_TAX_FIELDS = (
	"charge_type",
	"account_head",
	"description",
	"rate",
	"tax_amount",
	"row_id",
	"included_in_print_rate",
	"cost_center",
	"account_currency",
	"dont_recompute_tax",
)

_COLLECTIBLE_FEES = (
	(
		"insurance_participation_fee",
		"insurance_participation_item",
		"Insurance participation fee",
	),
	(
		"insurance_depreciation_fee",
		"insurance_depreciation_item",
		"Insurance depreciation fee",
	),
	(
		"insurance_other_fees_customer",
		"insurance_other_fee_item",
		"Insurance other fees",
	),
)


def _flt(value):
	try:
		return float(value or 0)
	except (TypeError, ValueError):
		return 0.0


def _get(obj, key, default=None):
	if obj is None:
		return default
	if isinstance(obj, dict):
		return obj.get(key, default)
	getter = getattr(obj, "get", None)
	if callable(getter):
		try:
			value = getter(key)
		except TypeError:
			value = None
		if value is not None:
			return value
	return getattr(obj, key, default)


def normalize_bill_type(bill_type):
	bt = (bill_type or "Customer").strip()
	if bt not in ("Insurance", "Warranty"):
		return "Customer"
	return bt


def party_for_charge(header, row):
	"""Customer who should receive the invoice for this charge row."""
	bill_type = normalize_bill_type(_get(row, "bill_type"))
	bill_to = (_get(row, "bill_to") or "").strip()
	if bill_type == "Insurance":
		return bill_to or (_get(header, "insurance_company") or "")
	if bill_type == "Warranty":
		return bill_to or (_get(header, "warranty") or "")
	return _get(header, "customer") or ""


def _charge_line(row):
	qty = _flt(_get(row, "qty"))
	rate = _flt(_get(row, "rate"))
	amount = _flt(_get(row, "amount"))
	if not qty and amount:
		qty = 1.0
		rate = amount
	description = _get(row, "description") or _get(row, "item_name")
	return {
		"item_code": _get(row, "item") or _get(row, "item_code"),
		"item_name": _get(row, "item_name"),
		"description": description,
		"qty": qty or 1.0,
		"uom": _get(row, "uom"),
		"rate": rate,
		"amount": amount,
		"conversion_factor": 1,
	}


def _collectible_lines(header, collectible_items):
	"""Fee lines billed to the Repair Order customer. Items come from Service Settings."""
	lines = []
	items = collectible_items or {}
	other_description = (_get(header, "insurance_other_fees_description") or "").strip()
	for fee_field, item_field, label in _COLLECTIBLE_FEES:
		amount = _flt(_get(header, fee_field))
		if not amount:
			continue
		item_code = items.get(item_field) or items.get(fee_field)
		if not item_code:
			raise RepairInvoiceError(
				_("{0} is {1}, but no item is set for it in Service Settings.").format(label, amount)
			)
		description = other_description if fee_field == "insurance_other_fees_customer" and other_description else label
		lines.append(
			{
				"item_code": item_code,
				"item_name": label,
				"description": description,
				"qty": 1,
				"uom": items.get(item_field + "_uom") or items.get("uom"),
				"rate": amount,
				"amount": amount,
				"conversion_factor": 1,
				"_collectible": 1,
			}
		)
	return lines


def _tax_rows_for_payer(taxes, payer_charge_net, document_net):
	"""Copy the Repair Order tax template rows. Fixed (Actual) amounts are split by charge net."""
	copied = []
	document_net = _flt(document_net)
	payer_charge_net = _flt(payer_charge_net)
	for row in taxes or []:
		entry = {}
		for field in _TAX_FIELDS:
			value = _get(row, field)
			if value is None or value == "":
				continue
			entry[field] = value
		if not entry.get("charge_type"):
			continue
		if entry.get("charge_type") == "Actual" and document_net:
			entry["tax_amount"] = _flt(entry.get("tax_amount")) * payer_charge_net / document_net
		copied.append(entry)
	return copied


def build_invoice_groups(header, charges, taxes=None, collectible_items=None):
	"""Group billable charge lines into one invoice payload per payer.

	Each group is a dict: bill_type, bill_to, lines, charge_net, taxes.
	Insurance collectible fees are added to the customer invoice.
	"""
	buckets = {}
	order = []
	document_net = 0.0

	for row in charges or []:
		amount = _flt(_get(row, "amount"))
		item_code = _get(row, "item") or _get(row, "item_code")
		if not amount or not item_code:
			continue
		bill_type = normalize_bill_type(_get(row, "bill_type"))
		bill_to = party_for_charge(header, row)
		key = (bill_type, bill_to)
		if key not in buckets:
			buckets[key] = []
			order.append(key)
		buckets[key].append(_charge_line(row))
		document_net += amount

	header_net = _flt(_get(header, "net_total"))
	if header_net:
		document_net = header_net

	collectibles = _collectible_lines(header, collectible_items)
	if collectibles:
		key = ("Customer", _get(header, "customer") or "")
		if key not in buckets:
			buckets[key] = []
			order.append(key)
		buckets[key].extend(collectibles)

	bill_type_rank = {"Customer": 0, "Insurance": 1, "Warranty": 2}
	order.sort(key=lambda key: (bill_type_rank.get(key[0], 9), key[1] or ""))

	groups = []
	for bill_type, bill_to in order:
		lines = buckets[(bill_type, bill_to)]
		charge_net = sum(_flt(line.get("amount")) for line in lines if not line.get("_collectible"))
		collectible_amount = sum(_flt(line.get("amount")) for line in lines if line.get("_collectible"))
		groups.append(
			{
				"bill_type": bill_type,
				"bill_to": bill_to,
				"lines": lines,
				"charge_net": charge_net,
				"collectible_amount": collectible_amount,
				"net": charge_net + collectible_amount,
				"taxes": _tax_rows_for_payer(taxes, charge_net, document_net),
			}
		)
	return groups


def invoice_lines(lines):
	"""Item rows safe to append on a Sales Invoice (drops builder-only flags)."""
	cleaned = []
	for line in lines or []:
		cleaned.append({key: value for key, value in line.items() if not key.startswith("_")})
	return cleaned


def select_invoice_group(groups, bill_type, bill_to):
	bill_type = normalize_bill_type(bill_type)
	matches = [
		group
		for group in groups
		if group["bill_type"] == bill_type and (group["bill_to"] or "") == (bill_to or "")
	]
	if len(matches) == 1:
		return matches[0]
	if not matches:
		raise RepairInvoiceError(
			_("No {0} charges to invoice for {1}.").format(bill_type, bill_to or _("this Repair Order"))
		)
	raise RepairInvoiceError(_("More than one {0} invoice matches {1}.").format(bill_type, bill_to))


def _meta_has(doctype, fieldname):
	try:
		return frappe.get_meta(doctype, cached=True).has_field(fieldname)
	except Exception:
		return False


def _set_if_present(doc, fieldname, value, only_if_empty=False):
	if value in (None, ""):
		return
	meta = getattr(doc, "meta", None)
	if meta is not None and hasattr(meta, "has_field") and not meta.has_field(fieldname):
		return
	if meta is None and not _doc_allows_field(doc, fieldname):
		return
	if only_if_empty and _get(doc, fieldname):
		return
	if hasattr(doc, "set"):
		doc.set(fieldname, value)
	elif isinstance(doc, dict):
		doc[fieldname] = value
	else:
		setattr(doc, fieldname, value)


def _doc_allows_field(doc, fieldname):
	"""Dict payloads can take any key. Other docs must list `_fields` when they have no meta."""
	if isinstance(doc, dict):
		return True
	fields = getattr(doc, "_fields", None)
	if fields is None:
		return False
	return fieldname in fields


def apply_repair_order_dimensions(doc):
	"""Set vehicle_unit from the Repair Order when repair_order is set and vehicle_unit is empty.

	Also copies both dimensions onto item rows. Does not mark the document as a vehicle sale.
	"""
	repair_order = _get(doc, "repair_order")
	if not repair_order:
		return
	if not frappe.db.exists("Repair Order", repair_order):
		return
	vehicle_unit = frappe.db.get_value("Repair Order", repair_order, "vehicle_unit")
	if vehicle_unit:
		_set_if_present(doc, "vehicle_unit", vehicle_unit, only_if_empty=True)
	for row in _get(doc, "items") or []:
		_set_if_present(row, "repair_order", repair_order, only_if_empty=True)
		if vehicle_unit:
			_set_if_present(row, "vehicle_unit", vehicle_unit, only_if_empty=True)


def validate_single_repair_invoice(doc):
	"""One open Sales Invoice per Repair Order, payer, and bill type."""
	repair_order = _get(doc, "repair_order")
	customer = _get(doc, "customer")
	bill_type = _get(doc, "custom_repair_bill_type")
	if not repair_order or not customer or not bill_type or _get(doc, "is_return"):
		return
	if not _meta_has("Sales Invoice", "repair_order") or not _meta_has("Sales Invoice", "custom_repair_bill_type"):
		return
	existing = frappe.get_all(
		"Sales Invoice",
		filters={
			"repair_order": repair_order,
			"customer": customer,
			"custom_repair_bill_type": bill_type,
			"docstatus": ["<", 2],
			"name": ["!=", _get(doc, "name") or ""],
		},
		pluck="name",
		limit=1,
	)
	if existing:
		frappe.throw(
			_("Sales Invoice {0} already bills Repair Order {1} to {2} ({3}).").format(
				existing[0], repair_order, customer, bill_type
			)
		)


def collectible_items_from_settings():
	try:
		settings = frappe.get_single("Service Settings")
	except Exception:
		return {}
	items = {}
	for _fee, item_field, _label in _COLLECTIBLE_FEES:
		item_code = settings.get(item_field)
		if item_code:
			items[item_field] = item_code
			uom = frappe.db.get_value("Item", item_code, "stock_uom")
			if uom:
				items[item_field + "_uom"] = uom
	return items


def find_open_sales_invoice(repair_order, bill_type, bill_to):
	if not repair_order or not bill_to:
		return None
	if not _meta_has("Sales Invoice", "repair_order") or not _meta_has("Sales Invoice", "custom_repair_bill_type"):
		return None
	names = frappe.get_all(
		"Sales Invoice",
		filters={
			"repair_order": repair_order,
			"customer": bill_to,
			"custom_repair_bill_type": normalize_bill_type(bill_type),
			"docstatus": ["<", 2],
		},
		pluck="name",
		limit=1,
	)
	return names[0] if names else None
