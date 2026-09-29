# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, nowdate, nowtime

from autods.service.charge_service_row import (
	persist_charge_service_links,
	resolve_charge_parent_service_links,
	validate_charge_service_links,
)
from autods.service.job_card_planning import get_locked_charge_row_names
from autods.service.gate_pass_utils import has_entry_gate_pass, require_entry_gate_pass
from autods.service.service_appointment_utils import get_expected_completion_datetime
from autods.service.service_inspection_sync import (
	find_service_inspection,
	sync_repair_order_inspection_links,
)


class RepairOrder(Document):
	def validate(self):
		self.set_expected_completion_from_appointment()
		self.set_financial_defaults()
		self.sync_service_inspection_links()
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

	def before_submit(self):
		require_entry_gate_pass(
			vehicle_unit=self.vehicle_unit,
			repair_order=self.name,
			customer=self.customer,
			context=_("Repair Order submission"),
		)

	def set_expected_completion_from_appointment(self):
		if not self.service_appointment:
			return
		if self.expected_completion_date and self.has_value_changed("expected_completion_date"):
			return
		if not self.expected_completion_date or self.has_value_changed("service_appointment"):
			completion = get_expected_completion_datetime(self.service_appointment)
			if completion:
				self.expected_completion_date = completion

	def sync_service_inspection_links(self):
		sync_repair_order_inspection_links(self)

	def set_financial_defaults(self):
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company")
		if self.company and not self.currency:
			self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
		if not self.conversion_rate:
			self.conversion_rate = 1.0

	def _charge_rows(self):
		return list(self.charges or [])

	def validate_charges(self):
		from autods.service.job_card_planning import (
			validate_charges_not_locked,
			validate_no_new_links_to_locked_services,
		)

		validate_charges_not_locked(self)
		validate_charge_service_links(self)
		validate_no_new_links_to_locked_services(self)

	def after_insert(self):
		persist_charge_service_links(self, "Repair Order Charges")

	def calculate_child_table_amounts(self):
		for row in self._charge_rows():
			t = (row.service_item_type or "").strip()
			if t == "Service":
				row.amount = flt(row.qty) * flt(row.rate)
			elif t in ("Spareparts", "Overhead"):
				row.amount = flt(row.qty) * flt(row.rate)
		for row in self.table_wlxj or []:
			row.amount = flt(row.qty) * flt(row.rate)
		for row in self.insurance_bills or []:
			row.amount = flt(row.qty) * flt(row.rate)

	def calculate_totals(self):
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
		"""Per Bill To: services, parts, overhead, net, proportional share of header taxes, total."""
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

	@frappe.whitelist()
	def fetch_template_items(self, service_template=None):
		"""Fetch charges and service inspections from Service Template (Actions → Load Service Template)."""
		from autods.service.template_charges import apply_template_terms, charge_row_from_template

		if not service_template:
			frappe.throw(_("Please select a Service Template"))
		template_name = service_template
		try:
			template = frappe.get_doc("Service Template", template_name)
			self.service_template = template_name
			apply_template_terms(self, template)
			self.charges = []

			for row in template.charges or []:
				charge_row = charge_row_from_template(row.as_dict(), template_name)
				if getattr(row, "item_tax_template", None):
					charge_row["item_tax_template"] = row.item_tax_template
				self.append("charges", charge_row)

			resolve_charge_parent_service_links(self)

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
			frappe.log_error(f"Error fetching template items: {str(e)}", "Repair Order - Fetch Template")
			frappe.throw(_("Error fetching items from template: {0}").format(str(e)))

	@frappe.whitelist()
	def get_job_card_plan(self, selected_charge_rows=None):
		"""Preview the Job Card plan for selected Service lines on this Repair Order."""
		from autods.service.job_card_planning import build_plan

		return build_plan(self, _parse_selected_charge_rows(selected_charge_rows))

	@frappe.whitelist()
	def create_job_cards_from_plan(self, selected_charge_rows=None):
		"""Create one Job Card per selected Service line (skipped when one already exists)."""
		from autods.service.job_card_planning import create_job_cards

		return create_job_cards(self, _parse_selected_charge_rows(selected_charge_rows))

	@frappe.whitelist()
	def create_gate_pass(self, gate_pass_type="Entry"):
		"""Create an entry/exit Gate Pass prefilled from this Repair Order."""
		if not self.name:
			frappe.throw(_("Save the Repair Order before creating a Gate Pass"))
		if not self.vehicle_unit:
			frappe.throw(_("Vehicle Unit is required to create a Gate Pass"))

		gate_pass_type = gate_pass_type if gate_pass_type in ("Entry", "Exit", "Both") else "Entry"
		if gate_pass_type == "Entry":
			existing = frappe.get_all(
				"Gate Pass",
				filters={
					"repair_order": self.name,
					"gate_pass_type": ("in", ("Entry", "Both")),
					"status": ("in", ("Entry Only", "Completed")),
				},
				pluck="name",
				limit_page_length=1,
			)
			if existing:
				return {"doctype": "Gate Pass", "name": existing[0], "existing": True}
		elif not has_entry_gate_pass(vehicle_unit=self.vehicle_unit, repair_order=self.name, customer=self.customer):
			frappe.throw(_("Create a Gate Pass Entry before creating an exit pass."))

		gate_pass = frappe.new_doc("Gate Pass")
		gate_pass.gate_pass_type = gate_pass_type
		gate_pass.repair_order = self.name
		gate_pass.customer = self.customer
		gate_pass.vehicle_unit = self.vehicle_unit
		gate_pass.plate_no = self.plate_no
		if gate_pass_type == "Entry":
			gate_pass.entry_date = nowdate()
			gate_pass.entry_time = nowtime()
			gate_pass.status = "Entry Only"
		elif gate_pass_type == "Exit":
			gate_pass.exit_date = nowdate()
			gate_pass.exit_time = nowtime()
			gate_pass.status = "Exit Only"
		else:
			gate_pass.entry_date = nowdate()
			gate_pass.entry_time = nowtime()
			gate_pass.exit_date = nowdate()
			gate_pass.exit_time = nowtime()
			gate_pass.status = "Completed"
		gate_pass.insert()
		frappe.msgprint(_("Gate Pass {0} created.").format(frappe.bold(gate_pass.name)))
		return {"doctype": gate_pass.doctype, "name": gate_pass.name}


