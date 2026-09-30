# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns = [
		{
			"fieldname": "original_part",
			"label": _("Original Part"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{"fieldname": "original_qty", "label": _("Original Qty"), "fieldtype": "Float", "width": 110},
		{
			"fieldname": "superseded_part",
			"label": _("Replacement"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{"fieldname": "replacement_qty", "label": _("Replacement Qty"), "fieldtype": "Float", "width": 130},
		{"fieldname": "supersession_type", "label": _("Type"), "fieldtype": "Data", "width": 140},
	]
	rows = frappe.db.sql(
		"""
		select ps.original_part, ps.superseded_part, ps.supersession_type
		from `tabParts Supersession` ps
		where ps.status = 'Active'
			and (ps.effective_date is null or ps.effective_date <= curdate())
			and (ps.end_date is null or ps.end_date = '0000-00-00' or ps.end_date >= curdate())
		""",
		as_dict=True,
	)
	if not rows or not frappe.db.table_exists("Bin"):
		return columns, []
	codes = list({row.original_part for row in rows} | {row.superseded_part for row in rows})
	bins = {
		row.item_code: flt(row.qty)
		for row in frappe.db.sql(
			"select item_code, sum(actual_qty) as qty from `tabBin` where item_code in %(codes)s group by item_code",
			{"codes": codes},
			as_dict=True,
		)
	}
	data = []
	for row in rows:
		original_qty = bins.get(row.original_part, 0)
		replacement_qty = bins.get(row.superseded_part, 0)
		if original_qty <= 0 and replacement_qty > 0:
			row.original_qty = original_qty
			row.replacement_qty = replacement_qty
			data.append(row)
	return columns, data
