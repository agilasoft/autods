# Copyright (c) 2026, Agilasoft Technologies Inc. and Contributors
# See license.txt

from datetime import datetime
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import add_days, getdate, today

from autods.service.service_appointment_utils import get_expected_completion_datetime


class TestRepairEstimate(UnitTestCase):
	def _make_customer(self):
		name = frappe.db.get_value("Customer", {}, "name")
		if name:
			return name
		doc = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "RE Test Customer",
				"customer_type": "Individual",
				"customer_group": "All Customer Groups",
				"territory": "All Territories",
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _make_vehicle_unit(self, customer):
		name = frappe.db.get_value("Vehicle Unit", {"customer": customer}, "name")
		if name:
			return name
		doc = frappe.get_doc(
			{
				"doctype": "Vehicle Unit",
				"customer": customer,
				"code": "RE-TEST-001",
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _make_service_appointment(self, customer, vehicle_unit):
		sa = frappe.get_doc(
			{
				"doctype": "Service Appointment",
				"customer": customer,
				"vehicle_unit": vehicle_unit,
				"appointment_date": today(),
				"appointment_start_time": "09:00:00",
				"appointment_end_time": "11:00:00",
				"expected_completion_date": add_days(today(), 2),
				"status": "Scheduled",
			}
		)
		sa.insert(ignore_permissions=True)
		return sa

	def _make_repair_estimate(self, customer, vehicle_unit, service_appointment=None):
		estimate = frappe.get_doc(
			{
				"doctype": "Repair Estimate",
				"customer": customer,
				"vehicle_unit": vehicle_unit,
				"estimate_date": today(),
				"service_appointment": service_appointment,
			}
		)
		estimate.flags.ignore_mandatory = True
		estimate.insert(ignore_permissions=True)
		return estimate

	def test_expected_completion_synced_from_service_appointment(self):
		customer = self._make_customer()
		vehicle_unit = self._make_vehicle_unit(customer)
		sa = self._make_service_appointment(customer, vehicle_unit)
		expected = get_expected_completion_datetime(sa)

		estimate = self._make_repair_estimate(customer, vehicle_unit, sa.name)
		self.assertEqual(getdate(estimate.expected_completion_date), getdate(expected))

	def test_manual_expected_completion_preserved_on_submit(self):
		customer = self._make_customer()
		vehicle_unit = self._make_vehicle_unit(customer)
		sa = self._make_service_appointment(customer, vehicle_unit)
		manual_dt = datetime(2026, 8, 15, 16, 30, 0)

		estimate = self._make_repair_estimate(customer, vehicle_unit, sa.name)
		estimate.expected_completion_date = manual_dt
		estimate.save(ignore_permissions=True)
		estimate.submit()

		stored = frappe.db.get_value("Repair Estimate", estimate.name, "expected_completion_date")
		self.assertEqual(frappe.utils.get_datetime(stored), manual_dt)

	@patch(
		"autods.service.doctype.repair_estimate.repair_estimate.get_expected_completion_datetime",
		return_value=None,
	)
	def test_manual_expected_completion_not_overwritten_on_validate(self, _mock_get):
		customer = self._make_customer()
		vehicle_unit = self._make_vehicle_unit(customer)
		sa = self._make_service_appointment(customer, vehicle_unit)
		manual_dt = datetime(2026, 9, 1, 10, 0, 0)

		estimate = frappe.new_doc("Repair Estimate")
		estimate.customer = customer
		estimate.vehicle_unit = vehicle_unit
		estimate.estimate_date = today()
		estimate.service_appointment = sa.name
		estimate.expected_completion_date = manual_dt
		estimate.set_expected_completion_from_appointment()

		self.assertEqual(frappe.utils.get_datetime(estimate.expected_completion_date), manual_dt)
