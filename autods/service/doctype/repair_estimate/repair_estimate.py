# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today


class RepairEstimate(Document):
	def validate(self):
		self.calculate_child_table_amounts()
		self.calculate_totals()
		if self.validity_date and self.estimate_date and getdate(self.validity_date) < getdate(self.estimate_date):
			frappe.throw(_("Validity Date cannot be before Estimate Date"))

	def calculate_child_table_amounts(self):
		"""Calculate amounts for all child table rows"""
		for item in self.service_items or []:
			item.amount = flt(item.hours) * flt(item.rate)
		for part in self.spareparts or []:
			part.amount = flt(part.qty) * flt(part.rate)
		for item in self.sundry_items or []:
			item.amount = flt(item.qty) * flt(item.rate)

	def calculate_totals(self):
		"""Calculate totals from child tables"""
		self.total_service_items_amount = sum(flt(item.amount) for item in self.service_items or [])
		self.total_parts_amount = sum(flt(item.amount) for item in self.spareparts or [])
		self.total_sundry_items_amount = sum(flt(item.amount) for item in self.sundry_items or [])
		self.grand_total = (
			flt(self.total_service_items_amount)
			+ flt(self.total_parts_amount)
			+ flt(self.total_sundry_items_amount)
		)

	def on_submit(self):
		"""Set status to Submitted when estimate is submitted for approval"""
		if self.status == "Draft":
			frappe.db.set_value("Repair Estimate", self.name, "status", "Submitted")
			self.status = "Submitted"

	@frappe.whitelist()
	def fetch_template_items(self, service_template=None):
		"""Fetch service items, spareparts, and sundry items from Service Template (same as Repair Order)."""
		if not service_template:
			frappe.throw(_("Please select a Service Template"))
		template_name = service_template
		try:
			template = frappe.get_doc("Service Template", template_name)
			self.service_items = []
			self.spareparts = []
			self.sundry_items = []

			if template.service_items:
				for template_item in template.service_items:
					self.append("service_items", {
						"service_item": template_item.service_item,
						"service_category": template_item.service_category,
						"description": template_item.description,
						"bill_type": template_item.bill_type,
						"bill_to": template_item.bill_to,
						"hours": template_item.hours,
						"rate": template_item.rate,
					})
			if template.spareparts:
				for template_part in template.spareparts:
					self.append("spareparts", {
						"item": template_part.item,
						"item_name": template_part.item_name,
						"item_type": template_part.item_type,
						"qty": template_part.qty,
						"uom": template_part.uom,
						"rate": template_part.rate,
						"bill_type": template_part.bill_type,
						"bill_to": template_part.bill_to,
						"warehouse": template_part.warehouse,
						"color_code": template_part.color_code,
						"paint_type": template_part.paint_type,
						"description": template_part.description,
					})
			if template.sundry_items:
				for template_sundry in template.sundry_items:
					self.append("sundry_items", {
						"item": template_sundry.item,
						"item_name": template_sundry.item_name,
						"description": template_sundry.description,
						"qty": template_sundry.qty,
						"uom": template_sundry.uom,
						"rate": template_sundry.rate,
						"bill_type": template_sundry.bill_type,
						"bill_to": template_sundry.bill_to,
					})
			if template.service_inspections:
				for template_inspection in template.service_inspections:
					existing = [qi for qi in (self.quality_inspections or []) if qi.inspection_name == template_inspection.inspection_name]
					if not existing:
						self.append("quality_inspections", {
							"inspection_name": template_inspection.inspection_name,
							"status": "Pending",
						})

			self.calculate_child_table_amounts()
			self.calculate_totals()
			frappe.msgprint(_("Items fetched from Service Template {0}").format(frappe.bold(template_name)))
			if self.name:
				self.save(ignore_permissions=True)
			return {
				"service_items_count": len(self.service_items),
				"spareparts_count": len(self.spareparts),
				"sundry_items_count": len(self.sundry_items),
				"service_inspections_count": len([qi for qi in (self.quality_inspections or []) if qi.inspection_name]),
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

		# At least one line required
		has_lines = (self.service_items and len(self.service_items) > 0) or \
			(self.spareparts and len(self.spareparts) > 0) or \
			(self.sundry_items and len(self.sundry_items) > 0)
		if not has_lines:
			frappe.throw(_("Add at least one Service Item, Part, or Sundry Item before creating a Repair Order"))

		ro = frappe.new_doc("Repair Order")
		# Header - align with Repair Order fields
		ro.repair_estimate = self.name
		ro.repair_date = self.validity_date or today()
		ro.customer = self.customer
		ro.vehicle_unit = self.vehicle_unit
		ro.repair_type = self.repair_type
		ro.service_order_type = self.service_order_type
		ro.service_advisor = self.service_advisor
		ro.odometer = self.odometer
		ro.expected_completion_date = self.expected_completion_date
		ro.insurance_claim_no = self.insurance_claim_no
		ro.insurance_company = self.insurance_company
		ro.warranty = self.warranty
		ro.service_level_agreement = self.service_level_agreement
		ro.sla_notes = self.sla_notes
		ro.terms_and_conditions = self.terms_and_conditions
		if self.terms_and_conditions:
			ro.tc_notes = frappe.db.get_value("Terms and Conditions", self.terms_and_conditions, "terms")

		# Concerns
		for row in self.concerns or []:
			ro.append("concerns", {
				"customer_concern": row.customer_concern,
				"concern": row.concern,
				"description": row.description,
				"notes": row.notes,
			})
		# Diagnostics
		for row in self.diagnostics or []:
			ro.append("diagnostics", {
				"customer_concern": row.customer_concern,
				"concern": row.concern,
				"diagnostic": row.diagnostic,
				"notes": row.notes,
			})
		# Service Items
		for row in self.service_items or []:
			ro.append("service_items", {
				"service_item": row.service_item,
				"service_category": row.service_category,
				"description": row.description,
				"bill_type": row.bill_type,
				"bill_to": row.bill_to,
				"hours": row.hours,
				"rate": row.rate,
				"amount": row.amount,
			})
		# Parts
		for row in self.spareparts or []:
			ro.append("spareparts", {
				"item": row.item,
				"item_name": row.item_name,
				"item_type": row.item_type,
				"qty": row.qty,
				"uom": row.uom,
				"rate": row.rate,
				"amount": row.amount,
				"bill_type": row.bill_type,
				"bill_to": row.bill_to,
				"warehouse": row.warehouse,
				"color_code": row.get("color_code"),
				"paint_type": row.get("paint_type"),
				"description": row.description,
			})
		# Sundry Items
		for row in self.sundry_items or []:
			ro.append("sundry_items", {
				"item": row.item,
				"item_name": row.item_name,
				"description": row.description,
				"qty": row.qty,
				"uom": row.uom,
				"rate": row.rate,
				"amount": row.amount,
				"bill_type": row.bill_type,
				"bill_to": row.bill_to,
			})
		# Optional: Service Inspections
		for row in self.quality_inspections or []:
			ro.append("quality_inspections", {
				"inspection_name": row.inspection_name,
				"quality_inspection": row.quality_inspection,
				"status": row.status,
				"inspection_date": row.inspection_date,
				"inspected_by": row.inspected_by,
				"remarks": row.remarks,
			})
		# Optional: Photos
		for row in self.photos or []:
			ro.append("photos", {
				"photo_type": row.photo_type,
				"description": row.description,
				"image": row.image,
				"taken_date": row.taken_date,
				"taken_by": row.taken_by,
			})

		ro.insert()

		# Update estimate: status and link to RO
		frappe.db.set_value("Repair Estimate", self.name, "status", "Converted to RO")
		frappe.db.set_value("Repair Estimate", self.name, "repair_order", ro.name)
		frappe.db.commit()

		frappe.msgprint(_("Repair Order {0} created from estimate").format(frappe.bold(ro.name)))
		return ro.name


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
