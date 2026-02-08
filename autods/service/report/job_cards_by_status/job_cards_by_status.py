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
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 140},
		{"fieldname": "work_area", "label": _("Work Area"), "fieldtype": "Link", "options": "Work Area", "width": 120},
		{"fieldname": "job_count", "label": _("Job Cards"), "fieldtype": "Int", "width": 100},
	]


def get_data(filters):
	conditions = ["j.docstatus >= 0"]
	values = {}
	if filters.get("from_date"):
		conditions.append("j.repair_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("j.repair_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("work_area"):
		conditions.append("j.work_area = %(work_area)s")
		values["work_area"] = filters["work_area"]
	if filters.get("status"):
		conditions.append("j.status = %(status)s")
		values["status"] = filters["status"]
	where = " and ".join(conditions)
	query = f"""
		select
			j.status,
			j.work_area,
			count(*) as job_count
		from `tabJob Card` j
		where {where}
		group by j.status, j.work_area
		order by j.status, j.work_area
	"""
	return frappe.db.sql(query, values, as_dict=1)
