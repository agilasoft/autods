# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.utils import get_combine_datetime


def get_expected_completion_datetime(service_appointment):
	"""Combine SA expected_completion_date and appointment_end_time into a system-timezone Datetime.

	The returned naive datetime is stored as shop-local wall clock (Frappe system timezone).
	Client forms display it without user-timezone conversion so it matches appointment_end_time.
	"""
	if not service_appointment:
		return None

	if isinstance(service_appointment, str):
		sa = frappe.get_cached_doc("Service Appointment", service_appointment)
	else:
		sa = service_appointment

	if not sa.expected_completion_date or not sa.appointment_end_time:
		return None

	return get_combine_datetime(sa.expected_completion_date, sa.appointment_end_time)
