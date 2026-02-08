# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import json
import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_time, getdate, today


class ServiceAppointment(Document):
	def validate(self):
		self.validate_time_range()

	def validate_time_range(self):
		if not self.appointment_start_time or not self.appointment_end_time:
			return
		if get_time(self.appointment_end_time) <= get_time(self.appointment_start_time):
			frappe.throw(_("End Time must be after Start Time"))

	@frappe.whitelist()
	def create_repair_estimate(self):
		"""Create Repair Estimate from this appointment. Allowed when status is Scheduled/Confirmed/In Progress and no estimate yet."""
		allowed_statuses = ("Scheduled", "Confirmed", "In Progress")
		if self.status not in allowed_statuses:
			frappe.throw(_("Create Repair Estimate only when status is Scheduled, Confirmed, or In Progress"))
		if self.repair_estimate:
			frappe.throw(_("Repair Estimate already linked: {0}").format(self.repair_estimate))
		if not self.customer:
			frappe.throw(_("Customer is required to create Repair Estimate"))
		if not self.vehicle_unit:
			frappe.throw(_("Vehicle Unit is required to create Repair Estimate"))

		estimate = frappe.new_doc("Repair Estimate")
		estimate.service_appointment = self.name
		estimate.customer = self.customer
		estimate.vehicle_unit = self.vehicle_unit
		estimate.service_advisor = self.service_advisor
		estimate.service_order_type = self.service_order_type
		estimate.repair_type = self.repair_type
		estimate.estimate_date = today()
		estimate.status = "Draft"
		estimate.flags.ignore_mandatory = True
		estimate.insert()

		frappe.db.set_value("Service Appointment", self.name, "repair_estimate", estimate.name)
		frappe.db.commit()
		frappe.msgprint(_("Repair Estimate {0} created").format(frappe.bold(estimate.name)))
		return estimate.name

	@frappe.whitelist()
	def create_repair_order(self):
		"""Create Repair Order from this appointment. If repair_estimate exists and is Approved, create from estimate; else create blank RO from appointment header."""
		allowed_statuses = ("Scheduled", "Confirmed", "In Progress")
		if self.status not in allowed_statuses:
			frappe.throw(_("Create Repair Order only when status is Scheduled, Confirmed, or In Progress"))
		if self.repair_order:
			frappe.throw(_("Repair Order already linked: {0}").format(self.repair_order))
		if not self.customer:
			frappe.throw(_("Customer is required to create Repair Order"))
		if not self.vehicle_unit:
			frappe.throw(_("Vehicle Unit is required to create Repair Order"))

		ro_name = None
		if self.repair_estimate:
			est = frappe.get_doc("Repair Estimate", self.repair_estimate)
			if est.status == "Approved" and not est.repair_order:
				ro_name = est.create_repair_order()
				if frappe.db.has_column("Repair Order", "service_appointment"):
					frappe.db.set_value("Repair Order", ro_name, "service_appointment", self.name)
				frappe.db.set_value("Service Appointment", self.name, "repair_order", ro_name)
				frappe.db.commit()
				frappe.msgprint(_("Repair Order {0} created from estimate").format(frappe.bold(ro_name)))
				return ro_name

		ro = frappe.new_doc("Repair Order")
		ro.repair_date = today()
		ro.customer = self.customer
		ro.vehicle_unit = self.vehicle_unit
		ro.service_advisor = self.service_advisor
		ro.service_order_type = self.service_order_type
		ro.repair_type = self.repair_type
		ro.status = "Draft"
		if frappe.db.has_column("Repair Order", "service_appointment"):
			ro.service_appointment = self.name
		ro.insert()
		ro_name = ro.name

		frappe.db.set_value("Service Appointment", self.name, "repair_order", ro_name)
		frappe.db.commit()
		frappe.msgprint(_("Repair Order {0} created from appointment").format(frappe.bold(ro_name)))
		return ro_name


@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Return events for calendar view. start/end are date strings."""
	from frappe.desk.calendar import get_event_conditions

	if filters and isinstance(filters, str):
		filters = json.loads(filters) if filters else []
	else:
		filters = filters or []
	conditions = get_event_conditions("Service Appointment", filters)

	# Parse start/end to date for range (calendar may send datetime strings)
	start_date = getdate(start)
	end_date = getdate(end)

	appointments = frappe.db.sql(
		"""
		SELECT name, appointment_date, appointment_start_time, appointment_end_time,
			customer, plate_no, vehicle_unit, status, service_advisor, subject
		FROM `tabService Appointment`
		WHERE (appointment_date BETWEEN %(start_date)s AND %(end_date)s)
		AND docstatus < 2
		{conditions}
		ORDER BY appointment_date, appointment_start_time
		""".format(conditions=conditions),
		{"start_date": start_date, "end_date": end_date},
		as_dict=1,
	)

	events = []
	for d in appointments:
		dt_date = getdate(d.appointment_date)
		start_time = get_time(d.appointment_start_time or "00:00:00")
		end_time = get_time(d.appointment_end_time or "23:59:59")
		start_dt = datetime.datetime.combine(dt_date, start_time)
		end_dt = datetime.datetime.combine(dt_date, end_time)
		customer_name = frappe.db.get_value("Customer", d.customer, "customer_name") if d.customer else ""
		title = f"{customer_name or d.customer or 'N/A'}"
		if d.plate_no:
			title += f" - {d.plate_no}"
		if d.subject:
			title += f" ({d.subject[:30]}{'...' if len((d.subject or '')) > 30 else ''})"
		events.append({
			"id": d.name,
			"name": d.name,
			"start": start_dt.isoformat() if hasattr(start_dt, "isoformat") else str(start_dt),
			"end": end_dt.isoformat() if hasattr(end_dt, "isoformat") else str(end_dt),
			"title": title.strip(),
			"status": d.status or "Scheduled",
			"allDay": 0,
		})
	return events
