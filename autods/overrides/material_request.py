# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# Keep Material Issue when creating Stock Entry from an AutoDS Job Card Material Request.

import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

from autods.overrides.stock_entry import apply_service_job_card_material_issue, is_service_job_card


def _update_stock_entry_item(obj, target, source_parent):
	qty = (
		flt(flt(obj.stock_qty) - flt(obj.ordered_qty)) / target.conversion_factor
		if flt(obj.stock_qty) > flt(obj.ordered_qty)
		else 0
	)
	target.qty = qty
	target.transfer_qty = qty * obj.conversion_factor
	target.conversion_factor = obj.conversion_factor

	if (
		source_parent.material_request_type == "Material Transfer"
		or source_parent.material_request_type == "Customer Provided"
	):
		target.t_warehouse = obj.warehouse
	else:
		target.s_warehouse = obj.warehouse

	if source_parent.material_request_type == "Customer Provided":
		target.allow_zero_valuation_rate = 1

	if source_parent.material_request_type == "Material Transfer":
		target.s_warehouse = obj.from_warehouse


def _set_missing_values_for_service_issue(source, target):
	target.purpose = source.material_request_type
	target.from_warehouse = source.set_from_warehouse
	target.to_warehouse = source.set_warehouse
	if source.job_card:
		target.job_card = source.job_card
	if getattr(source, "repair_order", None):
		target.repair_order = source.repair_order

	if source.material_request_type == "Material Issue":
		apply_service_job_card_material_issue(target)

	target.set_transfer_qty()
	target.set_actual_qty()
	target.calculate_rate_and_amount(raise_error_if_no_rate=False)
	if not getattr(target, "stock_entry_type", None):
		target.stock_entry_type = target.purpose


def _make_stock_entry_for_service_job_card(source_name, target_doc=None):
	"""Map Material Request → Stock Entry without ERPNext manufacturing Job Card fields."""
	return get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Stock Entry",
				"validation": {
					"docstatus": ["=", 1],
					"material_request_type": [
						"in",
						["Material Transfer", "Material Issue", "Customer Provided"],
					],
				},
			},
			"Material Request Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "material_request_item",
					"parent": "material_request",
					"uom": "stock_uom",
					"job_card_item": "job_card_item",
				},
				"field_no_map": ["expense_account"],
				"postprocess": _update_stock_entry_item,
				"condition": lambda doc: (
					flt(doc.ordered_qty, doc.precision("ordered_qty"))
					< flt(doc.stock_qty, doc.precision("ordered_qty"))
				),
			},
		},
		target_doc,
		_set_missing_values_for_service_issue,
	)


@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	"""ERPNext make_stock_entry, keeping Material Issue for AutoDS service Job Cards."""
	mr = frappe.get_doc("Material Request", source_name)
	if (
		mr.material_request_type == "Material Issue"
		and mr.get("job_card")
		and is_service_job_card(mr.job_card)
	):
		return _make_stock_entry_for_service_job_card(source_name, target_doc)

	from erpnext.stock.doctype.material_request.material_request import (
		make_stock_entry as erpnext_make,
	)

	return erpnext_make(source_name, target_doc)
