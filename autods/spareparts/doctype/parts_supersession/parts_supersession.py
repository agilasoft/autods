# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from autods.spareparts.supersession import approval_required


class PartsSupersession(Document):
	def validate(self):
		if self.original_part and self.original_part == self.superseded_part:
			frappe.throw(_("Original Part and Superseded Part must be different."))
		if self.effective_date and self.end_date and getdate(self.end_date) < getdate(self.effective_date):
			frappe.throw(_("End Date cannot be before Effective Date."))
		if approval_required() and self.status == "Active" and not self.get("approved"):
			frappe.throw(_("Supersession approval is required before status can be Active."))
