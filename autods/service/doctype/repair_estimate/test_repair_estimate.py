# Copyright (c) 2026, Agilasoft Technologies Inc. and Contributors
# See license.txt

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import add_days, flt, getdate, today

from autods.service.doctype.repair_estimate.repair_estimate import RepairEstimate
from autods.service.service_appointment_utils import get_expected_completion_datetime


class TestRepairEstimateChargesOnSubmit(unittest.TestCase):
	def test_before_submit_rejects_empty_charges(self):
		doc = MagicMock()
		doc._charge_rows = lambda: []
		with self.assertRaises(frappe.ValidationError) as ctx:
			RepairEstimate.before_submit(doc)
		self.assertIn("charge line", str(ctx.exception).lower())

	def test_before_submit_allows_when_charges_present(self):
		doc = MagicMock()
		doc._charge_rows = lambda: [object()]
		RepairEstimate.before_submit(doc)


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
		code = f"RE-TEST-{frappe.generate_hash(length=8)}"
		if frappe.db.exists("Vehicle Unit", code):
			return code
		doc = frappe.get_doc(
			{
				"doctype": "Vehicle Unit",
				"customer": customer,
				"code": code,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _make_service_appointment(self, customer, vehicle_unit):
		token = frappe.generate_hash(length=8)
		day_offset = 90 + (int(token[:4], 16) % 400)
		hour = 8 + (int(token[4:6], 16) % 8)
		minute = int(token[6:8], 16) % 50
		start = f"{hour:02d}:{minute:02d}:00"
		end_minute = minute + 30
		end_hour = hour if end_minute < 60 else hour + 1
		end_minute = end_minute if end_minute < 60 else end_minute - 60
		end = f"{end_hour:02d}:{end_minute:02d}:00"
		sa = frappe.get_doc(
			{
				"doctype": "Service Appointment",
				"customer": customer,
				"vehicle_unit": vehicle_unit,
				"appointment_date": add_days(today(), day_offset),
				"appointment_start_time": start,
				"appointment_end_time": end,
				"expected_completion_date": add_days(today(), day_offset + 2),
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

	def _make_service_item(self):
		item_code = "RE-TEST-SERVICE-ITEM"
		if frappe.db.exists("Item", item_code):
			return item_code
		item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups"
		doc = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": item_group,
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"custom_service_item_type": "Service",
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _add_charge_line(self, estimate):
		estimate.append(
			"charges",
			{
				"service_item_type": "Service",
				"item": self._make_service_item(),
				"qty": 1,
				"rate": 100,
				"bill_type": "Customer",
			},
		)
		estimate.save(ignore_permissions=True)
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
		self._add_charge_line(estimate)
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

	def _make_service_template(self, item_code, suffix="RE"):
		template_name = f"TEST-TPL-{suffix}-{frappe.generate_hash(length=8)}"
		tpl = frappe.get_doc(
			{
				"doctype": "Service Template",
				"template_name": template_name,
				"is_active": 1,
				"charges": [
					{
						"service_item_type": "Service",
						"item": item_code,
						"qty": 1,
						"rate": 1500,
						"amount": 1500,
						"bill_type": "Customer",
					}
				],
			}
		)
		tpl.insert(ignore_permissions=True)
		return tpl

	def test_fetch_template_items_populates_charges(self):
		"""Actions → Load Service Template must fill Repair Estimate charges."""
		customer = self._make_customer()
		vehicle_unit = self._make_vehicle_unit(customer)
		estimate_name = self._make_repair_estimate(customer, vehicle_unit).name

		item_code = self._make_service_item()
		tpl = self._make_service_template(item_code, suffix="RE")

		estimate = frappe.get_doc("Repair Estimate", estimate_name)
		with patch("autods.service.doctype.repair_estimate.repair_estimate.frappe.msgprint"):
			result = estimate.fetch_template_items(service_template=tpl.name)

		estimate.reload()
		self.assertEqual(len(estimate.charges), 1)
		self.assertEqual(estimate.charges[0].item, item_code)
		self.assertEqual(flt(estimate.charges[0].qty), 1)
		self.assertEqual(flt(estimate.charges[0].rate), 1500)
		self.assertEqual(result["service_items_count"], 1)
