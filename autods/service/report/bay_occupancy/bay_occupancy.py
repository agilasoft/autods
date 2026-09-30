# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, time_diff_in_hours


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "scheduled_date", "label": _("Date"), "fieldtype": "Date", "width": 110},
		{
			"fieldname": "work_area",
			"label": _("Work Area"),
			"fieldtype": "Link",
			"options": "Work Area",
			"width": 140,
		},
		{"fieldname": "scheduled_hours", "label": _("Scheduled Hours"), "fieldtype": "Float", "width": 130},
		{"fieldname": "available_hours", "label": _("Available Hours"), "fieldtype": "Float", "width": 130},
		{"fieldname": "occupancy", "label": _("Occupancy %"), "fieldtype": "Percent", "width": 110},
	]
	data = get_data(filters)
	return columns, data, None, get_chart(data)


def shop_hours():
	opens = "08:00:00"
	closes = "17:00:00"
	if frappe.db.exists("DocType", "Service Settings"):
		opens = frappe.db.get_single_value("Service Settings", "planning_shop_opens") or opens
		closes = frappe.db.get_single_value("Service Settings", "planning_shop_closes") or closes
	hours = time_diff_in_hours(str(closes), str(opens))
	return hours if hours and hours > 0 else 8


def get_data(filters):
	conditions = ["s.docstatus < 2", "s.status != 'Cancelled'"]
	values = {}
	if filters.get("from_date"):
		conditions.append("s.scheduled_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("s.scheduled_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	rows = frappe.db.sql(
		"""
		select s.scheduled_date, s.work_area, s.scheduled_start_time, s.scheduled_end_time,
			ifnull(w.capacity, 1) as capacity
		from `tabShopFloor Schedule` s
		left join `tabWork Area` w on w.name = s.work_area
		where {where}
		""".format(where=" and ".join(conditions)),
		values,
		as_dict=True,
	)
	day_hours = shop_hours()
	grouped = {}
	for row in rows:
		start = row.scheduled_start_time
		end = row.scheduled_end_time
		hours = 0
		if start and end:
			hours = time_diff_in_hours(str(end), str(start)) or 0
			if hours < 0:
				hours = 0
		key = (str(getdate(row.scheduled_date)) if row.scheduled_date else "", row.work_area)
		bucket = grouped.setdefault(key, {"scheduled_hours": 0, "capacity": flt(row.capacity) or 1})
		bucket["scheduled_hours"] += hours
		bucket["capacity"] = max(bucket["capacity"], flt(row.capacity) or 1)
	data = []
	for (day, work_area), bucket in sorted(grouped.items()):
		available = (bucket["capacity"] or 1) * day_hours
		occupancy = round(100 * bucket["scheduled_hours"] / available, 1) if available else 0
		data.append(
			{
				"scheduled_date": day,
				"work_area": work_area,
				"scheduled_hours": round(bucket["scheduled_hours"], 2),
				"available_hours": round(available, 2),
				"occupancy": occupancy,
			}
		)
	return data


def get_chart(data):
	if not data:
		return None
	by_area = {}
	for row in data:
		area = row["work_area"] or _("Unassigned")
		bucket = by_area.setdefault(area, {"scheduled": 0, "available": 0})
		bucket["scheduled"] += row["scheduled_hours"]
		bucket["available"] += row["available_hours"]
	labels = list(by_area)
	values = [
		round(100 * by_area[label]["scheduled"] / by_area[label]["available"], 1)
		if by_area[label]["available"]
		else 0
		for label in labels
	]
	return {
		"data": {"labels": labels, "datasets": [{"name": _("Occupancy %"), "values": values}]},
		"type": "bar",
		"height": 280,
	}
