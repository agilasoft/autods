# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe

CHARGE_DOCTYPES = (
	"Repair Order Charges",
	"Repair Estimate Charges",
	"Service Template Charges",
)


def execute():
	"""Rename hours column to standard_hours before charge child DocTypes sync."""
	for doctype in CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		if not frappe.db.has_table(doctype):
			continue
		_rename_hours_column(doctype)
	frappe.db.commit()


def _rename_hours_column(doctype: str):
	table = f"tab{doctype}"
	columns = {row["Field"] for row in frappe.db.sql(f"SHOW COLUMNS FROM `{table}`", as_dict=True)}
	if "hours" in columns and "standard_hours" not in columns:
		frappe.db.sql_ddl(
			f"ALTER TABLE `{table}` CHANGE `hours` `standard_hours` decimal(21,9) NOT NULL DEFAULT 0.000000000"
		)
