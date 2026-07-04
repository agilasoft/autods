# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime

from autods.vehicle_sales.doctype.vehicle_cost_ledger.vehicle_cost_ledger import (
	add_entry as add_cost_ledger_entry,
)
from autods.vehicle_sales.doctype.vehicle_sales_settings.vehicle_sales_settings import (
	get_company_settings,
	get_settings,
)


class VehicleDeliveryNote(Document):
	def validate(self):
		self._set_currency_defaults()
		self._compute_accessory_lines()
		self._compute_totals()
		self._apply_company_defaults()
		self._validate_vehicle_unit()

	def before_submit(self):
		self.status = "Delivered"
		if not self.released_on:
			self.released_on = now_datetime()
		if not self.released_by:
			self.released_by = frappe.session.user

	def on_submit(self):
		ledger = self._post_cogs_cost_ledger()
		if ledger:
			self.db_set("vehicle_cost_ledger", ledger.name)
		je = self._post_cogs_journal_entry(ledger)
		if je:
			self.db_set("journal_entry", je)
			if ledger:
				frappe.db.set_value("Vehicle Cost Ledger", ledger.name, "journal_entry", je)
		self._update_vehicle_unit_links()
		self._update_sales_order_status()

	def on_cancel(self):
		self.status = "Cancelled"
		self._cancel_journal_entry()
		self._cancel_cost_ledger()
		self._unlink_from_vehicle_unit()
		self._update_sales_order_status()

	def _set_currency_defaults(self):
		if not self.currency and self.company:
			self.currency = frappe.db.get_value("Company", self.company, "default_currency")
		if not self.conversion_rate:
			self.conversion_rate = 1

	def _compute_accessory_lines(self):
		for row in self.get("accessories") or []:
			qty = flt(row.qty, 2) or 1
			row.qty = qty
			row.amount = flt(qty * flt(row.rate, 2) + flt(row.installation_cost, 2), 2)

	def _compute_totals(self):
		acc_total = sum(flt(r.amount, 2) for r in (self.get("accessories") or []))
		self.accessories_total = acc_total
		self.net_total = flt(self.base_price, 2) + acc_total
		taxable = max(self.net_total - flt(self.discount_amount, 2), 0)
		self.grand_total = flt(taxable + flt(self.total_taxes_and_charges, 2), 2)

	def _apply_company_defaults(self):
		if not self.company:
			return
		cs = get_company_settings(self.company)
		if not self.vehicle_inventory_account:
			self.vehicle_inventory_account = cs.get("default_vehicle_inventory_account")
		if not self.cogs_account:
			self.cogs_account = cs.get("default_cogs_account")
		if not self.cost_center:
			self.cost_center = cs.get("default_cost_center")

	def _validate_vehicle_unit(self):
		if not self.vehicle_unit:
			return
		if self.docstatus == 0:
			status = frappe.db.get_value("Vehicle Unit", self.vehicle_unit, "status")
			if status == "Sold":
				existing = frappe.db.exists(
					"Vehicle Delivery Note",
					{
						"vehicle_unit": self.vehicle_unit,
						"docstatus": 1,
						"name": ["!=", self.name or ""],
					},
				)
				if existing:
					frappe.throw(
						_("Vehicle Unit {0} has already been delivered via {1}.").format(
							self.vehicle_unit, existing
						)
					)

	def _get_vehicle_cost(self):
		"""Read current cost from Vehicle Unit (sum of Vehicle Cost Ledger)."""
		if not self.vehicle_unit:
			return 0.0
		return flt(frappe.db.get_value("Vehicle Unit", self.vehicle_unit, "current_cost"), 2)

	def _post_cogs_cost_ledger(self):
		if not self.vehicle_unit:
			return None
		cost = self._get_vehicle_cost()
		if cost <= 0:
			frappe.msgprint(
				_("Vehicle Unit {0} has zero cost recorded; skipping COGS posting.").format(self.vehicle_unit),
				alert=True,
				indicator="orange",
			)
			return None
		return add_cost_ledger_entry(
			vehicle_unit=self.vehicle_unit,
			amount=cost,
			cost_type="COGS",
			voucher_type="Vehicle Delivery Note",
			voucher_no=self.name,
			account=self.cogs_account,
			cost_center=self.cost_center,
			posting_date=self.posting_date,
			company=self.company,
			remarks=_("COGS on delivery to {0}").format(self.customer),
			submit=True,
		)

	def _post_cogs_journal_entry(self, ledger=None):
		settings = get_settings()
		if not settings.auto_post_je:
			return None
		cost = self._get_vehicle_cost()
		if cost <= 0:
			return None
		if not self.cogs_account or not self.vehicle_inventory_account:
			frappe.msgprint(
				_("Skipping COGS Journal Entry: COGS Account or Vehicle Inventory Account not configured."),
				alert=True,
				indicator="orange",
			)
			return None
		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.posting_date = self.posting_date
		je.company = self.company
		je.user_remark = _("Vehicle Delivery {0} - VIN {1}").format(self.name, self.chassis_number or self.vehicle_unit)
		je.append(
			"accounts",
			{
				"account": self.cogs_account,
				"debit_in_account_currency": flt(cost, 2),
				"cost_center": self.cost_center,
				"reference_type": self.doctype,
				"reference_name": self.name,
			},
		)
		je.append(
			"accounts",
			{
				"account": self.vehicle_inventory_account,
				"credit_in_account_currency": flt(cost, 2),
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
			frappe.log_error(frappe.get_traceback(), "Vehicle Delivery JE submit failed")
			frappe.msgprint(
				_("COGS Journal Entry created in Draft state due to a posting error."),
				alert=True,
				indicator="orange",
			)
		return je.name

	def _update_vehicle_unit_links(self):
		if not self.vehicle_unit:
			return
		updates = {
			"vehicle_delivery_note": self.name,
			"status": "Sold",
			"customer": self.customer,
		}
		if self.sales_invoice:
			updates["sales_invoice"] = self.sales_invoice
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
			frappe.log_error(frappe.get_traceback(), "Vehicle Delivery JE cancel failed")

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
		current = frappe.db.get_value("Vehicle Unit", self.vehicle_unit, "vehicle_delivery_note")
		if current == self.name:
			frappe.db.set_value(
				"Vehicle Unit",
				self.vehicle_unit,
				{"vehicle_delivery_note": None, "status": "Reserved"},
			)

	def _update_sales_order_status(self):
		if not self.vehicle_sales_order:
			return
		try:
			so = frappe.get_doc("Vehicle Sales Order", self.vehicle_sales_order)
			so.update_delivery_status()
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Vehicle Delivery: VSO status update failed")
