# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, today

from autods.service.charge_service_row import service_row_index
from autods.service.service_appointment_utils import get_expected_completion_datetime


class RepairEstimate(Document):
	def validate(self):
		self.set_expected_completion_from_appointment()
		self.set_financial_defaults()
		self.calculate_child_table_amounts()
		self.calculate_totals()
		self.calculate_insurance_rollups()
		self.calculate_insurance_collectibles()
		self.calculate_sales_taxes()
		self.calculate_bill_to_summaries()
		self.validate_insurance_lines()
		self.validate_charges()
		if self.validity_date and self.estimate_date and getdate(self.validity_date) < getdate(self.estimate_date):
			frappe.throw(_("Validity Date cannot be before Estimate Date"))

	def set_expected_completion_from_appointment(self):
		if not self.service_appointment:
			return
		if self.expected_completion_date and self.has_value_changed("expected_completion_date"):
			return
		if not self.expected_completion_date or self.has_value_changed("service_appointment"):
			completion = get_expected_completion_datetime(self.service_appointment)
			if completion:
				self.expected_completion_date = completion

	def set_financial_defaults(self):
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company")
		if self.company and not self.currency:
			self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
		if not self.conversion_rate:
			self.conversion_rate = 1.0

	def _charge_rows(self):
		return list(self.charges or [])

	def _service_line_count(self):
		return len([r for r in self._charge_rows() if (r.service_item_type or "").strip() == "Service"])

	def validate_charges(self):
		n_svc = self._service_line_count()
		for row in self._charge_rows():
			t = (row.service_item_type or "").strip()
			if t == "Service":
				row.service_row = ""
				continue
			if t in ("Spareparts", "Overhead"):
				sr = (row.service_row or "").strip()
				if not sr:
					frappe.throw(_("Service is required for Spareparts and Overhead lines."))
				i = service_row_index(sr)
				if i is None:
					frappe.throw(_("Service must start with a number between 1 and {0}.").format(max(n_svc, 1)))
				if n_svc < 1:
					frappe.throw(_("Add at least one Service line before Spareparts or Overhead."))
				if i < 1 or i > n_svc:
					frappe.throw(_("Service must be between 1 and {0} (Service lines in this document).").format(n_svc))

	def calculate_child_table_amounts(self):
		"""Calculate amounts for all child table rows"""
		for row in self._charge_rows():
			t = (row.service_item_type or "").strip()
			if t == "Service":
				row.amount = flt(row.qty) * flt(row.rate)
			elif t in ("Spareparts", "Overhead"):
				row.amount = flt(row.qty) * flt(row.rate)

	def calculate_totals(self):
		"""Subtotals by table, net total, and split by Bill To (bill_type)."""
		ch = self._charge_rows()
		self.total_service_items_amount = sum(
			flt(r.amount) for r in ch if (r.service_item_type or "").strip() == "Service"
		)
		self.total_parts_amount = sum(flt(r.amount) for r in ch if (r.service_item_type or "").strip() == "Spareparts")
		self.total_sundry_items_amount = sum(
			flt(r.amount) for r in ch if (r.service_item_type or "").strip() == "Overhead"
		)

		self.net_total = (
			flt(self.total_service_items_amount)
			+ flt(self.total_parts_amount)
			+ flt(self.total_sundry_items_amount)
		)

		self.total_net_customer = 0.0
		self.total_net_insurance = 0.0
		self.total_net_warranty = 0.0

		for row in ch:
			t = (row.service_item_type or "").strip()
			if t not in ("Service", "Spareparts", "Overhead"):
				continue
			amt = flt(row.amount)
			if not amt:
				continue
			self._add_bill_type_amount(amt, row.bill_type)

	def _add_bill_type_amount(self, amount, bill_type):
		if not amount:
			return
		bt = (bill_type or "Customer").strip()
		if bt == "Insurance":
			self.total_net_insurance += amount
		elif bt == "Warranty":
			self.total_net_warranty += amount
		else:
			self.total_net_customer += amount

	def calculate_insurance_rollups(self):
		"""Insurance tab: sums where bill_type = Insurance."""
		ch = self._charge_rows()
		self.insurance_billed_services_total = sum(
			flt(r.amount)
			for r in ch
			if (r.service_item_type or "").strip() == "Service" and (r.bill_type or "").strip() == "Insurance"
		)
		self.insurance_billed_parts_total = sum(
			flt(r.amount)
			for r in ch
			if (r.service_item_type or "").strip() == "Spareparts" and (r.bill_type or "").strip() == "Insurance"
		)
		self.insurance_billed_overhead_total = sum(
			flt(r.amount)
			for r in ch
			if (r.service_item_type or "").strip() == "Overhead" and (r.bill_type or "").strip() == "Insurance"
		)
		self.insurance_billed_subtotal = (
			flt(self.insurance_billed_services_total)
			+ flt(self.insurance_billed_parts_total)
			+ flt(self.insurance_billed_overhead_total)
		)

	def calculate_insurance_collectibles(self):
		self.insurance_customer_collectibles_total = (
			flt(self.insurance_participation_fee)
			+ flt(self.insurance_depreciation_fee)
			+ flt(self.insurance_other_fees_customer)
		)
		self.customer_total_responsibility = flt(self.total_net_customer) + flt(
			self.insurance_customer_collectibles_total
		)

	def calculate_sales_taxes(self):
		"""Header Sales Taxes and Charges — simplified ERPNext-style (no item-wise tax math)."""
		self.total_taxes_and_charges = 0.0
		net = flt(self.net_total)
		if not self.sales_taxes_and_charges:
			self.grand_total = net
			return

		try:
			from erpnext.controllers.accounts_controller import validate_taxes_and_charges

			for tax in self.sales_taxes_and_charges:
				validate_taxes_and_charges(tax)
		except ImportError:
			pass

		cumulative = net
		total_tax = 0.0

		for i, row in enumerate(self.sales_taxes_and_charges):
			charge_type = row.charge_type
			if charge_type == "Actual":
				amt = flt(row.tax_amount)
			elif charge_type == "On Net Total":
				amt = net * flt(row.rate) / 100.0
			elif charge_type == "On Previous Row Total":
				amt = cumulative * flt(row.rate) / 100.0
			elif charge_type == "On Previous Row Amount" and i > 0:
				prev = self.sales_taxes_and_charges[i - 1]
				amt = flt(prev.tax_amount) * flt(row.rate) / 100.0
			else:
				amt = flt(row.tax_amount)

			row.tax_amount = amt
			total_tax += amt
			cumulative += amt
			row.total = cumulative

		self.total_taxes_and_charges = total_tax
		self.grand_total = net + total_tax

	def calculate_bill_to_summaries(self):
		"""Per Bill To (Customer / Insurance / Warranty): services, parts, overhead, net, allocated tax, total.

		Tax share is proportional to each payer's net vs document net_total (header taxes apply to whole document).
		"""
		ch = self._charge_rows()
		buckets = {
			"Customer": {"Service": 0.0, "Spareparts": 0.0, "Overhead": 0.0},
			"Insurance": {"Service": 0.0, "Spareparts": 0.0, "Overhead": 0.0},
			"Warranty": {"Service": 0.0, "Spareparts": 0.0, "Overhead": 0.0},
		}
		for row in ch:
			t = (row.service_item_type or "").strip()
			if t not in ("Service", "Spareparts", "Overhead"):
				continue
			bt = (row.bill_type or "Customer").strip()
			if bt not in ("Insurance", "Warranty"):
				bt = "Customer"
			buckets[bt][t] += flt(row.amount)

		def _set(prefix, key):
			b = buckets[key]
			setattr(self, f"summary_{prefix}_services", b["Service"])
			setattr(self, f"summary_{prefix}_parts", b["Spareparts"])
			setattr(self, f"summary_{prefix}_overhead", b["Overhead"])
			net = b["Service"] + b["Spareparts"] + b["Overhead"]
			setattr(self, f"summary_{prefix}_net", net)

		_set("customer", "Customer")
		_set("insurance", "Insurance")
		_set("warranty", "Warranty")

		net_doc = flt(self.net_total)
		tax_doc = flt(self.total_taxes_and_charges)
		nets = [flt(self.total_net_customer), flt(self.total_net_insurance), flt(self.total_net_warranty)]
		prefixes = ("customer", "insurance", "warranty")
		if net_doc > 0 and tax_doc:
			allocated = []
			remaining = tax_doc
			for i, n in enumerate(nets[:-1]):
				part = flt(tax_doc * n / net_doc)
				allocated.append(part)
				remaining -= part
			allocated.append(flt(remaining))
			for i, prefix in enumerate(prefixes):
				tax_i = allocated[i]
				setattr(self, f"summary_{prefix}_tax", tax_i)
				setattr(
					self,
					f"summary_{prefix}_grand",
					flt(getattr(self, f"summary_{prefix}_net")) + tax_i,
				)
		else:
			for prefix in prefixes:
				setattr(self, f"summary_{prefix}_tax", 0.0)
				setattr(self, f"summary_{prefix}_grand", flt(getattr(self, f"summary_{prefix}_net")))

	def validate_insurance_lines(self):
		has_insurance = False
		has_warranty = False
		for line in self._charge_rows():
			bt = (line.bill_type or "").strip()
			if bt == "Insurance":
				has_insurance = True
			elif bt == "Warranty":
				has_warranty = True
		if has_insurance and not self.insurance_company:
			frappe.throw(_("Insurance Company is required when any line has Bill To = Insurance."))
		if has_warranty and not self.warranty:
			frappe.throw(_("Warranty is required when any line has Bill To = Warranty."))

	def on_submit(self):
		"""Set status to Submitted when estimate is submitted for approval"""
		if self.status == "Draft":
			frappe.db.set_value("Repair Estimate", self.name, "status", "Submitted")
			self.status = "Submitted"

	@frappe.whitelist()
	def fetch_template_items(self, service_template=None):
		"""Fetch charges and service inspections from Service Template."""
		from autods.service.template_charges import charge_row_from_template

		if not service_template:
			frappe.throw(_("Please select a Service Template"))
		template_name = service_template
		try:
			template = frappe.get_doc("Service Template", template_name)
			self.service_template = template_name
			self.charges = []

			for row in template.charges or []:
				charge_row = charge_row_from_template(row.as_dict(), template_name)
				if getattr(row, "item_tax_template", None):
					charge_row["item_tax_template"] = row.item_tax_template
				self.append("charges", charge_row)

			if template.service_inspections:
				for template_inspection in template.service_inspections:
					existing = [
						qi
						for qi in (self.quality_inspections or [])
						if qi.inspection_name == template_inspection.inspection_name
					]
					if not existing:
						self.append(
							"quality_inspections",
							{
								"inspection_name": template_inspection.inspection_name,
								"status": "Pending",
							},
						)

			self.calculate_child_table_amounts()
			self.calculate_totals()
			self.calculate_insurance_rollups()
			self.calculate_insurance_collectibles()
			self.calculate_sales_taxes()
			self.calculate_bill_to_summaries()
			ch = self.charges or []
			frappe.msgprint(_("Items fetched from Service Template {0}").format(frappe.bold(template_name)))
			if self.name:
				self.save(ignore_permissions=True)
			return {
				"service_items_count": len([r for r in ch if (r.service_item_type or "").strip() == "Service"]),
				"spareparts_count": len([r for r in ch if (r.service_item_type or "").strip() == "Spareparts"]),
				"sundry_items_count": len([r for r in ch if (r.service_item_type or "").strip() == "Overhead"]),
				"service_inspections_count": len(
					[qi for qi in (self.quality_inspections or []) if qi.inspection_name]
				),
				"doc": self.as_dict(),
			}
		except frappe.DoesNotExistError:
			frappe.throw(_("Service Template {0} not found").format(frappe.bold(template_name)))
		except Exception as e:
			frappe.log_error(f"Error fetching template items: {str(e)}", "Repair Estimate - Fetch Template")
			frappe.throw(_("Error fetching items from template: {0}").format(str(e)))

	@frappe.whitelist()
	def create_repair_order(self):
		"""Create Repair Order from this approved estimate. Only when status is Approved and not yet converted."""
		if self.docstatus != 1:
			frappe.throw(_("Repair Estimate must be submitted before creating a Repair Order"))
		if self.status not in ("Submitted", "Approved"):
			frappe.throw(_("Only a Submitted or Approved estimate can be converted to a Repair Order"))
		if self.repair_order:
			frappe.throw(_("This estimate is already converted to Repair Order {0}").format(self.repair_order))

		ch = self.charges or []
		if not ch:
			frappe.throw(_("Add at least one charge line before creating a Repair Order."))

		ro = frappe.new_doc("Repair Order")
		# Header - align with Repair Order fields
		ro.repair_estimate = self.name
		if ro.meta.get_field("service_template") and getattr(self, "service_template", None):
			ro.service_template = self.service_template
		ro.repair_date = self.validity_date or today()
		if ro.meta.get_field("estimate_date"):
			ro.estimate_date = self.estimate_date
		if ro.meta.get_field("validity_date"):
			ro.validity_date = self.validity_date
		if ro.meta.get_field("status"):
			ro.status = "Draft"
		ro.customer = self.customer
		ro.vehicle_unit = self.vehicle_unit
		ro.repair_type = self.repair_type
		if ro.meta.get_field("service_type"):
			ro.service_type = self.service_type
		ro.service_advisor = self.service_advisor
		ro.odometer = self.odometer
		if ro.meta.get_field("service_appointment"):
			ro.service_appointment = getattr(self, "service_appointment", None)
		if ro.service_appointment:
			ro.expected_completion_date = get_expected_completion_datetime(ro.service_appointment)
		else:
			ro.expected_completion_date = self.expected_completion_date
		ro.insurance_claim_no = self.insurance_claim_no
		ro.insurance_company = self.insurance_company
		ro.warranty = self.warranty
		if ro.meta.get_field("company"):
			ro.company = self.company
		if ro.meta.get_field("currency"):
			ro.currency = self.currency
		if ro.meta.get_field("conversion_rate"):
			ro.conversion_rate = self.conversion_rate or 1.0
		if ro.meta.get_field("insurance_participation_fee"):
			ro.insurance_participation_fee = self.insurance_participation_fee
		if ro.meta.get_field("insurance_depreciation_fee"):
			ro.insurance_depreciation_fee = self.insurance_depreciation_fee
		if ro.meta.get_field("insurance_other_fees_customer"):
			ro.insurance_other_fees_customer = self.insurance_other_fees_customer
		if ro.meta.get_field("insurance_other_fees_description"):
			ro.insurance_other_fees_description = self.insurance_other_fees_description
		ro.service_level_agreement = self.service_level_agreement
		ro.sla_notes = self.sla_notes
		ro.terms_and_conditions = self.terms_and_conditions
		if self.terms_and_conditions:
			ro.tc_notes = frappe.db.get_value("Terms and Conditions", self.terms_and_conditions, "terms")

		if ro.meta.get_field("tax_category"):
			ro.tax_category = self.tax_category
		if ro.meta.get_field("taxes_and_charges"):
			ro.taxes_and_charges = self.taxes_and_charges
		if ro.meta.get_field("sales_taxes_and_charges") and self.sales_taxes_and_charges:
			for row in self.sales_taxes_and_charges:
				tax_row = {
					"charge_type": row.charge_type,
					"account_head": row.account_head,
					"description": row.description,
					"rate": row.rate,
					"tax_amount": row.tax_amount,
				}
				if row.get("row_id"):
					tax_row["row_id"] = row.row_id
				ro.append("sales_taxes_and_charges", tax_row)

		# Concerns
		for row in self.concerns or []:
			ro.append(
				"concerns",
				{
					"customer_concern": row.customer_concern,
					"concern_category": row.concern_category,
					"concern": row.concern,
					"description": row.description,
					"notes": row.notes,
				},
			)
		# Diagnostics
		for row in self.diagnostics or []:
			ro.append(
				"diagnostics",
				{
					"customer_concern": row.customer_concern,
					"concern": row.concern,
					"diagnostic": row.diagnostic,
					"notes": row.notes,
				},
			)
		# Unified charges
		ro_meta_charges = ro.meta.get_field("charges")
		for row in ch:
			t = (row.service_item_type or "").strip()
			if not t:
				continue
			entry = {
				"service_item_type": t,
				"item": row.item,
				"item_name": getattr(row, "item_name", None),
				"description": getattr(row, "description", None),
				"service_row": getattr(row, "service_row", None) if t in ("Spareparts", "Overhead") else None,
				"standard_hours": getattr(row, "standard_hours", None) if t == "Service" else None,
				"qty": getattr(row, "qty", None) if t in ("Service", "Spareparts", "Overhead") else None,
				"uom": getattr(row, "uom", None) if t in ("Service", "Spareparts", "Overhead") else None,
				"rate": row.rate,
				"amount": row.amount,
				"bill_type": row.bill_type,
				"bill_to": getattr(row, "bill_to", None),
				"item_type": getattr(row, "item_type", None),
				"warehouse": getattr(row, "warehouse", None),
				"color_code": getattr(row, "color_code", None),
				"paint_type": getattr(row, "paint_type", None),
				"service_template": getattr(row, "service_template", None),
			}
			if ro_meta_charges:
				ro.append("charges", entry)

		# Optional: Service Inspections
		for row in self.quality_inspections or []:
			ro.append(
				"quality_inspections",
				{
					"inspection_name": row.inspection_name,
					"quality_inspection": row.quality_inspection,
					"status": row.status,
					"inspection_date": row.inspection_date,
					"inspected_by": row.inspected_by,
					"remarks": row.remarks,
				},
			)
		# Optional: Photos
		for row in self.photos or []:
			ro.append(
				"photos",
				{
					"photo_type": row.photo_type,
					"description": row.description,
					"image": row.image,
					"taken_date": row.taken_date,
					"taken_by": row.taken_by,
				},
			)

		ro.insert()

		# Update estimate: status and link to RO
		frappe.db.set_value("Repair Estimate", self.name, "status", "Converted to RO")
		frappe.db.set_value("Repair Estimate", self.name, "repair_order", ro.name)
		frappe.db.commit()

		frappe.msgprint(_("Repair Order {0} created from estimate").format(frappe.bold(ro.name)))
		return ro.name


