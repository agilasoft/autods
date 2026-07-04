# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from autods.vehicle_sales.doctype.vehicle_cost_ledger.vehicle_cost_ledger import (
	add_entry as add_cost_ledger_entry,
)
from autods.vehicle_sales.doctype.vehicle_sales_settings.vehicle_sales_settings import (
	get_company_settings,
	get_settings,
)


class VehicleReceiving(Document):
	def autoname(self):
		from frappe.model.naming import set_name_by_naming_series

		set_name_by_naming_series(self)

	def validate(self):
		self._validate_item_is_vehicle()
		self._compute_total_cost()
		self._apply_company_defaults()
		self._validate_or_link_vehicle_unit()

	def before_submit(self):
		self.status = "Received"

	def on_submit(self):
		self._ensure_vehicle_unit()
		ledger = self._post_cost_ledger()
		if ledger:
			self.db_set("vehicle_cost_ledger", ledger.name)
		je = self._post_journal_entry(ledger)
		if je:
			self.db_set("journal_entry", je)
			if ledger:
				frappe.db.set_value("Vehicle Cost Ledger", ledger.name, "journal_entry", je)
		self._update_vehicle_unit_links()

	def on_cancel(self):
		self.status = "Cancelled"
		self._cancel_journal_entry()
		self._cancel_cost_ledger()
		self._unlink_from_vehicle_unit()

	def _validate_item_is_vehicle(self):
		if not self.item:
			return
		is_vehicle = frappe.db.get_value("Item", self.item, "custom_vehicle_item")
		if not is_vehicle:
			frappe.throw(
				_("Item {0} is not tagged as a Vehicle Item. Set 'Vehicle Item' on the Item master.").format(
					self.item
				)
			)

	def _compute_total_cost(self):
		self.total_cost = flt(self.base_cost, 2) + flt(self.freight, 2) + flt(self.other_landed_cost, 2)

	def _apply_company_defaults(self):
		if not self.company:
			return
		cs = get_company_settings(self.company)
		if not self.vehicle_inventory_account:
			self.vehicle_inventory_account = cs.get("default_vehicle_inventory_account")
		if not self.stock_received_but_not_billed:
			self.stock_received_but_not_billed = cs.get("default_stock_received_but_not_billed")
		if not self.cost_center:
			self.cost_center = cs.get("default_cost_center")
		if not self.supplier_account:
			self.supplier_account = cs.get("default_supplier_account")
		if not self.warehouse:
			self.warehouse = cs.get("default_vehicle_warehouse")
		if not self.currency:
			self.currency = frappe.db.get_value("Company", self.company, "default_currency")

	def _validate_or_link_vehicle_unit(self):
		if self.vehicle_unit:
			return
		# Auto-link to existing Vehicle Unit by chassis (= code)
		if self.chassis_number:
			existing = frappe.db.get_value("Vehicle Unit", {"code": self.chassis_number}, "name")
			if existing:
				self.vehicle_unit = existing

	def _ensure_vehicle_unit(self):
		if self.vehicle_unit:
			return
		settings = get_settings()
		if not settings.auto_create_vehicle_unit:
			frappe.throw(
				_("Vehicle Unit is required. Set Auto-create Vehicle Unit in Vehicle Sales Settings or pre-create the Vehicle Unit.")
			)
		if not self.chassis_number:
			frappe.throw(_("Chassis Number is required to auto-create Vehicle Unit."))
		vu = frappe.new_doc("Vehicle Unit")
		vu.code = self.chassis_number
		vu.description = self.item_name or self.item
		vu.item = self.item
		vu.chassis_number = self.chassis_number
		vu.engine_number = self.engine_number
		vu.make = self.make
		vu.model = self.model
		vu.variant = self.variant
		vu.year_model = self.year_model
		vu.edition = self.edition
		vu.color = self.color
		vu.transmission_type = self.transmission_type
		vu.drive_type = self.drive_type
		vu.fuel_type = self.fuel_type
		vu.body_type = self.body_type
		vu.warehouse = self.warehouse
		vu.purchase_date = self.posting_date
		vu.purchase_price = self.base_cost
		vu.status = "Available"
		vu.flags.ignore_permissions = True
		vu.insert(ignore_permissions=True)
		self.db_set("vehicle_unit", vu.name)

	def _post_cost_ledger(self):
		if not self.vehicle_unit:
			return None
		return add_cost_ledger_entry(
			vehicle_unit=self.vehicle_unit,
			amount=self.total_cost,
			cost_type="Base",
			voucher_type="Vehicle Receiving",
			voucher_no=self.name,
			account=self.vehicle_inventory_account,
			cost_center=self.cost_center,
			posting_date=self.posting_date,
			company=self.company,
			remarks=_("Receiving from {0} ({1})").format(self.supplier, self.purchase_order or ""),
			submit=True,
		)

	def _post_journal_entry(self, ledger=None):
		settings = get_settings()
		if not settings.auto_post_je:
			return None
		if flt(self.total_cost) <= 0:
			return None
		if not self.vehicle_inventory_account or not self.stock_received_but_not_billed:
			frappe.msgprint(
				_("Skipping Journal Entry: Vehicle Inventory Account or Stock Received But Not Billed not configured."),
				alert=True,
				indicator="orange",
			)
			return None
		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.posting_date = self.posting_date
		je.company = self.company
		je.user_remark = _("Vehicle Receiving {0} - VIN {1}").format(self.name, self.chassis_number)
		# Dr Vehicle Inventory
		je.append(
			"accounts",
			{
				"account": self.vehicle_inventory_account,
				"debit_in_account_currency": flt(self.total_cost, 2),
				"cost_center": self.cost_center,
				"reference_type": self.doctype,
				"reference_name": self.name,
			},
		)
		# Cr Stock Received But Not Billed
		je.append(
			"accounts",
			{
				"account": self.stock_received_but_not_billed,
				"credit_in_account_currency": flt(self.total_cost, 2),
				"cost_center": self.cost_center,
				"reference_type": self.doctype,
				"reference_name": self.name,
			},
		)
		je.flags.ignore_permissions = True
		je.insert(ignore_permissions=True)
		try:
			je.submit()
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Vehicle Receiving JE submit failed")
			frappe.msgprint(_("Journal Entry created in Draft state due to a posting error."), alert=True, indicator="orange")
		return je.name

	def _update_vehicle_unit_links(self):
		if not self.vehicle_unit:
			return
		updates = {
			"vehicle_receiving": self.name,
			"purchase_date": self.posting_date,
			"purchase_price": self.base_cost,
			"warehouse": self.warehouse,
		}
		frappe.db.set_value("Vehicle Unit", self.vehicle_unit, updates)

	def _cancel_journal_entry(self):
		if not self.journal_entry:
			return
		try:
			je = frappe.get_doc("Journal Entry", self.journal_entry)
			if je.docstatus == 1:
				je.flags.ignore_permissions = True
				je.cancel()
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Vehicle Receiving JE cancel failed")

	def _cancel_cost_ledger(self):
		if not self.vehicle_cost_ledger:
			return
		try:
			vcl = frappe.get_doc("Vehicle Cost Ledger", self.vehicle_cost_ledger)
			if vcl.docstatus == 1:
				vcl.flags.ignore_permissions = True
				vcl.cancel()
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Vehicle Cost Ledger cancel failed")

	def _unlink_from_vehicle_unit(self):
		if not self.vehicle_unit:
			return
		current = frappe.db.get_value("Vehicle Unit", self.vehicle_unit, "vehicle_receiving")
		if current == self.name:
			frappe.db.set_value("Vehicle Unit", self.vehicle_unit, "vehicle_receiving", None)


@frappe.whitelist()
def make_vehicle_receiving_from_purchase_order(source_name, target_doc=None):
	"""Map a Purchase Order line to a single-VIN Vehicle Receiving (Fixed-Asset-style)."""
	from frappe.model.mapper import get_mapped_doc

	def postprocess(source, target):
		target.posting_date = frappe.utils.getdate()
		# Pick first vehicle line; user must duplicate for additional VINs
		for row in source.items or []:
			is_vehicle = frappe.db.get_value("Item", row.item_code, "custom_vehicle_item")
			if is_vehicle:
				target.item = row.item_code
				target.item_name = row.item_name
				target.base_cost = flt(row.rate, 2)
				break

	doc = get_mapped_doc(
		"Purchase Order",
		source_name,
		{
			"Purchase Order": {
				"doctype": "Vehicle Receiving",
				"field_map": {
					"name": "purchase_order",
					"supplier": "supplier",
					"company": "company",
					"currency": "currency",
					"conversion_rate": "conversion_rate",
				},
				"validation": {"docstatus": ["=", 1]},
			}
		},
		target_doc,
		postprocess,
	)
	return doc
