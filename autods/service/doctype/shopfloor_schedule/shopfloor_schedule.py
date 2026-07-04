# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import datetime
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, get_time, getdate


class ShopFloorSchedule(Document):
	def validate(self):
		self.validate_time_range()
		self.validate_overlap_rules()
		self.validate_work_area_capacity()

	def on_submit(self):
		if self.status in (None, "", "Scheduled", "In Progress"):
			frappe.db.set_value("ShopFloor Schedule", self.name, "status", "Completed")
			self.status = "Completed"

	def on_cancel(self):
		frappe.db.set_value("ShopFloor Schedule", self.name, "status", "Cancelled")
		self.status = "Cancelled"

	def validate_time_range(self):
		start_dt, end_dt = schedule_window(self)
		if not start_dt or not end_dt:
			return
		if end_dt <= start_dt:
			frappe.throw(_("Scheduled End Time must be after Scheduled Start Time"))

	def validate_overlap_rules(self):
		if self.status in ("Completed", "Cancelled"):
			return
		settings = frappe.get_cached_doc("Service Settings")
		if getattr(settings, "allow_overlapping_schedules", None):
			return
		start_dt, end_dt = schedule_window(self)
		if not start_dt or not end_dt:
			return
		for row in overlapping_schedule_rows(self, start_dt, end_dt):
			if row.work_area == self.work_area:
				frappe.throw(
					_("ShopFloor Schedule {0} already uses Work Area {1} in this time slot.").format(
						frappe.bold(row.name),
						frappe.bold(self.work_area),
					),
				)
			if self.technician and row.technician == self.technician:
				frappe.throw(
					_("Technician {0} already has overlapping ShopFloor Schedule {1}.").format(
						frappe.bold(self.technician),
						frappe.bold(row.name),
					),
				)

	def validate_work_area_capacity(self):
		if self.status in ("Completed", "Cancelled"):
			return
		settings = frappe.get_cached_doc("Service Settings")
		if not getattr(settings, "respect_work_area_capacity", None):
			return
		if not self.work_area:
			return
		capacity = cint(frappe.db.get_value("Work Area", self.work_area, "capacity"))
		if not capacity:
			return
		start_dt, end_dt = schedule_window(self)
		if not start_dt or not end_dt:
			return
		vehicle_keys = {schedule_vehicle_key(self)}
		for row in overlapping_schedule_rows(self, start_dt, end_dt, work_area_only=True):
			vehicle_keys.add(schedule_vehicle_key(row))
		vehicle_keys.discard("")
		if len(vehicle_keys) > capacity:
			frappe.throw(
				_("Work Area {0} capacity is {1} vehicle(s); this time slot would schedule {2}.").format(
					frappe.bold(self.work_area),
					capacity,
					len(vehicle_keys),
				),
			)


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


def schedule_window(doc):
	if not (doc.scheduled_date and doc.scheduled_start_time and doc.scheduled_end_time):
		return None, None
	start_dt = get_datetime(f"{getdate(doc.scheduled_date)} {get_time(doc.scheduled_start_time)}")
	end_dt = get_datetime(f"{getdate(doc.scheduled_date)} {get_time(doc.scheduled_end_time)}")
	return start_dt, end_dt


def schedule_vehicle_key(doc):
	return (getattr(doc, "vehicle_unit", None) or getattr(doc, "plate_no", None) or getattr(doc, "job_card", None) or getattr(doc, "name", None) or "").strip()


def overlapping_schedule_rows(doc, start_dt, end_dt, work_area_only=False):
	filters = [
		["ShopFloor Schedule", "scheduled_date", "=", getdate(start_dt)],
		["ShopFloor Schedule", "status", "not in", ("Completed", "Cancelled")],
	]
	if doc.name:
		filters.append(["ShopFloor Schedule", "name", "!=", doc.name])
	if work_area_only:
		filters.append(["ShopFloor Schedule", "work_area", "=", doc.work_area])

	rows = frappe.get_all(
		"ShopFloor Schedule",
		filters=filters,
		fields=[
			"name",
			"scheduled_date",
			"scheduled_start_time",
			"scheduled_end_time",
			"work_area",
			"technician",
			"vehicle_unit",
			"plate_no",
			"job_card",
		],
		limit_page_length=200,
	)
	overlapping = []
	for row in rows:
		if not work_area_only and row.work_area != doc.work_area and row.technician != doc.technician:
			continue
		row_start, row_end = schedule_window(row)
		if row_start and row_end and start_dt < row_end and end_dt > row_start:
			overlapping.append(row)
	return overlapping
