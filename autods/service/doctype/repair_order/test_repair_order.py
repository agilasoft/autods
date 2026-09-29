# Copyright (c) 2025, Agilasoft Technologies Inc. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import flt, today


class TestRepairOrder(UnitTestCase):
	def _make_customer(self):
		name = frappe.db.get_value("Customer", {}, "name")
		if name:
			return name
		doc = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "RO Test Customer",
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
		code = f"RO-TEST-{frappe.generate_hash(length=8)}"
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

	def _make_service_item(self):
		item_code = "RO-TEST-SERVICE-ITEM"
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

	def _make_repair_order(self, customer, vehicle_unit):
		ro = frappe.get_doc(
			{
				"doctype": "Repair Order",
				"customer": customer,
				"vehicle_unit": vehicle_unit,
				"repair_date": today(),
				"status": "Draft",
			}
		)
		ro.flags.ignore_mandatory = True
		ro.insert(ignore_permissions=True)
		return ro

	def _make_service_template(self, item_code):
		template_name = f"TEST-TPL-RO-{frappe.generate_hash(length=8)}"
		tpl = frappe.get_doc(
			{
				"doctype": "Service Template",
				"template_name": template_name,
				"is_active": 1,
				"charges": [
					{
						"service_item_type": "Service",
						"item": item_code,
						"qty": 2,
						"rate": 750,
						"amount": 1500,
						"bill_type": "Customer",
					}
				],
			}
		)
		tpl.insert(ignore_permissions=True)
		return tpl

	def test_fetch_template_items_populates_charges(self):
		"""Actions → Load Service Template must fill Repair Order charges."""
		customer = self._make_customer()
		vehicle_unit = self._make_vehicle_unit(customer)
		ro_name = self._make_repair_order(customer, vehicle_unit).name

		item_code = self._make_service_item()
		tpl = self._make_service_template(item_code)

		# Fresh load avoids timestamp skew from after_insert link persistence
		ro = frappe.get_doc("Repair Order", ro_name)
		with patch("autods.service.doctype.repair_order.repair_order.frappe.msgprint"):
			result = ro.fetch_template_items(service_template=tpl.name)

		ro.reload()
		self.assertEqual(len(ro.charges), 1)
		self.assertEqual(ro.charges[0].item, item_code)
		self.assertEqual(flt(ro.charges[0].qty), 2)
		self.assertEqual(flt(ro.charges[0].rate), 750)
		self.assertEqual(result["service_items_count"], 1)