@frappe.whitelist()
def get_expected_completion_for_appointment(service_appointment):
	"""Return combined expected completion datetime from Service Appointment (for client form sync)."""
	return get_expected_completion_datetime(service_appointment)


@frappe.whitelist()
def get_tax_rows_from_template(template):
	"""Return tax rows from Sales Taxes and Charges Template (for client populate)."""
	if not template:
		return []
	try:
		from erpnext.controllers.accounts_controller import get_taxes_and_charges

		return get_taxes_and_charges("Sales Taxes and Charges Template", template) or []
	except ImportError:
		return []


@frappe.whitelist()
def create_repair_order(doctype=None, name=None):
	"""Module-level wrapper so Frappe can resolve the command; calls doc.create_repair_order()."""
	if not doctype:
		doctype = frappe.form_dict.get("doctype", "Repair Estimate")
	if not name:
		name = frappe.form_dict.get("name") or frappe.form_dict.get("docname")
	if not name:
		frappe.throw(_("Repair Estimate document is required"))
	doc_obj = frappe.get_doc(doctype, name)
	return doc_obj.create_repair_order()


@frappe.whitelist()
def fetch_template_items(doctype=None, name=None, service_template=None, doc=None):
	"""Module-level wrapper for RepairEstimate.fetch_template_items (supports new/saved docs)."""
	if not doctype:
		doctype = frappe.form_dict.get("doctype", "Repair Estimate")
	if not name:
		name = frappe.form_dict.get("name")
	if not service_template:
		service_template = frappe.form_dict.get("service_template")
	if not doc:
		doc = frappe.form_dict.get("doc")

	if doc:
		if isinstance(doc, str):
			try:
				doc = frappe.parse_json(doc)
			except Exception:
				pass
		if isinstance(doc, dict):
			if doc.get("name"):
				doc_obj = frappe.get_doc(doctype, doc["name"])
			else:
				doc_obj = frappe.new_doc(doctype)
				doc_obj.update(doc)
		else:
			frappe.throw(_("Invalid document format"))
	elif name:
		doc_obj = frappe.get_doc(doctype, name)
	else:
		frappe.throw(_("Repair Estimate document is required"))

	result = doc_obj.fetch_template_items(service_template=service_template)
	result["doc"] = doc_obj.as_dict()
	return result
