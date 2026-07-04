# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Shared vehicle schedule conflict checks for Service Appointment, Repair Order, and Job Card."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, getdate

try:
	from erpnext.stock.utils import get_combine_datetime
except ImportError:  # pragma: no cover - unit tests without ERPNext
	def get_combine_datetime(date_part, time_part):
		date_str = getdate(date_part).isoformat()
		if hasattr(time_part, "isoformat"):
			time_str = time_part.isoformat()
		else:
			time_str = str(time_part)
		if len(time_str.split(":")) == 2:
			time_str = f"{time_str}:00"
		return get_datetime(f"{date_str} {time_str}")


DEFAULT_SLOT_HOURS = 1
JOB_CARD_INACTIVE_STATUSES = ("Completed", "Cancelled")
SERVICE_APPOINTMENT_INACTIVE_STATUSES = ("Completed", "Cancelled", "No-show")
REPAIR_ORDER_INACTIVE_STATUSES = ("Completed", "Cancelled")


def intervals_overlap(a0, a1, b0, b1) -> bool:
	a0, a1 = get_datetime(a0), get_datetime(a1)
	b0, b1 = get_datetime(b0), get_datetime(b1)
	if a0 > a1:
		a0, a1 = a1, a0
	if b0 > b1:
		b0, b1 = b1, b0
	return a0 < b1 and a1 > b0


def same_schedule_start(start_a, start_b) -> bool:
	if not start_a or not start_b:
		return False
	return get_datetime(start_a) == get_datetime(start_b)


def schedules_conflict(start_a, end_a, start_b, end_b) -> bool:
	if same_schedule_start(start_a, start_b):
		return True
	if not start_a or not start_b:
		return True
	if not end_a or not end_b:
		return True
	return intervals_overlap(start_a, end_a, start_b, end_b)


def vehicle_identifiers(vehicle_unit=None, plate_no=None) -> tuple[set[str], set[str]]:
	units: set[str] = set()
	plates: set[str] = set()
	if vehicle_unit:
		units.add(vehicle_unit)
	if not plate_no and vehicle_unit:
		plate_no = frappe.db.get_value("Vehicle Unit", vehicle_unit, "plate_no")
	if plate_no:
		plates.add(str(plate_no).strip())
	return units, plates


def schedule_date_for_doc(repair_date=None, start_time=None):
	if repair_date:
		return getdate(repair_date)
	if start_time:
		return getdate(start_time)
	return None


def job_card_schedule_window(doc):
	if doc.start_time and doc.end_time:
		return get_datetime(doc.start_time), get_datetime(doc.end_time)
	if doc.start_time and doc.expected_completion_date:
		return get_datetime(doc.start_time), get_datetime(doc.expected_completion_date)
	if doc.start_time:
		start = get_datetime(doc.start_time)
		return start, add_to_date(start, hours=DEFAULT_SLOT_HOURS)
	if doc.repair_date and doc.expected_completion_date:
		return get_datetime(f"{getdate(doc.repair_date)} 00:00:00"), get_datetime(doc.expected_completion_date)
	if doc.repair_date:
		start = get_datetime(f"{getdate(doc.repair_date)} 09:00:00")
		return start, add_to_date(start, hours=DEFAULT_SLOT_HOURS)
	return None, None


def service_appointment_schedule_window(doc):
	if not doc.appointment_date:
		return None, None
	if doc.appointment_start_time and doc.appointment_end_time:
		start = get_combine_datetime(doc.appointment_date, doc.appointment_start_time)
		end_date = getdate(doc.expected_completion_date) if doc.expected_completion_date else doc.appointment_date
		end = get_combine_datetime(end_date, doc.appointment_end_time)
		return start, end
	if doc.appointment_start_time:
		start = get_combine_datetime(doc.appointment_date, doc.appointment_start_time)
		return start, add_to_date(start, hours=DEFAULT_SLOT_HOURS)
	return None, None


def repair_order_schedule_window(doc):
	if doc.repair_date and doc.expected_completion_date:
		start = get_datetime(f"{getdate(doc.repair_date)} 09:00:00")
		end = get_datetime(doc.expected_completion_date)
		if end <= start:
			end = add_to_date(start, hours=DEFAULT_SLOT_HOURS)
		return start, end
	if doc.repair_date:
		start = get_datetime(f"{getdate(doc.repair_date)} 09:00:00")
		return start, add_to_date(start, hours=DEFAULT_SLOT_HOURS)
	return None, None


def _vehicle_match_sql(vehicle_unit=None, plate_no=None) -> tuple[str, list]:
	units, plates = vehicle_identifiers(vehicle_unit, plate_no)
	clauses: list[str] = []
	params: list = []
	if units:
		clauses.append("vehicle_unit in %s")
		params.append(tuple(units))
	if plates:
		clauses.append("plate_no in %s")
		params.append(tuple(plates))
	if not clauses:
		return "", []
	return f"({' or '.join(clauses)})", params