def get_dashboard_data(data=None):
	"""Show Sales Invoices linked by the Repair Order accounting dimension."""
	data = data or {}
	try:
		has_link = frappe.get_meta("Sales Invoice").has_field("repair_order")
	except Exception:
		has_link = False
	if not has_link:
		return data
	data.setdefault("non_standard_fieldnames", {})["Sales Invoice"] = "repair_order"
	transactions = data.setdefault("transactions", [])
	already = any(
		"Sales Invoice" in (group.get("items") or [])
		for group in transactions
		if isinstance(group, dict)
	)
	if not already:
		transactions.append({"label": _("Billing"), "items": ["Sales Invoice"]})
	return data


@frappe.whitelist()
def get_service_inspection_by_name(repair_order, inspection_name):
	"""Return Service Inspection linked to a Repair Order row by inspection_name."""
	if not repair_order or not inspection_name:
		return None
	frappe.has_permission("Repair Order", "read", repair_order, throw=True)
	return find_service_inspection(repair_order, (inspection_name or "").strip())


@frappe.whitelist()
def get_repair_order_inspection_names(repair_order):
	"""Return inspection_name values from a Repair Order quality_inspections table."""
	if not repair_order:
		return []
	frappe.has_permission("Repair Order", "read", repair_order, throw=True)
	return frappe.get_all(
		"Repair Order Service Inspection",
		filters={"parent": repair_order, "parenttype": "Repair Order"},
		pluck="inspection_name",
		order_by="idx",
	)


@frappe.whitelist()
def get_job_card_service_selection(repair_order):
	"""Return Service charge lines for the job card selection modal."""
	if not repair_order:
		frappe.throw(_("Repair Order is required"))
	ro = frappe.get_doc("Repair Order", repair_order)
	ro.check_permission("read")
	from autods.service.job_card_planning import build_service_selection

	return build_service_selection(ro)


@frappe.whitelist()
def get_locked_charge_rows(repair_order):
	"""Return {charge_row_name: job_card_name} for rows locked by a non-Cancelled Job Card."""
	if not repair_order:
		return {}
	ro = frappe.get_doc("Repair Order", repair_order)
	ro.check_permission("read")
	return get_locked_charge_row_names(ro)


