# Copyright (c) 2025, Agilasoft Technologies Inc.
# Migrate body_repair_order to repair_order for body repair doctypes (consolidation into Repair Order).

import frappe


def execute():
	"""Copy body_repair_order to repair_order for existing records after field rename."""
	doctypes_with_body_repair_order = [
		"Body Repair Job Card",
		"Body Repair Outsourcing",
		"Body Repair Spareparts Request",
		"Body Panel Transfer",
	]
	for doctype in doctypes_with_body_repair_order:
		table = "tab" + doctype.replace(" ", " ")
		try:
			# Only run if old column exists (upgrade from pre-consolidation; fresh install has only repair_order)
			result = frappe.db.sql("SHOW COLUMNS FROM `{}` LIKE 'body_repair_order'".format(table))
			if not result:
				continue
			frappe.db.sql("""
				UPDATE `{table}`
				SET repair_order = body_repair_order
				WHERE (repair_order IS NULL OR repair_order = '') AND body_repair_order IS NOT NULL AND body_repair_order != ''
			""".format(table=table))
			frappe.db.commit()
		except Exception as e:
			frappe.log_error(f"Patch migrate_body_repair_order_to_repair_order for {doctype}: {e}")
