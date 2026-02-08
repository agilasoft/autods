# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now


class SparepartsRequest(Document):
	def validate(self):
		if not self.requested_date:
			self.requested_date = now()
		if not self.requested_by:
			self.requested_by = frappe.session.user
	
	def on_submit(self):
		"""Update status when submitted"""
		if self.status == "Draft":
			self.status = "Requested"
			self.save()
	
	@frappe.whitelist()
	def approve_request(self):
		"""Approve the spareparts request"""
		if self.status not in ["Requested", "Draft"]:
			frappe.throw(_("Only Draft or Requested requests can be approved"))
		
		self.status = "Approved"
		self.approved_by = frappe.session.user
		self.approved_date = now()
		self.save()
		frappe.msgprint(_("Spareparts Request {0} has been approved").format(
			frappe.bold(self.name)
		))
	
	@frappe.whitelist()
	def reject_request(self):
		"""Reject the spareparts request"""
		if self.status not in ["Requested", "Draft"]:
			frappe.throw(_("Only Draft or Requested requests can be rejected"))
		
		self.status = "Rejected"
		self.save()
		frappe.msgprint(_("Spareparts Request {0} has been rejected").format(
			frappe.bold(self.name)
		))
	
	@frappe.whitelist()
	def make_material_request(self):
		"""Create Material Request from Spareparts Request"""
		if not self.items:
			frappe.throw(_("Please add items to the request"))
		
		material_request = frappe.new_doc("Material Request")
		material_request.material_request_type = "Material Issue"
		material_request.spareparts_request = self.name
		
		for item in self.items:
			material_request.append("items", {
				"item_code": item.item_code,
				"qty": item.qty,
				"uom": item.uom,
				"warehouse": item.warehouse,
			})
		
		material_request.insert()
		
		frappe.msgprint(_("Material Request {0} created").format(
			frappe.bold(material_request.name)
		))
		
		# Return dict with doctype and name for JavaScript
		return {
			"doctype": material_request.doctype,
			"name": material_request.name
		}
