# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "name", "label": _("Supersession"), "fieldtype": "Link", "options": "Parts Supersession", "width": 140},
		{"fieldname": "original_part", "label": _("Original Part"), "fieldtype": "Link", "options": "Item", "width": 140},
		{"fieldname": "original_part_name", "label": _("Original Part Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "superseded_part", "label": _("Superseded Part"), "fieldtype": "Link", "options": "Item", "width": 140},
		{"fieldname": "superseded_part_name", "label": _("Superseded Part Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "supersession_type", "label": _("Type"), "fieldtype": "Data", "width": 120},
		{"fieldname": "effective_date", "label": _("Effective Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "end_date", "label": _("End Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "is_two_way", "label": _("Two-Way"), "fieldtype": "Check", "width": 80},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 90},
		{"fieldname": "supersession_reason", "label": _("Reason"), "fieldtype": "Data", "width": 200},
	]


def get_data(filters):
	conditions = []
	values = {}
	if filters.get("original_part"):
		conditions.append("p.original_part = %(original_part)s")
		values["original_part"] = filters["original_part"]
	if filters.get("superseded_part"):
		conditions.append("p.superseded_part = %(superseded_part)s")
		values["superseded_part"] = filters["superseded_part"]
	if filters.get("supersession_type"):
		conditions.append("p.supersession_type = %(supersession_type)s")
		values["supersession_type"] = filters["supersession_type"]
	if filters.get("status"):
		conditions.append("p.status = %(status)s")
		values["status"] = filters["status"]
	where = " and ".join(conditions) if conditions else "1=1"
	query = f"""
		select
			p.name,
			p.original_part,
			o.item_name as original_part_name,
			p.superseded_part,
			s.item_name as superseded_part_name,
			p.supersession_type,
			p.effective_date,
			p.end_date,
			p.is_two_way,
			p.status,
			left(p.supersession_reason, 200) as supersession_reason
		from `tabParts Supersession` p
		left join `tabItem` o on o.name = p.original_part
		left join `tabItem` s on s.name = p.superseded_part
		where {where}
		order by p.original_part, p.supersession_type, p.effective_date desc
	"""
	return frappe.db.sql(query, values, as_dict=1)
