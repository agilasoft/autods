# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from autods.principal_portal.permissions import apply_party_filters


def execute(filters=None):
	filters = filters or {}
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"fieldname": "name",
			"label": _("Claim"),
			"fieldtype": "Link",
			"options": "Warranty Claim",
			"width": 140,
		},
		{"fieldname": "claim_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{
			"fieldname": "principal",
			"label": _("Principal"),
			"fieldtype": "Link",
			"options": "Principal",
			"width": 130,
		},
		{"fieldname": "dealer", "label": _("Dealer"), "fieldtype": "Link", "options": "Dealer", "width": 130},
		{"fieldname": "vin", "label": _("VIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "claim_amount", "label": _("Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "sync_status", "label": _("Sync"), "fieldtype": "Data", "width": 90},
	]


def get_data(filters):
	query_filters = apply_party_filters({"docstatus": 1})
	if filters.get("status"):
		query_filters["status"] = filters["status"]
	if filters.get("principal"):
		query_filters["principal"] = filters["principal"]
	if filters.get("dealer"):
		query_filters["dealer"] = filters["dealer"]
	rows = frappe.get_all(
		"Warranty Claim",
		filters=query_filters,
		fields=["name", "claim_date", "principal", "dealer", "vin", "status", "claim_amount", "sync_status"],
		order_by="claim_date desc, modified desc",
	)
	if filters.get("from_date"):
		rows = [row for row in rows if str(row.claim_date) >= str(filters["from_date"])]
	if filters.get("to_date"):
		rows = [row for row in rows if str(row.claim_date) <= str(filters["to_date"])]
	return rows
