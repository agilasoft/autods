# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today

from autods.service.service_inspection_sync import link_service_inspection_to_repair_order


class ServiceInspection(Document):
	def validate(self):
		"""Validate inspection data"""
		# Auto-set inspection date if not set
		if not self.inspection_date:
			self.inspection_date = today()

		# Auto-set inspected_by to current user if not set
		if not self.inspected_by:
			self.inspected_by = frappe.session.user

		# Calculate overall result based on items if not manually set
		if not self.overall_result or self.overall_result == "Pending":
			self.calculate_overall_result()

	def after_insert(self):
		link_service_inspection_to_repair_order(self)

	def on_update(self):
		link_service_inspection_to_repair_order(self)
	
	def calculate_overall_result(self):
		"""Calculate overall result based on inspection items"""
		if not self.inspection_items:
			self.overall_result = "Pending"
			return
		
		passed = 0
		failed = 0
		pending = 0
		
		for item in self.inspection_items:
			if item.result == "Pass":
				passed += 1
			elif item.result == "Fail":
				failed += 1
			else:
				pending += 1
		
		if failed > 0:
			self.overall_result = "Fail"
		elif pending > 0:
			self.overall_result = "Pending"
		else:
			self.overall_result = "Pass"
	
	def on_submit(self):
		"""Update status when submitted"""
		self.status = "Completed"
		if not self.overall_result:
			self.calculate_overall_result()
	
	@frappe.whitelist()
	def load_from_template(self, template_name):
		"""Load inspection items from template"""
		if not template_name:
			frappe.throw(_("Template name is required"))
		
		try:
			template = frappe.get_doc("Service Inspection Template", template_name)
			
			# Clear existing items
			self.inspection_items = []
			
			# Load items from template
			for template_item in template.inspection_items or []:
				self.append("inspection_items", {
					"item_code": template_item.item_code,
					"item_name": template_item.item_name,
					"specification": template_item.specification,
					"expected_value": template_item.expected_value,
					"uom": template_item.uom,
					"is_mandatory": template_item.is_mandatory
				})
			
			frappe.msgprint(_("Inspection items loaded from template {0}").format(
				frappe.bold(template_name)
			))
			
		except frappe.DoesNotExistError:
			frappe.throw(_("Template {0} not found").format(
				frappe.bold(template_name)
			))
