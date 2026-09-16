# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class PortalConnection(Document):
	def validate(self):
		if self.site_url:
			self.site_url = self.site_url.strip().rstrip("/")
		if self.party_code:
			self.party_code = self.party_code.strip()

	@frappe.whitelist()
	def test_connection(self):
		from autods.principal_portal.sync import handshake

		try:
			result = handshake(self)
			remote_code = (result or {}).get("party_code") or ""
			if remote_code != self.party_code:
				frappe.throw(
					_("Handshake party code {0} does not match this connection's party code {1}.").format(
						remote_code, self.party_code
					)
				)
			self.db_set("last_handshake_at", now_datetime())
			self.db_set("last_error", "")
			frappe.msgprint(_("Connection successful. Remote site role: {0}").format(result.get("site_role")))
			return result
		except Exception as exc:
			self.db_set("last_error", str(exc)[:500])
			raise
