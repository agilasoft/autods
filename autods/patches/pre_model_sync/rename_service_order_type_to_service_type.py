# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Rename DocType and DB columns before schema sync so data is preserved."""
	if frappe.db.exists("DocType", "Service Order Type") and not frappe.db.exists("DocType", "Service Type"):
		frappe.rename_doc("DocType", "Service Order Type", "Service Type", force=True)

	# DDL must not run in a transaction with pending writes (ImplicitCommitError).
	frappe.db.commit()
	_rename_header_link_columns()
	_rename_child_service_category_columns()
	_rename_repair_concern_order_type_column()


def _table_columns(doctype):
	if not frappe.db.has_table(doctype):
		return []
	try:
		return frappe.db.get_table_columns(doctype) or []
	except Exception:
		return []


def _rename_header_link_columns():
	for dt in ("Repair Estimate", "Service Appointment"):
		cols = _table_columns(dt)
		if not cols:
			continue
		table = f"tab{dt}"
		if "service_order_type" in cols and "service_type" not in cols:
			frappe.db.sql(f"ALTER TABLE `{table}` CHANGE COLUMN `service_order_type` `service_type` VARCHAR(140)")
			frappe.db.commit()
		elif "service_order_type" in cols and "service_type" in cols:
			frappe.db.sql(
				f"UPDATE `{table}` SET `service_type` = COALESCE(NULLIF(`service_type`, ''), `service_order_type`)"
			)
			frappe.db.commit()
			frappe.db.sql(f"ALTER TABLE `{table}` DROP COLUMN `service_order_type`")
			frappe.db.commit()


def _rename_child_service_category_columns():
	for dt in (
		"Repair Estimate Services",
		"Repair Estimate Service Items",
		"Repair Order Services",
		"Repair Order Service Items",
		"Service Template Service Items",
	):
		cols = _table_columns(dt)
		if not cols:
			continue
		table = f"tab{dt}"
		if "service_category" in cols and "service_type" not in cols:
			frappe.db.sql(f"ALTER TABLE `{table}` CHANGE COLUMN `service_category` `service_type` VARCHAR(140)")
			frappe.db.commit()
		elif "service_category" in cols and "service_type" in cols:
			frappe.db.sql(
				f"UPDATE `{table}` SET `service_type` = COALESCE(NULLIF(`service_type`, ''), `service_category`)"
			)
			frappe.db.commit()
			frappe.db.sql(f"ALTER TABLE `{table}` DROP COLUMN `service_category`")
			frappe.db.commit()


def _rename_repair_concern_order_type_column():
	dt = "Repair Concern Order Type"
	cols = _table_columns(dt)
	if not cols:
		return
	table = f"tab{dt}"
	if "service_order_type" in cols and "service_type" not in cols:
		frappe.db.sql(f"ALTER TABLE `{table}` CHANGE COLUMN `service_order_type` `service_type` VARCHAR(140)")
		frappe.db.commit()
	elif "service_order_type" in cols and "service_type" in cols:
		frappe.db.sql(
			f"UPDATE `{table}` SET `service_type` = COALESCE(NULLIF(`service_type`, ''), `service_order_type`)"
		)
		frappe.db.commit()
		frappe.db.sql(f"ALTER TABLE `{table}` DROP COLUMN `service_order_type`")
		frappe.db.commit()
