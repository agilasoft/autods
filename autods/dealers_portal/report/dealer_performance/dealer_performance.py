# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "dealer", "label": _("Dealer"), "fieldtype": "Link", "options": "Dealer", "width": 140},
		{"fieldname": "dealer_name", "label": _("Name"), "fieldtype": "Data", "width": 160},
		{"fieldname": "order_count", "label": _("Orders"), "fieldtype": "Int", "width": 90},
		{"fieldname": "fill_rate", "label": _("Fill Rate %"), "fieldtype": "Percent", "width": 110},
		{"fieldname": "claim_count", "label": _("Claims"), "fieldtype": "Int", "width": 90},
		{
			"fieldname": "avg_claim_tat",
			"label": _("Avg Claim TAT (days)"),
			"fieldtype": "Float",
			"width": 160,
		},
		{"fieldname": "claim_amount", "label": _("Claim Amount"), "fieldtype": "Currency", "width": 130},
	]
	dealer_filters = {}
	if filters.get("dealer"):
		dealer_filters["name"] = filters["dealer"]
	dealers = frappe.get_all("Dealer", filters=dealer_filters, fields=["name", "dealer_name"])
	data = []
	for dealer in dealers:
		orders = frappe.get_all(
			"Principal Order",
			filters={"dealer": dealer.name, "docstatus": 1},
			fields=["name", "status"],
		)
		delivered = [row for row in orders if row.status in ("Delivered", "Closed")]
		fill_rate = (len(delivered) / len(orders) * 100) if orders else 0
		claims = frappe.get_all(
			"Warranty Claim",
			filters={"dealer": dealer.name, "docstatus": 1},
			fields=["name", "claim_date", "modified", "status", "claim_amount"],
		)
		closed = [
			row for row in claims if row.status in ("Approved", "Rejected", "Settled") and row.claim_date
		]
		tat_days = []
		for row in closed:
			try:
				tat_days.append(max((row.modified.date() - row.claim_date).days, 0))
			except Exception:
				continue
		avg_tat = sum(tat_days) / len(tat_days) if tat_days else 0
		data.append(
			{
				"dealer": dealer.name,
				"dealer_name": dealer.dealer_name,
				"order_count": len(orders),
				"fill_rate": flt(fill_rate, 2),
				"claim_count": len(claims),
				"avg_claim_tat": flt(avg_tat, 2),
				"claim_amount": flt(sum(flt(row.claim_amount) for row in claims), 2),
			}
		)
	data.sort(key=lambda row: row["order_count"], reverse=True)
	return columns, data
