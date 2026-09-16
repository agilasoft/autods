# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "dealer", "label": _("Dealer"), "fieldtype": "Link", "options": "Dealer", "width": 160},
		{"fieldname": "dealer_name", "label": _("Dealer Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "order_count", "label": _("Orders"), "fieldtype": "Int", "width": 90},
		{"fieldname": "open_count", "label": _("Open"), "fieldtype": "Int", "width": 90},
		{"fieldname": "delivered_count", "label": _("Delivered"), "fieldtype": "Int", "width": 100},
		{"fieldname": "net_total", "label": _("Net Total"), "fieldtype": "Currency", "width": 120},
	]
	conditions = ["docstatus = 1"]
	values = {}
	if filters.get("from_date"):
		conditions.append("order_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("order_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("dealer"):
		conditions.append("dealer = %(dealer)s")
		values["dealer"] = filters["dealer"]
	query = (
		"""
		select
			dealer,
			count(name) as order_count,
			sum(case when status in ('Submitted', 'Confirmed', 'Partially Delivered') then 1 else 0 end) as open_count,
			sum(case when status in ('Delivered', 'Closed') then 1 else 0 end) as delivered_count,
			sum(ifnull(net_total, 0)) as net_total
		from `tabPrincipal Order`
		where """
		+ " and ".join(conditions)
		+ """
		group by dealer
		order by order_count desc
		"""
	)
	rows = frappe.db.sql(query, values, as_dict=1)
	for row in rows:
		row.dealer_name = frappe.db.get_value("Dealer", row.dealer, "dealer_name") if row.dealer else ""
		row.net_total = flt(row.net_total)
	return columns, rows
