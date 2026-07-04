# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, getdate


class VehicleSalesOrder(Document):
	def validate(self):
		self._set_currency_defaults()
		self._compute_accessory_lines()
		self._compute_totals()
		self._validate_vehicle_unit_status()

	def on_submit(self):
		self.db_set("status", self._compute_overall_status())
		self._reserve_vehicle_unit()

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		self._release_vehicle_unit()

	def _set_currency_defaults(self):
		if not self.currency and self.company:
			self.currency = frappe.db.get_value("Company", self.company, "default_currency")
		if not self.price_list_currency and self.selling_price_list:
			self.price_list_currency = frappe.db.get_value(
				"Price List", self.selling_price_list, "currency"
			) or self.currency
		if not self.conversion_rate:
			self.conversion_rate = 1
		if not self.plc_conversion_rate:
			self.plc_conversion_rate = 1

	def _compute_accessory_lines(self):
		for row in self.get("accessories") or []:
			qty = flt(row.qty, 2) or 1
			row.qty = qty
			row.amount = flt(qty * flt(row.rate, 2) + flt(row.installation_cost, 2), 2)

	def _compute_totals(self):
		acc_total = sum(flt(r.amount, 2) for r in (self.get("accessories") or []))
		self.accessories_total = acc_total
		self.net_total = flt(self.base_price, 2) + acc_total

		discount = flt(self.discount_amount, 2)
		if not discount and flt(self.additional_discount_percentage):
			discount = flt(self.net_total * flt(self.additional_discount_percentage) / 100, 2)
			self.discount_amount = discount

		taxable = max(self.net_total - discount, 0)
		self.total_taxes_and_charges = self._calculate_taxes(taxable)
		self.grand_total = flt(taxable + self.total_taxes_and_charges, 2)
		try:
			from frappe.utils import money_in_words

			self.in_words = money_in_words(self.grand_total, self.currency)
		except Exception:
			self.in_words = None

	def _calculate_taxes(self, taxable):
		total = 0.0
		for row in self.get("taxes") or []:
			rate = flt(row.rate, 6)
			if row.charge_type == "On Net Total":
				row.tax_amount = flt(taxable * rate / 100, 2)
			elif row.charge_type == "Actual":
				row.tax_amount = flt(row.tax_amount, 2)
			else:
				row.tax_amount = flt(row.tax_amount, 2)
			row.base_tax_amount = flt(row.tax_amount * flt(self.conversion_rate or 1), 2)
			total += flt(row.tax_amount, 2)
			row.total = flt(taxable + total, 2)
			row.base_total = flt(row.total * flt(self.conversion_rate or 1), 2)
		return flt(total, 2)

	def _validate_vehicle_unit_status(self):
		if not self.vehicle_unit:
			return
		if self.docstatus == 0:
			status = frappe.db.get_value("Vehicle Unit", self.vehicle_unit, "status")
			if status == "Sold":
				frappe.throw(_("Vehicle Unit {0} is already sold.").format(self.vehicle_unit))

	def _reserve_vehicle_unit(self):
		if not self.vehicle_unit:
			return
		current = frappe.db.get_value("Vehicle Unit", self.vehicle_unit, "status")
		if current in (None, "Available"):
			frappe.db.set_value("Vehicle Unit", self.vehicle_unit, {"status": "Reserved", "customer": self.customer})

	def _release_vehicle_unit(self):
		if not self.vehicle_unit:
			return
		current = frappe.db.get_value("Vehicle Unit", self.vehicle_unit, "status")
		if current == "Reserved":
			frappe.db.set_value("Vehicle Unit", self.vehicle_unit, {"status": "Available"})

	def _compute_overall_status(self):
		"""Compute overall status from delivery_status + billing_status."""
		ds = self.delivery_status or "Not Delivered"
		bs = self.billing_status or "Not Billed"
		if ds == "Delivered" and bs == "Fully Billed":
			return "Completed"
		if ds == "Delivered" and bs != "Fully Billed":
			return "To Bill"
		if ds != "Delivered" and bs == "Fully Billed":
			return "To Deliver"
		return "To Deliver and Bill"

	def update_delivery_status(self):
		"""Recompute delivery_status from existing Vehicle Delivery Notes."""
		delivered = frappe.db.exists(
			"Vehicle Delivery Note",
			{"vehicle_sales_order": self.name, "docstatus": 1},
		)
		new_status = "Delivered" if delivered else "Not Delivered"
		self.db_set("delivery_status", new_status)
		self.db_set("status", self._compute_overall_status())

	def update_billing_status(self):
		"""Recompute billing_status from Sales Invoices linked to this VSO."""
		billed = frappe.db.sql(
			"""
			select coalesce(sum(grand_total), 0) as total
			from `tabSales Invoice`
			where docstatus = 1 and (vehicle_sales_order = %(name)s or vehicle_sales_order is null
				and exists (select 1 from `tabSales Invoice Item` sii
					where sii.parent = `tabSales Invoice`.name and sii.sales_order = %(name)s))
			""",
			{"name": self.name},
		)
		billed_total = flt(billed[0][0]) if billed else 0
		new_status = "Not Billed"
		if billed_total > 0:
			new_status = "Fully Billed" if billed_total >= flt(self.grand_total) else "Partly Billed"
		self.db_set("billing_status", new_status)
		self.db_set("status", self._compute_overall_status())


