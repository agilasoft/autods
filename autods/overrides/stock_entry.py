# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# Set Job Card and Repair Order on Stock Entry from Material Request; update Job Card spareparts on submit.

import frappe
from frappe.utils import flt

# Import only when used (override class)
def _get_stock_entry_class():
	from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry as ERPNextStockEntry
	return ERPNextStockEntry


class StockEntryOverride(_get_stock_entry_class()):
	"""Override Stock Entry so validation passes when created from MR/Repair Order without touching core."""

	def validate(self):
		self._autods_set_default_warehouses()
		self._autods_set_job_card_item_from_job_card()
		super(StockEntryOverride, self).validate()

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

	def _autods_set_job_card_item_from_job_card(self):
		"""Set job_card_item on rows from Job Card Item or Job Card Spareparts Request so Job Card reference is kept."""
		if not self.job_card or self.purpose == "Manufacture":
			return
		if frappe.db.get_single_value("Manufacturing Settings", "job_card_excess_transfer"):
			return
		for row in self.get("items") or []:
			if row.get("job_card_item") or not row.get("s_warehouse") or not row.get("item_code"):
				continue
			# 1) ERPNext Job Card: use existing Job Card Item if present
			jc_item = frappe.db.get_value(
				"Job Card Item",
				{"parent": self.job_card, "item_code": row.item_code},
				"name",
			)
			if jc_item:
				row.job_card_item = jc_item
				continue
			# 2) Autods Job Card: spareparts_requests → ensure a Job Card Item exists and link it
			jc_item = self._autods_get_or_create_job_card_item_for_row(row)
			if jc_item:
				row.job_card_item = jc_item
		# Only clear job_card if a row still has s_warehouse but no job_card_item (e.g. unknown source)
		for row in self.get("items") or []:
			if row.get("s_warehouse") and not row.get("job_card_item"):
				self.job_card = None
				return

	def _autods_get_or_create_job_card_item_for_row(self, row):
		"""For autods Job Cards with spareparts_requests: get or create Job Card Item and return its name."""
		# Match by Job Card Spareparts Request (autods)
		spr = frappe.db.get_value(
			"Job Card Spareparts Request",
			{"parent": self.job_card, "item_code": row.item_code},
			["name", "qty", "uom"],
			as_dict=True,
		)
		if not spr:
			return None
		# Re-check in case we just created one in a previous row
		jc_item = frappe.db.get_value(
			"Job Card Item",
			{"parent": self.job_card, "item_code": row.item_code},
			"name",
		)
		if jc_item:
			return jc_item
		# Create Job Card Item so core validation accepts this row and Job Card reference is kept
		item_doc = frappe.get_cached_doc("Item", row.item_code)
		jc_item_doc = frappe.new_doc("Job Card Item")
		jc_item_doc.parent = self.job_card
		jc_item_doc.parenttype = "Job Card"
		jc_item_doc.parentfield = "items"
		jc_item_doc.item_code = row.item_code
		jc_item_doc.required_qty = flt(row.get("qty")) or flt(spr.qty)
		jc_item_doc.stock_uom = item_doc.stock_uom or row.get("stock_uom")
		jc_item_doc.uom = spr.uom or item_doc.stock_uom
		jc_item_doc.flags.ignore_validate = True
		jc_item_doc.insert(ignore_permissions=True)
		return jc_item_doc.name


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


def on_submit(doc, event=None):
	"""When Stock Entry (Material Issue) is submitted with job_card, mark Job Card spareparts as Issued and link this Stock Entry."""
	if not doc.job_card or doc.purpose != "Material Issue":
		return
	if not frappe.db.exists("Job Card", doc.job_card):
		return
	# Item codes issued in this Stock Entry
	issued_items = {item.item_code for item in doc.items if item.get("item_code")}
	if not issued_items:
		return
	job_doc = frappe.get_doc("Job Card", doc.job_card)
	if not getattr(job_doc, "spareparts_requests", None):
		return
	updated = False
	for row in job_doc.spareparts_requests:
		if row.item_code in issued_items and row.status != "Issued":
			row.status = "Issued"
			row.stock_entry = doc.name
			updated = True
	if updated:
		job_doc.flags.ignore_validate_update_after_submit = True
		job_doc.save(ignore_permissions=True)
