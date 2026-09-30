# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "week", "label": _("Week"), "fieldtype": "Data", "width": 110},
		{
			"fieldname": "item_group",
			"label": _("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 140,
		},
		{"fieldname": "requested_qty", "label": _("Requested"), "fieldtype": "Float", "width": 110},
		{"fieldname": "issued_qty", "label": _("Issued"), "fieldtype": "Float", "width": 110},
		{"fieldname": "fill_rate", "label": _("Fill Rate %"), "fieldtype": "Percent", "width": 110},
	]
	data = get_data(filters)
	return columns, data, None, get_chart(data)


def get_data(filters):
	conditions = ["s.docstatus < 2", "s.status != 'Cancelled'"]
	values = {}
	if filters.get("from_date"):
		conditions.append("date(s.creation) >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("date(s.creation) <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	where = " and ".join(conditions)
	rows = frappe.db.sql(
		"""
		select date_format(s.creation, '%%x-W%%v') as week,
			ifnull(i.item_group, '') as item_group,
			sum(ifnull(si.qty, 0)) as requested_qty,
			sum(case when s.status = 'Issued' then ifnull(si.qty, 0) else 0 end) as issued_qty
		from `tabSpareparts Request` s
		inner join `tabSpareparts Request Item` si on si.parent = s.name
		left join `tabItem` i on i.name = si.item_code
		where """
		+ where
		+ """
		group by week, item_group
		order by week
		""",
		values,
		as_dict=True,
	)
	for row in rows:
		requested = flt(row.requested_qty)
		row.fill_rate = round(100 * flt(row.issued_qty) / requested, 1) if requested else 0
	return rows


def get_chart(data):
	if not data:
		return None
	weeks = []
	for row in data:
		if row.week not in weeks:
			weeks.append(row.week)
	requested, issued = [], []
	for week in weeks:
		requested.append(sum(flt(row.requested_qty) for row in data if row.week == week))
		issued.append(sum(flt(row.issued_qty) for row in data if row.week == week))
	return {
		"data": {
			"labels": weeks,
			"datasets": [
				{"name": _("Requested"), "values": requested},
				{"name": _("Issued"), "values": issued},
			],
		},
		"type": "bar",
		"height": 280,
	}
