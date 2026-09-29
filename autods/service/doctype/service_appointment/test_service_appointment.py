# Copyright (c) 2026, Agilasoft Technologies Inc. and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import add_days, today

from autods.service.doctype.service_appointment.service_appointment import ServiceAppointment


class TestServiceAppointment(UnitTestCase):
	def test_on_submit_uses_db_set_for_status(self):
		doc = MagicMock()
		doc.status = "Scheduled"
		ServiceAppointment.on_submit(doc)
		doc.db_set.assert_called_once_with("status", "Confirmed")

	def test_on_submit_skips_db_set_when_not_scheduled(self):
		doc = MagicMock()
		doc.status = "Confirmed"
		ServiceAppointment.on_submit(doc)
		doc.db_set.assert_not_called()

	def test_on_cancel_uses_db_set_for_status(self):
		doc = MagicMock()
		ServiceAppointment.on_cancel(doc)
		doc.db_set.assert_called_once_with("status", "Cancelled")

	def test_create_repair_estimate_links_with_db_set(self):
		doc = MagicMock()
		doc.docstatus = 1
		doc.status = "Confirmed"
		doc.repair_estimate = None
		doc.customer = "CUST-1"
		doc.vehicle_unit = "VU-1"
		doc.name = "SA-TEST-CREATE-RE"
		doc.service_advisor = None
		doc.service_type = None
		doc.repair_type = None

		mock_estimate = MagicMock()
		mock_estimate.name = "RE-TEST-001"

		with (
			patch(
				"autods.service.doctype.service_appointment.service_appointment.frappe.new_doc",
				return_value=mock_estimate,
			),
			patch(
				"autods.service.doctype.service_appointment.service_appointment.get_expected_completion_datetime",
				return_value=add_days(today(), 2),
			),
			patch("autods.service.doctype.service_appointment.service_appointment.frappe.msgprint"),
			patch(
				"autods.service.doctype.service_appointment.service_appointment.frappe.defaults.get_user_default",
				return_value=None,
			),
		):
			result = ServiceAppointment.create_repair_estimate(doc)

		self.assertEqual(result, "RE-TEST-001")
		doc.db_set.assert_called_once_with("repair_estimate", "RE-TEST-001")

	def test_create_repair_estimate_does_not_populate_charges(self):
		"""SA → RE convert must leave charges empty (no template load)."""
		doc = MagicMock()
		doc.docstatus = 1
		doc.status = "Confirmed"
		doc.repair_estimate = None
		doc.customer = "CUST-1"
		doc.vehicle_unit = "VU-1"
		doc.name = "SA-TEST-RE-NO-CHARGES"
		doc.service_advisor = None
		doc.service_type = None
		doc.repair_type = None

		mock_estimate = MagicMock()
		mock_estimate.name = "RE-TEST-EMPTY"
		mock_estimate.append = MagicMock()
		mock_estimate.fetch_template_items = MagicMock()

		with (
			patch(
				"autods.service.doctype.service_appointment.service_appointment.frappe.new_doc",
				return_value=mock_estimate,
			),
			patch(
				"autods.service.doctype.service_appointment.service_appointment.get_expected_completion_datetime",
				return_value=add_days(today(), 2),
			),
			patch("autods.service.doctype.service_appointment.service_appointment.frappe.msgprint"),
			patch(
				"autods.service.doctype.service_appointment.service_appointment.frappe.defaults.get_user_default",
				return_value=None,
			),
		):
			ServiceAppointment.create_repair_estimate(doc)

		mock_estimate.insert.assert_called_once()
		mock_estimate.append.assert_not_called()
		mock_estimate.fetch_template_items.assert_not_called()

	def test_create_repair_order_uses_appointment_date_not_today(self):
		appointment_date = add_days(today(), 7)
		doc = MagicMock()
		doc.docstatus = 1
		doc.status = "Confirmed"
		doc.repair_order = None
		doc.repair_estimate = None
		doc.customer = "CUST-1"
		doc.vehicle_unit = "VU-1"
		doc.name = "SA-TEST-CREATE-RO"
		doc.appointment_date = appointment_date
		doc.service_advisor = None
		doc.service_type = None
		doc.repair_type = None

		mock_ro = MagicMock()
		mock_ro.name = "RO-TEST-001"

		with (
			patch(
				"autods.service.doctype.service_appointment.service_appointment.frappe.new_doc",
				return_value=mock_ro,
			),
			patch(
				"autods.service.doctype.service_appointment.service_appointment.get_expected_completion_datetime",
				return_value=add_days(appointment_date, 1),
			),
			patch("autods.service.doctype.service_appointment.service_appointment.frappe.msgprint"),
			patch(
				"autods.service.doctype.service_appointment.service_appointment.frappe.db.has_column",
				return_value=True,
			),
		):
			result = ServiceAppointment.create_repair_order(doc)

		self.assertEqual(result, "RO-TEST-001")
		self.assertEqual(mock_ro.repair_date, appointment_date)
		self.assertNotEqual(mock_ro.repair_date, today())
		doc.db_set.assert_called_once_with("repair_order", "RO-TEST-001")

	def test_create_repair_order_blank_does_not_populate_charges(self):
		"""SA → blank RO convert must leave charges empty (no template load)."""
		doc = MagicMock()
		doc.docstatus = 1
		doc.status = "Confirmed"
		doc.repair_order = None
		doc.repair_estimate = None
		doc.customer = "CUST-1"
		doc.vehicle_unit = "VU-1"
		doc.name = "SA-TEST-RO-NO-CHARGES"
		doc.appointment_date = today()
		doc.service_advisor = None
		doc.service_type = None
		doc.repair_type = None

		mock_ro = MagicMock()
		mock_ro.name = "RO-TEST-EMPTY"
		mock_ro.append = MagicMock()
		mock_ro.fetch_template_items = MagicMock()
		mock_ro.meta = MagicMock()
		mock_ro.meta.get_field = MagicMock(return_value=True)

		with (
			patch(
				"autods.service.doctype.service_appointment.service_appointment.frappe.new_doc",
				return_value=mock_ro,
			),
			patch(
				"autods.service.doctype.service_appointment.service_appointment.get_expected_completion_datetime",
				return_value=add_days(today(), 1),
			),
			patch("autods.service.doctype.service_appointment.service_appointment.frappe.msgprint"),
			patch(
				"autods.service.doctype.service_appointment.service_appointment.frappe.db.has_column",
				return_value=True,
			),
		):
			ServiceAppointment.create_repair_order(doc)

		mock_ro.insert.assert_called_once()
		mock_ro.append.assert_not_called()
		mock_ro.fetch_template_items.assert_not_called()


