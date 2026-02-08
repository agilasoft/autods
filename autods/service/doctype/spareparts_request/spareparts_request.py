# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now, nowdate

try:
	import erpnext
except ImportError:
	erpnext = None


class SparepartsRequest(Document):
	def validate(self):
		if not self.requested_date:
			self.requested_date = now()
		if not self.requested_by:
			self.requested_by = frappe.session.user

	@frappe.whitelist()
	def make_material_request(self):
		"""Create Material Request (Material Issue) from this Spareparts Request for Stock module.
		Sets job_card and spareparts_request on the Material Request for proper referencing.
		"""
		if not self.items:
			frappe.throw(_("Please add items to the request"))

		material_request = create_material_request_from_spareparts_request(
			self, job_card=getattr(self, "job_card", None)
		)
		frappe.msgprint(_("Material Request {0} created for issue.").format(
			frappe.bold(material_request.name)
		))
		return {"doctype": material_request.doctype, "name": material_request.name}


def create_material_request_from_spareparts_request(spareparts_request, job_card=None):
	"""Create a Material Request (Material Issue) from a Spareparts Request with proper references."""
	material_request = frappe.new_doc("Material Request")
	material_request.material_request_type = "Material Issue"
	material_request.job_card = job_card or getattr(spareparts_request, "job_card", None)
	material_request.spareparts_request = spareparts_request.name
	material_request.schedule_date = getdate(nowdate())

	# Use company from item warehouses so MR company matches (avoid InvalidWarehouseCompany)
	company = None
	companies = set()
	for item in spareparts_request.items:
		wh = item.get("warehouse")
		if wh:
			wh_company = frappe.db.get_value("Warehouse", wh, "company")
			if wh_company:
				companies.add(wh_company)
				if company is None:
					company = wh_company
	if len(companies) > 1:
		frappe.throw(_("All item warehouses must belong to the same company. Found: {0}").format(", ".join(companies)))
	if not company:
		if erpnext:
			company = erpnext.get_default_company()
		else:
			company = frappe.db.get_single_value("Global Defaults", "default_company")
	if company:
		material_request.company = company

	for item in spareparts_request.items:
		uom = item.get("uom") or frappe.db.get_value("Item", item.item_code, "stock_uom")
		material_request.append("items", {
			"item_code": item.item_code,
			"qty": item.qty,
			"uom": uom,
			"warehouse": item.get("warehouse"),
			"schedule_date": material_request.schedule_date,
		})

	material_request.insert()
	return material_request
