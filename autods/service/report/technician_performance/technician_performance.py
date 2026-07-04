# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	return columns, data, None, chart


def get_chart(data):
	if not data:
		return None
	totals = {}
	for d in data:
		key = d.get("technician_name") or d.get("technician") or _("(Unknown)")
		row = totals.setdefault(key, {"completed": 0, "open_or_wip": 0})
		row["completed"] += int(d.get("completed") or 0)
		row["open_or_wip"] += int(d.get("open_or_wip") or 0)
	sorted_techs = sorted(
		totals.items(), key=lambda kv: kv[1]["completed"] + kv[1]["open_or_wip"], reverse=True
	)[:10]
	labels = [t[0] for t in sorted_techs]
	completed = [t[1]["completed"] for t in sorted_techs]
	open_or_wip = [t[1]["open_or_wip"] for t in sorted_techs]
	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Completed"), "values": completed},
				{"name": _("Open / WIP"), "values": open_or_wip},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
		"height": 300,
	}


def get_columns():
	return [
		{"fieldname": "technician", "label": _("Technician"), "fieldtype": "Link", "options": "Employee", "width": 140},
		{"fieldname": "technician_name", "label": _("Technician Name"), "fieldtype": "Data", "width": 160},
		{"fieldname": "work_area", "label": _("Work Area"), "fieldtype": "Link", "options": "Work Area", "width": 120},
		{"fieldname": "total_job_cards", "label": _("Total Job Cards"), "fieldtype": "Int", "width": 110},
		{"fieldname": "completed", "label": _("Completed"), "fieldtype": "Int", "width": 90},
		{"fieldname": "open_or_wip", "label": _("Open / WIP"), "fieldtype": "Int", "width": 100},
		{"fieldname": "total_hours", "label": _("Total Hours"), "fieldtype": "Float", "width": 100},
		{"fieldname": "avg_hours_per_card", "label": _("Avg Hours/Card"), "fieldtype": "Float", "width": 110},
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
	if filters.get("technician"):
		conditions.append("j.technician = %(technician)s")
		values["technician"] = filters["technician"]
	if filters.get("work_area"):
		conditions.append("j.work_area = %(work_area)s")
		values["work_area"] = filters["work_area"]
	if filters.get("status"):
		conditions.append("j.status = %(status)s")
		values["status"] = filters["status"]
	where = " and ".join(conditions)
	query = f"""
		select
			j.technician,
			e.employee_name as technician_name,
			j.work_area,
			count(*) as total_job_cards,
			sum(case when j.status = 'Completed' then 1 else 0 end) as completed,
			sum(case when j.status in ('Open', 'Work In Progress', 'On Hold') then 1 else 0 end) as open_or_wip,
			sum(ifnull(j.total_hours, 0)) as total_hours,
			round(sum(ifnull(j.total_hours, 0)) / nullif(count(*), 0), 2) as avg_hours_per_card
		from `tabJob Card` j
		left join `tabEmployee` e on e.name = j.technician
		where {where}
			and ifnull(j.technician, '') != ''
		group by j.technician, j.work_area
		order by total_job_cards desc, completed desc
	"""
	return frappe.db.sql(query, values, as_dict=1)
