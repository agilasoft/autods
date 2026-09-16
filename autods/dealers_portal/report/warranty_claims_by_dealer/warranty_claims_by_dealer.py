# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "dealer", "label": _("Dealer"), "fieldtype": "Link", "options": "Dealer", "width": 160},
		{"fieldname": "claim_count", "label": _("Claims"), "fieldtype": "Int", "width": 90},
		{"fieldname": "open_count", "label": _("Open"), "fieldtype": "Int", "width": 90},
		{"fieldname": "approved_count", "label": _("Approved"), "fieldtype": "Int", "width": 100},
		{"fieldname": "rejected_count", "label": _("Rejected"), "fieldtype": "Int", "width": 100},
		{"fieldname": "claim_amount", "label": _("Amount"), "fieldtype": "Currency", "width": 120},
	]
	conditions = ["docstatus = 1"]
	values = {}
	if filters.get("from_date"):
		conditions.append("claim_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("claim_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("dealer"):
		conditions.append("dealer = %(dealer)s")
		values["dealer"] = filters["dealer"]
	query = (
		"""
		select
			dealer,
			count(name) as claim_count,
			sum(case when status in ('Submitted', 'Under Review') then 1 else 0 end) as open_count,
			sum(case when status in ('Approved', 'Settled') then 1 else 0 end) as approved_count,
			sum(case when status = 'Rejected' then 1 else 0 end) as rejected_count,
			sum(ifnull(claim_amount, 0)) as claim_amount
		from `tabWarranty Claim`
		where """
		+ " and ".join(conditions)
		+ """
		group by dealer
		order by claim_count desc
		"""
	)
	rows = frappe.db.sql(query, values, as_dict=1)
	for row in rows:
		row.claim_amount = flt(row.claim_amount)
	return columns, rows