def _parse_selected_charge_rows(selected_charge_rows):
	if not selected_charge_rows:
		return None
	if isinstance(selected_charge_rows, str):
		selected_charge_rows = frappe.parse_json(selected_charge_rows)
	if not isinstance(selected_charge_rows, (list, tuple)):
		frappe.throw(_("selected_charge_rows must be a list"))
	return list(selected_charge_rows)


@frappe.whitelist()
def get_job_card_plan_by_repair_order(repair_order, selected_charge_rows=None):
	"""Preview job card plan for a Repair Order (for Service Appointment / Repair Estimate)."""
	if not repair_order:
		frappe.throw(_("Repair Order is required"))
	ro = frappe.get_doc("Repair Order", repair_order)
	ro.check_permission("read")
	from autods.service.job_card_planning import build_plan

	return build_plan(ro, _parse_selected_charge_rows(selected_charge_rows))


@frappe.whitelist()
def create_job_cards_from_plan_by_repair_order(repair_order, selected_charge_rows=None):
	"""Create job cards from plan for a Repair Order (for Service Appointment / Repair Estimate)."""
	if not repair_order:
		frappe.throw(_("Repair Order is required"))
	ro = frappe.get_doc("Repair Order", repair_order)
	from autods.service.job_card_planning import create_job_cards

	return create_job_cards(ro, _parse_selected_charge_rows(selected_charge_rows))


@frappe.whitelist()
def get_service_templates_filtered(
	vehicle_make=None,
	vehicle_model=None,
	vehicle_variant=None,
	vehicle_year_model=None,
	vehicle_transmission_type=None,
	vehicle_fuel_type=None,
	vehicle_body_type=None,
	vehicle_drive_type=None,
	template_name=None,
	template_name_like=None,
):
	frappe.has_permission("Service Template", "read", throw=True)

	filters = []

	def _add(field, value):
		if value is None or value == "":
			return
		filters.append([field, "=", value])

	_add("vehicle_make", vehicle_make)
	_add("vehicle_model", vehicle_model)
	_add("vehicle_variant", vehicle_variant)
	_add("vehicle_transmission_type", vehicle_transmission_type)
	_add("vehicle_fuel_type", vehicle_fuel_type)
	_add("vehicle_body_type", vehicle_body_type)
	_add("vehicle_drive_type", vehicle_drive_type)

	if vehicle_year_model is not None and vehicle_year_model != "":
		try:
			filters.append(["vehicle_year_model", "=", int(vehicle_year_model)])
		except (TypeError, ValueError):
			pass

	if template_name:
		if cint(template_name_like):
			filters.append(
				[
					"template_name",
					"like",
					"%{0}%".format(frappe.db.escape(template_name, percent=False)),
				]
			)
		else:
			filters.append(["template_name", "=", template_name])

	if not filters:
		filters = [["is_active", "=", 1]]

	fields = [
		"name",
		"template_name",
		"vehicle_make",
		"vehicle_model",
		"vehicle_variant",
		"vehicle_year_model",
	]

	return frappe.get_all(
		"Service Template",
		filters=filters,
		fields=fields,
		order_by="modified desc",
		limit_page_length=200,
	)


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
def fetch_template_items(doctype=None, name=None, service_template=None, doc=None):
	if not doctype:
		doctype = frappe.form_dict.get("doctype", "Repair Order")
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
		frappe.throw(_("Repair Order document is required"))

	result = doc_obj.fetch_template_items(service_template=service_template)
	result["doc"] = doc_obj.as_dict()
	return result


