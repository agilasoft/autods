# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from autods.principal_portal.utils import get_site_role


class DealerCircular(Document):
	def validate(self):
		if self.audience == "Selected Dealers" and not self.get("recipients"):
			frappe.throw(_("Add at least one dealer when audience is Selected Dealers."))

	def before_save(self):
		self.flags.publish_now = False
		if self.published:
			previous = self.get_doc_before_save()
			if not previous or not previous.published:
				self.flags.publish_now = True
				if not self.published_on:
					self.published_on = now_datetime()

	def on_update(self):
		if (
			self.flags.publish_now
			and get_site_role() == "Principal"
			and not getattr(self.flags, "skip_circular_sync", False)
		):
			from autods.principal_portal.sync import enqueue_sync

			enqueue_sync(self, "circular")
