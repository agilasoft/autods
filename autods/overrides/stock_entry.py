# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# Set Job Card and Repair Order on Stock Entry from Material Request; update Job Card spareparts on submit.

import frappe


def _get_stock_entry_class():
	from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry as ERPNextStockEntry

	return ERPNextStockEntry


def is_service_job_card(job_card):
	"""True when Job Card is the AutoDS workshop card (has spareparts_requests)."""
	if not job_card:
		return False
	if not frappe.db.exists("Job Card", job_card):
		return False
	return bool(frappe.get_meta("Job Card").has_field("spareparts_requests"))


def apply_service_job_card_material_issue(doc):
	"""Keep a service Job Card Stock Entry as Material Issue (not manufacture transfer)."""
	doc.purpose = "Material Issue"
	doc.from_bom = 0
	doc.bom_no = None
	doc.work_order = None
	doc.fg_completed_qty = 0
	setter = getattr(doc, "set_stock_entry_type", None)
	if callable(setter):
		setter()
	if not getattr(doc, "stock_entry_type", None):
		doc.stock_entry_type = "Material Issue"


class StockEntryOverride(_get_stock_entry_class()):
	"""Override Stock Entry so AutoDS Job Card issues skip manufacturing Job Card Item checks."""

	def validate(self):
		self._autods_set_default_warehouses()
		self._autods_normalize_purpose_for_service_job_card()
		super().validate()

	def set_job_card_data(self):
		if is_service_job_card(self.job_card):
			return
		return super().set_job_card_data()

	def validate_job_card_item(self):
		if is_service_job_card(self.job_card):
			return
		return super().validate_job_card_item()

	def update_work_order(self):
		if is_service_job_card(self.job_card):
			job_card = self.job_card
			self.job_card = None
			try:
				super().update_work_order()
			finally:
				self.job_card = job_card
			return
		super().update_work_order()

	def _autods_normalize_purpose_for_service_job_card(self):
		if not is_service_job_card(self.job_card):
			return
		if self.purpose != "Material Transfer for Manufacture":
			return
		mr_type = None
		for item in self.get("items") or []:
			if item.get("material_request"):
				mr_type = frappe.db.get_value(
					"Material Request", item.material_request, "material_request_type"
				)
				break
		if mr_type == "Material Issue" or (getattr(self, "repair_order", None) and not self.work_order):
			apply_service_job_card_material_issue(self)

	def _autods_set_default_warehouses(self):
		"""Set default from_warehouse/to_warehouse when repair_order is set and purpose requires it."""
		if not getattr(self, "repair_order", None) or not self.get("items"):
			return
		try:
			settings = frappe.get_single("Service Settings")
		except Exception:
			return
		default_wh = getattr(settings, "default_parts_warehouse", None)
		if not default_wh or not frappe.db.exists("Warehouse", default_wh):
			return
		source_mandatory = (
			"Material Issue",
			"Material Transfer",
			"Send to Subcontractor",
			"Material Transfer for Manufacture",
			"Material Consumption for Manufacture",
			"Return Raw Material to Customer",
			"Subcontracting Delivery",
		)
		target_mandatory = (
			"Material Receipt",
			"Material Transfer",
			"Send to Subcontractor",
			"Material Transfer for Manufacture",
			"Receive from Customer",
			"Subcontracting Return",
		)
		if self.purpose in source_mandatory and not self.from_warehouse:
			self.from_warehouse = default_wh
		if self.purpose in target_mandatory and not self.to_warehouse:
			self.to_warehouse = default_wh


def before_insert(doc, event=None):
	"""When Stock Entry is created from Material Request, copy job_card and repair_order from MR."""
	if not doc.get("items"):
		return
	mr_name = None
	for item in doc.items:
		if item.get("material_request"):
			mr_name = item.material_request
			break
	if not mr_name or not frappe.db.exists("Material Request", mr_name):
		return
	mr = frappe.get_cached_doc("Material Request", mr_name)
	if mr.get("job_card"):
		doc.job_card = mr.job_card
	if getattr(mr, "repair_order", None):
		doc.repair_order = mr.repair_order


def validate(doc, event=None):
	"""Copy Vehicle Unit from the linked Repair Order onto the Stock Entry and its rows."""
	from autods.service.repair_order_invoice import apply_repair_order_dimensions

	apply_repair_order_dimensions(doc)


def _mr_names_on_stock_entry(doc):
	return {
		item.material_request
		for item in (doc.get("items") or [])
		if item.get("material_request")
	}


def _issued_item_codes(doc):
	return {item.item_code for item in (doc.get("items") or []) if item.get("item_code")}


def _spareparts_rows_to_issue(job_doc, issued_items, mr_names):
	"""Rows to mark Issued: empty stock_entry, matching item, prefer Material Request on this SE."""
	candidates = []
	for row in getattr(job_doc, "spareparts_requests", None) or []:
		if getattr(row, "stock_entry", None):
			continue
		if row.item_code not in issued_items:
			continue
		row_mr = getattr(row, "material_request", None)
		if mr_names and row_mr and row_mr not in mr_names:
			continue
		candidates.append(row)
	if mr_names:
		matched = [row for row in candidates if getattr(row, "material_request", None) in mr_names]
		if matched:
			return matched
	return candidates


def on_submit(doc, event=None):
	"""When Stock Entry (Material Issue) is submitted with job_card, mark spareparts Issued and link SE."""
	if not doc.job_card or doc.purpose != "Material Issue":
		return
	if not frappe.db.exists("Job Card", doc.job_card):
		return
	issued_items = _issued_item_codes(doc)
	if not issued_items:
		return
	job_doc = frappe.get_doc("Job Card", doc.job_card)
	if not getattr(job_doc, "spareparts_requests", None):
		return
	updated = False
	for row in _spareparts_rows_to_issue(job_doc, issued_items, _mr_names_on_stock_entry(doc)):
		row.status = "Issued"
		row.stock_entry = doc.name
		updated = True
	if updated:
		job_doc.flags.ignore_validate_update_after_submit = True
		job_doc.save(ignore_permissions=True)


def on_cancel(doc, event=None):
	"""Clear spareparts stock_entry link when this Material Issue is cancelled."""
	if not doc.job_card or doc.purpose != "Material Issue":
		return
	if not frappe.db.exists("Job Card", doc.job_card):
		return
	job_doc = frappe.get_doc("Job Card", doc.job_card)
	if not getattr(job_doc, "spareparts_requests", None):
		return
	updated = False
	for row in job_doc.spareparts_requests:
		if row.stock_entry != doc.name:
			continue
		row.stock_entry = None
		row.status = "Approved" if getattr(row, "material_request", None) else "Requested"
		updated = True
	if updated:
		job_doc.flags.ignore_validate_update_after_submit = True
		job_doc.save(ignore_permissions=True)
