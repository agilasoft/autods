# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, getdate

from autods.vehicle_sales.quote_status import validate_lost_reason


class VehicleSalesQuote(Document):
	def validate(self):
		self._set_currency_defaults()
		self._compute_accessory_lines()
		self._compute_totals()
		self._set_status_on_validate()

	def on_submit(self):
		self.db_set("status", "Open")
		self._update_opportunity_status("Quotation")

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		self._update_opportunity_status("Open")

	def _update_opportunity_status(self, status):
		if not self.opportunity or not frappe.db.exists("Opportunity", self.opportunity):
			return
		opp = frappe.get_doc("Opportunity", self.opportunity)
		opp.set_status(status=status, update=True)

	def _set_currency_defaults(self):
		if not self.currency and self.company:
			self.currency = frappe.db.get_value("Company", self.company, "default_currency")
		if not self.price_list_currency and self.selling_price_list:
			self.price_list_currency = (
				frappe.db.get_value("Price List", self.selling_price_list, "currency") or self.currency
			)
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
		"""Calculate row tax_amount and total for the simple ad-valorem rows."""
		total = 0.0
		for row in self.get("taxes") or []:
			rate = flt(row.rate, 6)
			if row.charge_type in ("On Net Total", "Actual"):
				if row.charge_type == "On Net Total":
					row.tax_amount = flt(taxable * rate / 100, 2)
				else:
					row.tax_amount = flt(row.tax_amount, 2)
			else:
				row.tax_amount = flt(row.tax_amount, 2)
			row.base_tax_amount = flt(row.tax_amount * flt(self.conversion_rate or 1), 2)
			total += flt(row.tax_amount, 2)
			row.total = flt(taxable + total, 2)
			row.base_total = flt(row.total * flt(self.conversion_rate or 1), 2)
		return flt(total, 2)

	@frappe.whitelist()
	def declare_lost(self, lost_reason, competitor=None):
		"""Mark a submitted quote Lost. Ordered quotes stay Ordered."""
		if self.docstatus != 1:
			frappe.throw(_("Submit the quote before marking it Lost."))
		if self.status == "Ordered":
			frappe.throw(_("Quote {0} is already ordered.").format(self.name))
		if self.status in ("Cancelled", "Lost"):
			frappe.throw(_("Quote {0} is already {1}.").format(self.name, self.status))
		reason = validate_lost_reason(lost_reason)
		if not reason:
			frappe.throw(_("A lost reason is required."))
		self.db_set("lost_reason", reason)
		self.db_set("competitor", (competitor or "").strip() or None)
		self.db_set("status", "Lost")
		return self.status

	def _set_status_on_validate(self):
		if self.docstatus == 0 and not self.status:
			self.status = "Draft"
		if (
			self.valid_till
			and getdate(self.valid_till) < getdate()
			and self.status not in ("Ordered", "Cancelled", "Lost")
		):
			self.status = "Expired"


@frappe.whitelist()
def make_from_opportunity(source_name, target_doc=None):
	"""Map an Opportunity to a Vehicle Sales Quote.

	Customer (`party_name`) is copied only when Opportunity From is Customer.
	Lead / Prospect party names are never written into the Customer Link field.
	"""

	def postprocess(source, target):
		target.naming_series = target.naming_series or "VSQ-.YYYY.-"
		target.transaction_date = target.transaction_date or frappe.utils.getdate()
		target.status = target.status or "Draft"
		target.order_type = target.order_type or "Sales"
		target.opportunity = source.name

		if source.opportunity_from != "Customer":
			target.party_name = None
			target.customer_name = None

	doc = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {
				"doctype": "Vehicle Sales Quote",
				"field_map": {
					"name": "opportunity",
					"company": "company",
					"currency": "currency",
					"conversion_rate": "conversion_rate",
					"contact_person": "contact_person",
					"customer_address": "customer_address",
					"contact_email": "contact_email",
					"contact_mobile": "contact_mobile",
				},
				"field_no_map": ["party_name", "customer_name"],
			},
		},
		target_doc,
		postprocess,
	)

	# Map Customer only when Opportunity From is Customer (after field_no_map).
	source = frappe.get_doc("Opportunity", source_name)
	if source.opportunity_from == "Customer" and source.party_name:
		doc.party_name = source.party_name
		doc.customer_name = source.customer_name

	return doc