def fetch_rows_for_vehicle(
	doctype: str,
	vehicle_unit=None,
	plate_no=None,
	schedule_date=None,
	exclude_name=None,
	inactive_statuses=(),
	fields=None,
	extra_conditions: list[str] | None = None,
):
	match_sql, match_params = _vehicle_match_sql(vehicle_unit, plate_no)
	if not match_sql:
		return []

	conditions = [match_sql, "status not in %s"]
	params = list(match_params) + [tuple(inactive_statuses or ("",))]
	if schedule_date:
		date_field = "repair_date" if doctype in ("Job Card", "Repair Order") else "appointment_date"
		conditions.append(f"{date_field} = %s")
		params.append(getdate(schedule_date))
	if exclude_name:
		conditions.append("name != %s")
		params.append(exclude_name)
	if extra_conditions:
		conditions.extend(extra_conditions)

	field_sql = ", ".join(fields or ["name"])
	query = f"""
		select {field_sql}
		from `tab{doctype}`
		where {" and ".join(conditions)}
	"""
	return frappe.db.sql(query, tuple(params), as_dict=True)


def validate_vehicle_job_card_conflict(doc):
	if doc.status in JOB_CARD_INACTIVE_STATUSES:
		return
	units, plates = vehicle_identifiers(doc.vehicle_unit, doc.plate_no)
	if not units and not plates:
		return

	on_date = schedule_date_for_doc(doc.repair_date, doc.start_time)
	if not on_date:
		return

	start_dt, end_dt = job_card_schedule_window(doc)
	existing = fetch_rows_for_vehicle(
		"Job Card",
		doc.vehicle_unit,
		doc.plate_no,
		on_date,
		exclude_name=doc.name,
		inactive_statuses=JOB_CARD_INACTIVE_STATUSES,
		fields=["name", "repair_date", "start_time", "end_time", "expected_completion_date"],
	)
	if not existing:
		return

	if not start_dt or not end_dt:
		frappe.throw(
			_("An active Job Card already exists for this vehicle on {0}: {1}").format(
				on_date,
				frappe.bold(existing[0].name),
			),
		)

	for row in existing:
		row_start, row_end = job_card_schedule_window(row)
		if schedules_conflict(start_dt, end_dt, row_start, row_end):
			frappe.throw(
				_("Job Card {0} already covers this vehicle in the selected repair window.").format(
					frappe.bold(row.name),
				),
			)


def validate_vehicle_service_appointment_conflict(doc):
	if doc.status in SERVICE_APPOINTMENT_INACTIVE_STATUSES:
		return
	units, plates = vehicle_identifiers(doc.vehicle_unit, doc.plate_no)
	if not units and not plates:
		return
	if not doc.appointment_date:
		return

	start_dt, end_dt = service_appointment_schedule_window(doc)
	existing = fetch_rows_for_vehicle(
		"Service Appointment",
		doc.vehicle_unit,
		doc.plate_no,
		doc.appointment_date,
		exclude_name=doc.name,
		inactive_statuses=SERVICE_APPOINTMENT_INACTIVE_STATUSES,
		fields=[
			"name",
			"appointment_date",
			"appointment_start_time",
			"appointment_end_time",
			"expected_completion_date",
		],
	)
	if not existing:
		return

	if not start_dt or not end_dt:
		frappe.throw(
			_("An active Service Appointment already exists for this vehicle on {0}: {1}").format(
				getdate(doc.appointment_date),
				frappe.bold(existing[0].name),
			),
		)

	for row in existing:
		row_start, row_end = service_appointment_schedule_window(row)
		if schedules_conflict(start_dt, end_dt, row_start, row_end):
			frappe.throw(
				_("Service Appointment {0} already covers this vehicle in the selected time slot.").format(
					frappe.bold(row.name),
				),
			)


def validate_vehicle_repair_order_conflict(doc):
	if doc.status in REPAIR_ORDER_INACTIVE_STATUSES:
		return
	if doc.docstatus == 2:
		return
	units, plates = vehicle_identifiers(doc.vehicle_unit, doc.plate_no)
	if not units and not plates:
		return
	if not doc.repair_date:
		return

	start_dt, end_dt = repair_order_schedule_window(doc)
	existing = fetch_rows_for_vehicle(
		"Repair Order",
		doc.vehicle_unit,
		doc.plate_no,
		doc.repair_date,
		exclude_name=doc.name,
		inactive_statuses=REPAIR_ORDER_INACTIVE_STATUSES,
		fields=["name", "repair_date", "expected_completion_date"],
		extra_conditions=["docstatus < 2"],
	)
	if not existing:
		return

	if not start_dt or not end_dt:
		frappe.throw(
			_("An active Repair Order already exists for this vehicle on {0}: {1}").format(
				getdate(doc.repair_date),
				frappe.bold(existing[0].name),
			),
		)

	for row in existing:
		row_start, row_end = repair_order_schedule_window(row)
		if schedules_conflict(start_dt, end_dt, row_start, row_end):
			frappe.throw(
				_("Repair Order {0} already covers this vehicle on the selected repair date.").format(
					frappe.bold(row.name),
				),
			)
