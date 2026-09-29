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
			"label": _("Order"),
			"fieldtype": "Link",
			"options": "Principal Order",
			"width": 140,
		},
		{"fieldname": "order_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "order_type", "label": _("Type"), "fieldtype": "Data", "width": 100},
		{
			"fieldname": "principal",
			"label": _("Principal"),
			"fieldtype": "Link",
			"options": "Principal",
			"width": 130,
		},
		{"fieldname": "dealer", "label": _("Dealer"), "fieldtype": "Link", "options": "Dealer", "width": 130},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 140},
		{"fieldname": "net_total", "label": _("Net Total"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "sync_status", "label": _("Sync"), "fieldtype": "Data", "width": 90},
	]


def get_data(filters):
	query_filters = apply_party_filters({"docstatus": 1})
	if filters.get("from_date"):
		query_filters["order_date"] = [">=", filters["from_date"]]
	orders = frappe.get_all(
		"Principal Order",
		filters=query_filters,
		fields=[
			"name",
			"order_date",
			"order_type",
			"principal",
			"dealer",
			"status",
			"net_total",
			"sync_status",
		],
		order_by="order_date desc, modified desc",
	)
	if filters.get("to_date"):
		orders = [row for row in orders if str(row.order_date) <= str(filters["to_date"])]
	if filters.get("status"):
		orders = [row for row in orders if row.status == filters["status"]]
	if filters.get("principal"):
		orders = [row for row in orders if row.principal == filters["principal"]]
	if filters.get("dealer"):
		orders = [row for row in orders if row.dealer == filters["dealer"]]
	return orders
