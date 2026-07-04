# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Clear Repair Order service_type values that are not valid Service Type names (e.g. legacy Select values)."""
	if not frappe.db.has_table("Repair Order"):
		return
	if not frappe.db.has_table("Service Type"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabRepair Order` ro
		LEFT JOIN `tabService Type` st ON st.name = ro.service_type
		SET ro.service_type = NULL
		WHERE ro.service_type IS NOT NULL AND st.name IS NULL
		"""
	)
