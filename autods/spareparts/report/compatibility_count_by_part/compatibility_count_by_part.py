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
		{"fieldname": "part", "label": _("Part"), "fieldtype": "Link", "options": "Item", "width": 140},
		{"fieldname": "part_name", "label": _("Part Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "compatibility_count", "label": _("Compatibility Records"), "fieldtype": "Int", "width": 140},
	]


def get_data(filters):
	conditions = []
	values = {}
	if filters.get("part"):
		conditions.append("p.part = %(part)s")
		values["part"] = filters["part"]
	where = " and ".join(conditions) if conditions else "1=1"
	query = (
		"select p.part, max(i.item_name) as part_name, count(*) as compatibility_count "
		"from `tabParts Compatibility` p left join `tabItem` i on i.name = p.part "
		"where " + where + " group by p.part order by compatibility_count desc"
	)
	return frappe.db.sql(query, values, as_dict=1)