@frappe.whitelist()
def get_sales_invoice_payers(repair_order):
	"""Payers that have an amount on this Repair Order, and any open Sales Invoice for each."""
	if not repair_order:
		return []
	doc = frappe.get_doc("Repair Order", repair_order)
	doc.check_permission("read")
	from autods.service.repair_order_invoice import (
		RepairInvoiceError,
		build_invoice_groups,
		collectible_items_from_settings,
		find_open_sales_invoice,
	)

	try:
		groups = build_invoice_groups(
			doc,
			doc.charges,
			doc.sales_taxes_and_charges,
			collectible_items_from_settings(),
		)
	except RepairInvoiceError as exc:
		frappe.throw(str(exc))

	payers = []
	for group in groups:
		if not group.get("net"):
			continue
		customer_name = group.get("bill_to")
		if group.get("bill_to") and frappe.db.exists("Customer", group["bill_to"]):
			customer_name = frappe.db.get_value("Customer", group["bill_to"], "customer_name") or customer_name
		payers.append(
			{
				"bill_type": group["bill_type"],
				"bill_to": group["bill_to"],
				"customer_name": customer_name,
				"net": group["net"],
				"sales_invoice": find_open_sales_invoice(doc.name, group["bill_type"], group["bill_to"]),
			}
		)
	return payers


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, args=None):
	"""Map a submitted Repair Order to a draft Sales Invoice for one payer.

	Called by ``frappe.model.open_mapped_doc``. ``args`` carries ``bill_type`` and ``bill_to``.
	"""
	from frappe.model.mapper import get_mapped_doc

	from autods.service.repair_order_invoice import (
		RepairInvoiceError,
		build_invoice_groups,
		collectible_items_from_settings,
		invoice_lines,
		select_invoice_group,
	)

	if isinstance(args, str):
		args = frappe.parse_json(args)
	args = args or {}
	bill_type = args.get("bill_type")
	bill_to = args.get("bill_to")
	# open_mapped_doc passes selected child rows in this argument, not a target doc.
	if isinstance(target_doc, (str, list, tuple)):
		target_doc = None

	source = frappe.get_doc("Repair Order", source_name)
	source.check_permission("read")
	frappe.has_permission("Sales Invoice", "create", throw=True)
	if source.docstatus != 1:
		frappe.throw(_("Submit the Repair Order before creating a Sales Invoice."))
	if not source.company:
		frappe.throw(_("Company is required on the Repair Order."))

	try:
		groups = build_invoice_groups(
			source,
			source.charges,
			source.sales_taxes_and_charges,
			collectible_items_from_settings(),
		)
		group = select_invoice_group(groups, bill_type, bill_to)
	except RepairInvoiceError as exc:
		frappe.throw(str(exc))

	if not group.get("bill_to"):
		frappe.throw(_("Bill To is required for the {0} invoice.").format(group["bill_type"]))

	def postprocess(src, target):
		target.customer = group["bill_to"]
		target.company = src.company
		target.currency = src.currency
		target.conversion_rate = src.conversion_rate or 1
		target.update_stock = 0
		target.ignore_pricing_rule = 1
		target.tax_category = src.tax_category
		target.taxes_and_charges = src.taxes_and_charges
		if target.meta.has_field("custom_repair_bill_type"):
			target.custom_repair_bill_type = group["bill_type"]
		if target.meta.has_field("repair_order"):
			target.repair_order = src.name
		if src.vehicle_unit and target.meta.has_field("vehicle_unit"):
			target.vehicle_unit = src.vehicle_unit
		target.remarks = _("From Repair Order {0} ({1})").format(src.name, group["bill_type"])

		applied = []
		for line in invoice_lines(group["lines"]):
			row = target.append("items", line)
			applied.append((row, row.rate))
			if src.vehicle_unit and row.meta.has_field("vehicle_unit"):
				row.vehicle_unit = src.vehicle_unit
			if row.meta.has_field("repair_order"):
				row.repair_order = src.name
		if hasattr(target, "set_missing_values"):
			target.set_missing_values()
		for row, rate in applied:
			row.rate = rate
			row.amount = flt(rate) * flt(row.qty)
		target.update_stock = 0
		target.taxes = []
		for tax in group["taxes"]:
			target.append("taxes", tax)
		if hasattr(target, "calculate_taxes_and_totals"):
			target.calculate_taxes_and_totals()
		target.update_stock = 0

	return get_mapped_doc(
		"Repair Order",
		source_name,
		{
			"Repair Order": {
				"doctype": "Sales Invoice",
				"field_map": {
					"company": "company",
					"currency": "currency",
					"conversion_rate": "conversion_rate",
				},
				"field_no_map": [
					"customer",
					"status",
					"naming_series",
					"amended_from",
					"net_total",
					"grand_total",
					"total_taxes_and_charges",
					"charges",
					"sales_taxes_and_charges",
				],
				"validation": {"docstatus": ["=", 1]},
			},
			# Lines and taxes are built per payer in postprocess.
			"Repair Order Charges": {
				"doctype": "Sales Invoice Item",
				"condition": lambda row: False,
			},
			"Sales Taxes and Charges": {
				"doctype": "Sales Taxes and Charges",
				"condition": lambda row: False,
			},
		},
		target_doc,
		postprocess,
	)
