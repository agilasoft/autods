# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from autods.principal_portal.utils import get_site_role


class PrincipalDealerSettings(Document):
	def validate(self):
		if self.site_role != "Dealer":
			self.default_principal = None
		if self.max_sync_retries is None or int(self.max_sync_retries) < 1:
			self.max_sync_retries = 5


def get_effective_site_role(settings=None):
	if settings:
		return settings.site_role
	return get_site_role()
