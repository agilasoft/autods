# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PortalSyncLog(Document):
	@frappe.whitelist()
	def retry(self):
		from autods.principal_portal.sync import retry_log

		return retry_log(self.name)