@frappe.whitelist()
def make_from_lead(source_name, target_doc=None):
	"""Map a Lead to a Vehicle Sales Quote.

	Customer (`party_name`) is left empty — Lead is not a Customer.
	Contact email / mobile are copied when present.
	"""

	def postprocess(source, target):
		target.naming_series = target.naming_series or "VSQ-.YYYY.-"
		target.transaction_date = target.transaction_date or frappe.utils.getdate()
		target.status = target.status or "Draft"
		target.order_type = target.order_type or "Sales"
		target.company = target.company or frappe.defaults.get_user_default("Company")
		target.party_name = None
		target.customer_name = None
		target.contact_email = source.email_id or target.contact_email
		target.contact_mobile = source.mobile_no or target.contact_mobile

	return get_mapped_doc(
		"Lead",
		source_name,
		{
			"Lead": {
				"doctype": "Vehicle Sales Quote",
				"field_no_map": ["party_name", "customer_name", "opportunity"],
			},
		},
		target_doc,
		postprocess,
	)


@frappe.whitelist()
def make_from_prospect(source_name, target_doc=None):
	"""Map a Prospect to a Vehicle Sales Quote.

	Customer (`party_name`) is left empty — Prospect is not a Customer.
	"""

	def postprocess(source, target):
		target.naming_series = target.naming_series or "VSQ-.YYYY.-"
		target.transaction_date = target.transaction_date or frappe.utils.getdate()
		target.status = target.status or "Draft"
		target.order_type = target.order_type or "Sales"
		target.company = source.company or target.company or frappe.defaults.get_user_default("Company")
		target.party_name = None
		target.customer_name = None

	return get_mapped_doc(
		"Prospect",
		source_name,
		{
			"Prospect": {
				"doctype": "Vehicle Sales Quote",
				"field_no_map": ["party_name", "customer_name", "opportunity"],
			},
		},
		target_doc,
		postprocess,
	)


@frappe.whitelist()
def make_from_customer(source_name, target_doc=None):
	"""Map a Customer to a Vehicle Sales Quote with party_name prefilled."""

	def postprocess(source, target):
		target.naming_series = target.naming_series or "VSQ-.YYYY.-"
		target.transaction_date = target.transaction_date or frappe.utils.getdate()
		target.status = target.status or "Draft"
		target.order_type = target.order_type or "Sales"
		target.company = target.company or frappe.defaults.get_user_default("Company")
		target.party_name = source.name
		target.customer_name = source.customer_name
		if source.default_currency:
			target.currency = source.default_currency

	return get_mapped_doc(
		"Customer",
		source_name,
		{
			"Customer": {
				"doctype": "Vehicle Sales Quote",
				"field_map": {"name": "party_name"},
				"field_no_map": ["opportunity"],
			},
		},
		target_doc,
		postprocess,
	)


@frappe.whitelist()
def make_sales_order(source_name, target_doc=None):
	"""Map a Vehicle Sales Quote to a Vehicle Sales Order."""

	def update_item(source, target, source_parent):
		target.amount = source.amount

	def postprocess(source, target):
		target.transaction_date = frappe.utils.getdate()
		target.delivery_date = frappe.utils.add_days(frappe.utils.getdate(), 7)
		target.vehicle_sales_quote = source.name
		target.naming_series = "VSO-.YYYY.-"
		target.status = "Draft"
		target.delivery_status = "Not Delivered"
		target.billing_status = "Not Billed"

	doc = get_mapped_doc(
		"Vehicle Sales Quote",
		source_name,
		{
			"Vehicle Sales Quote": {
				"doctype": "Vehicle Sales Order",
				"field_map": {
					"name": "vehicle_sales_quote",
					"party_name": "customer",
				},
				"validation": {"docstatus": ["=", 1]},
			},
			"Vehicle Sales Quote Accessory": {
				"doctype": "Vehicle Sales Order Accessory",
				"field_map": {},
				"postprocess": update_item,
			},
		},
		target_doc,
		postprocess,
	)
	return doc