def run_timestamp_regression_check():
	"""Run on a full site via: bench --site <site> execute autods.service.doctype.service_appointment.test_service_appointment.run_timestamp_regression_check"""
	row = frappe.db.sql(
		"""
		SELECT vu.customer, vu.name
		FROM `tabVehicle Unit` vu
		INNER JOIN `tabCustomer` c ON c.name = vu.customer
		ORDER BY vu.creation DESC
		LIMIT 1
		"""
	)
	if not row:
		print("SKIP: Customer and Vehicle Unit required")
		return
	customer, vehicle = row[0]

	sa = frappe.get_doc(
		{
			"doctype": "Service Appointment",
			"customer": customer,
			"vehicle_unit": vehicle,
			"appointment_date": add_days(today(), 30),
			"appointment_start_time": "14:00:00",
			"appointment_end_time": "15:00:00",
			"expected_completion_date": add_days(today(), 32),
			"status": "Scheduled",
		}
	)
	sa.insert(ignore_permissions=True)
	sa.submit()

	db_modified = frappe.db.get_value("Service Appointment", sa.name, "modified")
	if str(db_modified) != str(sa.modified):
		raise AssertionError(f"modified mismatch after submit: db={db_modified}, doc={sa.modified}")

	client_doc = frappe.get_doc({**sa.as_dict(), "doctype": "Service Appointment"})
	client_doc._original_modified = client_doc.modified
	client_doc.check_if_latest()
	estimate_name = client_doc.create_repair_estimate()
	if not estimate_name:
		raise AssertionError("create_repair_estimate returned empty result")

	frappe.db.rollback()
	print("PASS: submit then create_repair_estimate without timestamp mismatch")
