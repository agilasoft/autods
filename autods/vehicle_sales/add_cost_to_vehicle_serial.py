# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# Add accessory and installation cost to vehicle serial number inventory (Stock Ledger).
# Implements §3.3.1: once accessories are issued (Stock Entry) and installation done (Job Card),
# this creates a Stock Reconciliation to set the vehicle serial's valuation = current + amount.

import frappe
from frappe import _
from frappe.utils import flt


def _get_current_bundle_and_rate(vehicle_unit_code, item_code, warehouse):
	"""
	Get current serial-and-batch bundle and valuation rate for this serial in warehouse.
	Returns (bundle_name, current_qty, current_valuation_rate) or (None, 1, rate) with rate from legacy SLE.
	"""
	# Prefer bundle-based SLE (join with Serial and Batch Entry)
	row = frappe.db.sql(
		"""
		select sle.serial_and_batch_bundle, sle.valuation_rate, sle.qty_after_transaction
		from `tabStock Ledger Entry` sle
		inner join `tabSerial and Batch Entry` sbe
			on sbe.parent = sle.serial_and_batch_bundle and sbe.serial_no = %(serial_no)s
		where sle.item_code = %(item_code)s and sle.warehouse = %(warehouse)s and sle.is_cancelled = 0
		order by sle.posting_date desc, sle.posting_time desc, sle.creation desc
		limit 1
		""",
		{"serial_no": vehicle_unit_code, "item_code": item_code, "warehouse": warehouse},
		as_dict=True,
	)
	if row and row[0].get("serial_and_batch_bundle"):
		r = row[0]
		return (
			r.serial_and_batch_bundle,
			flt(r.qty_after_transaction, 2) or 1,
			flt(r.valuation_rate, 2),
		)
	# Legacy: SLE has serial_no stored (e.g. newline-separated)
	legacy = frappe.db.get_value(
		"Stock Ledger Entry",
		[
			["item_code", "=", item_code],
			["warehouse", "=", warehouse],
			["is_cancelled", "=", 0],
			["serial_no", "like", f"%{vehicle_unit_code}%"],
		],
		"valuation_rate",
		order_by="posting_date desc, posting_time desc, creation desc",
	)
	if legacy is not None:
		return None, 1, flt(legacy, 2)
	return None, 1, None


@frappe.whitelist()
def add_cost_to_vehicle_serial(vehicle_unit, amount_to_add, reason=None):
	"""
	Add the given cost to the vehicle serial number's inventory valuation (Stock Ledger).
	Creates and submits a Stock Reconciliation so the serial's valuation_rate becomes
	current + amount_to_add. Vehicle Unit's Current Cost will reflect this on next save.

	:param vehicle_unit: Vehicle Unit name (doc with code=serial, item, warehouse)
	:param amount_to_add: Amount to add (e.g. accessory cost + installation cost)
	:param reason: Optional remark for the Stock Reconciliation
	:return: dict with stock_reconciliation name and message
	"""
	amount_to_add = flt(amount_to_add, 2)
	if amount_to_add <= 0:
		frappe.throw(_("Amount to add must be greater than zero"))

	vu = frappe.db.get_value(
		"Vehicle Unit",
		vehicle_unit,
		["name", "code", "item", "warehouse", "current_cost"],
		as_dict=True,
	)
	if not vu or not vu.code or not vu.item or not vu.warehouse:
		frappe.throw(_("Vehicle Unit must have Code (serial no), Item, and Warehouse"))

	company = frappe.db.get_value("Warehouse", vu.warehouse, "company")
	if not company:
		frappe.throw(_("Warehouse {0} has no company").format(vu.warehouse))

	current_bundle, current_qty, current_rate = _get_current_bundle_and_rate(
		vu.code, vu.item, vu.warehouse
	)
	if current_rate is None:
		frappe.throw(
			_("No stock found for serial {0} in warehouse {1}. Receive the vehicle first.").format(
				vu.code, vu.warehouse
			)
		)

	new_rate = flt(current_rate, 2) + amount_to_add
	item_name = frappe.db.get_value("Item", vu.item, "item_name") or vu.item

	sr = frappe.new_doc("Stock Reconciliation")
	sr.purpose = "Stock Reconciliation"
	sr.company = company
	sr.posting_date = frappe.utils.getdate()
	sr.posting_time = frappe.utils.nowtime()
	sr.set_warehouse = vu.warehouse
	if reason:
		sr.remarks = reason

	row_data = {
		"item_code": vu.item,
		"item_name": item_name,
		"warehouse": vu.warehouse,
		"qty": 1,
		"valuation_rate": new_rate,
		"current_qty": current_qty,
		"current_valuation_rate": current_rate,
		"use_serial_batch_fields": 1,
	}
	if current_bundle:
		row_data["current_serial_and_batch_bundle"] = current_bundle
	else:
		row_data["current_serial_no"] = vu.code
		row_data["serial_no"] = vu.code

	sr.append("items", row_data)
	sr.flags.ignore_validate_update_after_submit = True
	sr.insert()

	# Reload to get row name and (if legacy) current_serial_and_batch_bundle set by validate
	sr.reload()
	row = sr.items[0]

	# Create new inward bundle so SR can post correct SLE (outward with current bundle, inward with new rate)
	from erpnext.stock.utils import get_combine_datetime

	from erpnext.stock.serial_batch_bundle import SerialBatchCreation

	new_bundle = SerialBatchCreation(
		{
			"item_code": vu.item,
			"warehouse": vu.warehouse,
			"posting_datetime": get_combine_datetime(sr.posting_date, sr.posting_time),
			"voucher_type": "Stock Reconciliation",
			"voucher_no": sr.name,
			"voucher_detail_no": row.name,
			"qty": 1,
			"avg_rate": new_rate,
			"total_amount": flt(new_rate),
			"type_of_transaction": "Inward",
			"company": company,
			"do_not_submit": True,
		}
	).make_serial_and_batch_bundle(serial_nos=[vu.code])

	if new_bundle and new_bundle.get("name"):
		frappe.db.set_value(
			"Stock Reconciliation Item",
			row.name,
			"serial_and_batch_bundle",
			new_bundle.name,
		)
		sr.reload()

	sr.submit()

	return {
		"stock_reconciliation": sr.name,
		"message": _(
			"Stock Reconciliation {0} created and submitted. Vehicle serial valuation updated by {1}."
		).format(sr.name, amount_to_add),
	}
