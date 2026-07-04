# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

CHARGE_DOCTYPES = (
	"Repair Order Charges",
	"Repair Estimate Charges",
	"Service Template Charges",
)


def execute():
	"""Backfill qty from hours on Service charge rows where qty is empty."""
	for doctype in CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		if not frappe.db.has_table(doctype):
			continue
		_migrate_charge_table(doctype)
	frappe.db.commit()


def _migrate_charge_table(doctype: str):
	rows = frappe.db.sql(
		f"""
		select name, hours, qty, rate
		from `tab{doctype}`
		where service_item_type = 'Service'
			and ifnull(hours, 0) > 0
			and ifnull(qty, 0) = 0
		""",
		as_dict=True,
	)
	for row in rows:
		qty = flt(row.hours)
		amount = qty * flt(row.rate)
		frappe.db.set_value(
			doctype,
			row.name,
			{"qty": qty, "amount": amount},
			update_modified=False,
		)