@frappe.whitelist()
def make_vehicle_delivery_note(source_name, target_doc=None):
	"""Map a Vehicle Sales Order to a Vehicle Delivery Note."""

	def update_item(source, target, source_parent):
		target.amount = source.amount

	def postprocess(source, target):
		target.posting_date = frappe.utils.getdate()
		target.vehicle_sales_order = source.name
		target.naming_series = "VDN-.YYYY.-"
		target.status = "Draft"

	doc = get_mapped_doc(
		"Vehicle Sales Order",
		source_name,
		{
			"Vehicle Sales Order": {
				"doctype": "Vehicle Delivery Note",
				"field_map": {
					"name": "vehicle_sales_order",
				},
				"validation": {"docstatus": ["=", 1]},
			},
			"Vehicle Sales Order Accessory": {
				"doctype": "Vehicle Delivery Note Accessory",
				"field_map": {},
				"postprocess": update_item,
			},
		},
		target_doc,
		postprocess,
	)
	return doc


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
	"""Map a Vehicle Sales Order to a standard Sales Invoice (one item line: vehicle item)."""
	from frappe.model.mapper import get_mapped_doc

	source = frappe.get_doc("Vehicle Sales Order", source_name)

	def postprocess(src, target):
		target.vehicle_unit = src.vehicle_unit
		target.vehicle_sales_order = src.name
		target.custom_vehicle_sales = 1
		target.update_stock = 0
		target.due_date = frappe.utils.add_days(frappe.utils.getdate(), 30)
		# Single line for the vehicle (qty=1, rate=grand_total - taxes ideally; here we use net_total after discount)
		taxable = max(flt(src.net_total) - flt(src.discount_amount), 0)
		target.append(
			"items",
			{
				"item_code": src.item,
				"item_name": src.item_name,
				"description": "{0} - VIN {1}".format(src.item_name or src.item, src.chassis_number or src.vehicle_unit),
				"qty": 1,
				"uom": frappe.db.get_value("Item", src.item, "stock_uom") if src.item else "Nos",
				"rate": taxable,
				"amount": taxable,
			},
		)
		# Carry tax template
		if src.taxes_and_charges:
			target.taxes_and_charges = src.taxes_and_charges

	doc = get_mapped_doc(
		"Vehicle Sales Order",
		source_name,
		{
			"Vehicle Sales Order": {
				"doctype": "Sales Invoice",
				"field_map": {
					"customer": "customer",
					"company": "company",
					"currency": "currency",
					"conversion_rate": "conversion_rate",
					"selling_price_list": "selling_price_list",
					"price_list_currency": "price_list_currency",
					"plc_conversion_rate": "plc_conversion_rate",
					"customer_address": "customer_address",
					"contact_person": "contact_person",
					"shipping_address_name": "shipping_address_name",
					"name": "vehicle_sales_order",
				},
				"validation": {"docstatus": ["=", 1]},
			},
		},
		target_doc,
		postprocess,
	)
	return doc
