# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Case chips for the advisor dashboard: promise, parts, invoice."""

import frappe
from frappe.utils import get_datetime, now_datetime

OPEN_REQUEST_STATUSES = ("Draft", "Requested", "Approved")


@frappe.whitelist()
def get_case_chips(repair_order):
	if not repair_order or not frappe.db.exists("Repair Order", repair_order):
		return {"promise": "none", "parts": "none", "invoice": "none"}
	return {
		"promise": _promise_chip(repair_order),
		"parts": _parts_chip(repair_order),
		"invoice": _invoice_chip(repair_order),
	}


def _promise_chip(repair_order):
	expected, status = frappe.db.get_value(
		"Repair Order", repair_order, ["expected_completion_date", "status"]
	)
	if not expected:
		return "none"
	expected_dt = get_datetime(expected)
	if status == "Completed":
		actual = frappe.db.sql(
			"""
			SELECT MAX(actual_completion_date)
			FROM `tabJob Card`
			WHERE repair_order = %s AND docstatus < 2 AND actual_completion_date IS NOT NULL
			""",
			repair_order,
		)[0][0]
		if not actual:
			return "on_time"
		return "on_time" if get_datetime(actual) <= expected_dt else "overdue"
	if status == "Cancelled":
		return "none"
	return "on_time" if now_datetime() <= expected_dt else "overdue"


def _parts_chip(repair_order):
	charge_count = frappe.db.count(
		"Repair Order Charges",
		{"parent": repair_order, "parenttype": "Repair Order", "service_item_type": "Spareparts"},
	)
	if not charge_count:
		return "none"
	open_requests = frappe.db.sql(
		"""
		SELECT COUNT(*)
		FROM `tabSpareparts Request`
		WHERE repair_order = %s AND docstatus < 2
			AND status IN %(statuses)s
		""",
		{"repair_order": repair_order, "statuses": OPEN_REQUEST_STATUSES},
	)[0][0]
	if open_requests:
		return "short"
	issued = frappe.db.count(
		"Spareparts Request",
		{"repair_order": repair_order, "docstatus": ["<", 2], "status": "Issued"},
	)
	if issued:
		return "ready"
	return "short"


def _invoice_chip(repair_order):
	if not frappe.db.has_column("Sales Invoice", "repair_order"):
		return "not_billed"
	rows = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(grand_total), 0), COALESCE(SUM(outstanding_amount), 0), COUNT(*)
		FROM `tabSales Invoice`
		WHERE docstatus = 1 AND repair_order = %s
		""",
		repair_order,
	)[0]
	count = rows[2] or 0
	if not count:
		return "not_billed"
	outstanding = rows[1] or 0
	if outstanding <= 0:
		return "billed"
	return "partial"
