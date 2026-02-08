# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import datetime
import json

import frappe
from frappe.model.document import Document
from frappe.utils import get_time, getdate


class ShopFloorSchedule(Document):
	pass


@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Return events for calendar view. start/end are date strings."""
	from frappe.desk.calendar import get_event_conditions

	if filters and isinstance(filters, str):
		filters = json.loads(filters) if filters else []
	else:
		filters = filters or []
	conditions = get_event_conditions("ShopFloor Schedule", filters)

	start_date = getdate(start)
	end_date = getdate(end)

	schedules = frappe.db.sql(
		"""
		SELECT name, scheduled_date, scheduled_start_time, scheduled_end_time,
			work_area, plate_no, technician, status, job_card
		FROM `tabShopFloor Schedule`
		WHERE (scheduled_date BETWEEN %(start_date)s AND %(end_date)s)
		{conditions}
		ORDER BY scheduled_date, scheduled_start_time
		""".format(conditions=conditions),
		{"start_date": start_date, "end_date": end_date},
		as_dict=1,
	)

	events = []
	for d in schedules:
		dt_date = getdate(d.scheduled_date)
		start_time = get_time(d.scheduled_start_time or "00:00:00")
		end_time = get_time(d.scheduled_end_time or "23:59:59")
		start_dt = datetime.datetime.combine(dt_date, start_time)
		end_dt = datetime.datetime.combine(dt_date, end_time)
		title_parts = []
		if d.plate_no:
			title_parts.append(d.plate_no)
		if d.work_area:
			title_parts.append(d.work_area)
		if d.technician:
			technician_name = frappe.db.get_value("Employee", d.technician, "employee_name")
			if technician_name:
				title_parts.append(technician_name)
		title = " - ".join(title_parts) if title_parts else d.name
		events.append({
			"id": d.name,
			"name": d.name,
			"start": start_dt.isoformat(),
			"end": end_dt.isoformat(),
			"title": title,
			"status": d.status or "Scheduled",
			"allDay": 0,
		})
	return events
