# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe

from autods.service.shop_status import LEGACY_STATUS_MAP


def execute():
	"""Move Repair Order off estimate statuses (Draft, Submitted, Approved, ...)."""
	if not frappe.db.table_exists("Repair Order"):
		return
	if not frappe.db.has_column("Repair Order", "status"):
		return
	for old, new in LEGACY_STATUS_MAP.items():
		frappe.db.sql(
			"UPDATE `tabRepair Order` SET status = %s WHERE status = %s",
			(new, old),
		)
