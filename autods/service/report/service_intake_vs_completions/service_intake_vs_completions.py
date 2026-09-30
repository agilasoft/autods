# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "week", "label": _("Week"), "fieldtype": "Data", "width": 110},
		{"fieldname": "intake", "label": _("Intake"), "fieldtype": "Int", "width": 90},
		{"fieldname": "completions", "label": _("Completions"), "fieldtype": "Int", "width": 110},
	]
	data = get_data(filters)
	return columns, data, None, get_chart(data)


def get_data(filters):
	values = {}
	intake_cond = ["docstatus < 2"]
	done_cond = ["docstatus < 2", "status = 'Completed'", "actual_completion_date is not null"]
	if filters.get("from_date"):
		intake_cond.append("repair_date >= %(from_date)s")
		done_cond.append("date(actual_completion_date) >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		intake_cond.append("repair_date <= %(to_date)s")
		done_cond.append("date(actual_completion_date) <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	intake = frappe.db.sql(
		"""
		select date_format(repair_date, '%%x-W%%v') as week, count(*) as intake
		from `tabRepair Order`
		where """
		+ " and ".join(intake_cond)
		+ " group by week",
		values,
		as_dict=True,
	)
	done = frappe.db.sql(
		"""
		select date_format(actual_completion_date, '%%x-W%%v') as week, count(distinct repair_order) as completions
		from `tabJob Card`
		where """
		+ " and ".join(done_cond)
		+ " group by week",
		values,
		as_dict=True,
	)
	weeks = {}
	for row in intake:
		weeks.setdefault(row.week, {"week": row.week, "intake": 0, "completions": 0})
		weeks[row.week]["intake"] = row.intake
	for row in done:
		weeks.setdefault(row.week, {"week": row.week, "intake": 0, "completions": 0})
		weeks[row.week]["completions"] = row.completions
	return [weeks[key] for key in sorted(weeks)]


def get_chart(data):
	if not data:
		return None
	return {
		"data": {
			"labels": [row["week"] for row in data],
			"datasets": [
				{"name": _("Intake"), "values": [row["intake"] for row in data]},
				{"name": _("Completions"), "values": [row["completions"] for row in data]},
			],
		},
		"type": "bar",
		"height": 280,
	}
