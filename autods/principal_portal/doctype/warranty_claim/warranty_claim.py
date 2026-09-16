# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from autods.principal_portal.utils import (
	get_default_principal,
	get_party_code,
	get_site_role,
	get_user_dealer,
	get_user_principal,
	is_system_manager,
	user_roles,
)


class WarrantyClaim(Document):
	def validate(self):
		self._apply_party_defaults()
		self._validate_parties()
		self._compute_totals()
		if self.docstatus == 0 and self.status not in ("Draft",):
			self.status = "Draft"

	def before_submit(self):
		if not (self.failure_description or "").strip() and not self.items:
			frappe.throw(_("Add a failure description or at least one claim item."))
		self.status = "Submitted"

	def on_submit(self):
		self._enqueue_sync("submit")

	def on_cancel(self):
		self.db_set("status", "Rejected")
		self._enqueue_sync("cancel")

	def on_update_after_submit(self):
		self._enqueue_sync("status")

	def _apply_party_defaults(self):
		site_role = get_site_role()
		roles = user_roles()
		if site_role == "Dealer":
			if not self.principal:
				self.principal = get_user_principal() or get_default_principal()
			if not self.dealer and get_party_code():
				self.dealer = frappe.db.get_value("Dealer", {"code": get_party_code()})
		elif site_role == "Principal":
			if "Dealer Portal User" in roles and not is_system_manager():
				mapped = get_user_dealer()
				if mapped:
					if self.dealer and self.dealer != mapped:
						frappe.throw(_("You cannot change the dealer on this claim."))
					self.dealer = mapped
			if not self.principal and get_party_code():
				self.principal = frappe.db.get_value("Principal", {"code": get_party_code()})

	def _validate_parties(self):
		site_role = get_site_role()
		if not self.principal:
			frappe.throw(_("Principal is required."))
		if site_role == "Principal" and not self.dealer:
			frappe.throw(_("Dealer is required on a principal site."))
		if self.principal:
			self.principal_code = frappe.db.get_value("Principal", self.principal, "code")
		if self.dealer:
			self.dealer_code = frappe.db.get_value("Dealer", self.dealer, "code")

	def _compute_totals(self):
		self.claim_amount = flt(sum(flt(r.amount) for r in (self.get("items") or [])), 2)

	def _enqueue_sync(self, event):
		from autods.principal_portal.sync import enqueue_sync

		enqueue_sync(self, event)

	@frappe.whitelist()
	def update_status(self, status):
		allowed = {
			"Submitted": ("Under Review", "Approved", "Rejected"),
			"Under Review": ("Approved", "Rejected"),
			"Approved": ("Settled", "Rejected"),
			"Rejected": (),
			"Settled": (),
		}
		if self.docstatus != 1:
			frappe.throw(_("Submit the claim before changing status."))
		if status not in allowed.get(self.status, ()):
			frappe.throw(_("Cannot change status from {0} to {1}.").format(self.status, status))
		if get_site_role() == "Dealer":
			frappe.throw(_("Only the principal site can review or settle warranty claims."))
		self.status = status
		self.save()
		return self.status


def _warranty_charge_rows(repair_order):
	rows = []
	if hasattr(repair_order, "_charge_rows"):
		try:
			return [
				line
				for line in repair_order._charge_rows()
				if (getattr(line, "bill_type", None) or "").strip() == "Warranty"
			]
		except Exception:
			pass
	for table in ("charges", "services", "spareparts", "overhead"):
		for line in repair_order.get(table) or []:
			if (getattr(line, "bill_type", None) or "").strip() == "Warranty":
				rows.append(line)
	return rows


@frappe.whitelist()
def create_warranty_claim_from_repair_order(repair_order):
	if not repair_order:
		frappe.throw(_("Repair Order is required."))
	ro = frappe.get_doc("Repair Order", repair_order)
	ro.check_permission("write")
	warranty_lines = _warranty_charge_rows(ro)
	if not warranty_lines:
		frappe.throw(_("No Repair Order lines have Bill To = Warranty."))

	existing = frappe.db.get_value("Warranty Claim", {"repair_order": ro.name, "docstatus": ["<", 2]})
	if existing:
		return {"doctype": "Warranty Claim", "name": existing}

	principal = get_user_principal() or get_default_principal()
	if not principal and getattr(ro, "warranty", None):
		principal = frappe.db.get_value("Principal", {"supplier": ro.warranty}) or frappe.db.get_value(
			"Principal", {"principal_name": ro.warranty}
		)

	if not principal:
		frappe.throw(_("Set Default Principal in Principal Dealer Settings, or map a Principal."))

	doc = frappe.new_doc("Warranty Claim")
	doc.principal = principal
	doc.repair_order = ro.name
	doc.vehicle_unit = getattr(ro, "vehicle_unit", None)
	doc.vin = getattr(ro, "vehicle_id_no", None)
	doc.chassis_number = getattr(ro, "vehicle_chassis_number", None)
	doc.odometer = getattr(ro, "odometer", None)
	doc.failure_description = getattr(ro, "service_description", None) or _("Warranty work from {0}").format(
		ro.name
	)
	for line in warranty_lines:
		doc.append(
			"items",
			{
				"item_code": getattr(line, "item", None) or "",
				"item_name": getattr(line, "item_name", None) or getattr(line, "description", None) or "",
				"description": getattr(line, "description", None) or "",
				"qty": flt(getattr(line, "qty", 1) or 1),
				"amount": flt(getattr(line, "amount", 0)),
			},
		)
	doc.insert()
	return {"doctype": doc.doctype, "name": doc.name}
