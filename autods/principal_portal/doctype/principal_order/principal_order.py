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


class PrincipalOrder(Document):
	def validate(self):
		self._apply_party_defaults()
		self._validate_parties()
		self._compute_totals()
		if self.docstatus == 0 and self.status not in ("Draft", "Cancelled"):
			self.status = "Draft"

	def before_submit(self):
		if not self.items:
			frappe.throw(_("Add at least one item."))
		self.status = "Submitted"

	def on_submit(self):
		self._enqueue_sync("submit")

	def on_cancel(self):
		self.db_set("status", "Cancelled")
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
						frappe.throw(_("You cannot change the dealer on this order."))
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
		total = 0.0
		for row in self.get("items") or []:
			qty = flt(row.qty)
			if qty <= 0:
				frappe.throw(_("Qty must be greater than zero on row {0}.").format(row.idx))
			row.amount = flt(qty * flt(row.rate), 2)
			total += row.amount
		self.net_total = flt(total, 2)

	def _enqueue_sync(self, event):
		from autods.principal_portal.sync import enqueue_sync

		enqueue_sync(self, event)

	@frappe.whitelist()
	def update_status(self, status):
		allowed = {
			"Submitted": ("Confirmed", "Cancelled"),
			"Confirmed": ("Partially Delivered", "Delivered", "Closed", "Cancelled"),
			"Partially Delivered": ("Delivered", "Closed"),
			"Delivered": ("Closed",),
		}
		if self.docstatus != 1:
			frappe.throw(_("Submit the order before changing status."))
		current = self.status
		if status not in allowed.get(current, ()):
			frappe.throw(_("Cannot change status from {0} to {1}.").format(current, status))
		site_role = get_site_role()
		principal_actions = {"Confirmed", "Partially Delivered", "Delivered"}
		if status in principal_actions and site_role == "Dealer":
			frappe.throw(_("Only the principal site can confirm or deliver this order."))
		self.status = status
		self.save()
		return self.status
