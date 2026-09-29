# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import sys
import types
import unittest
from unittest.mock import patch


def _install_frappe_stubs():
	if "frappe" in sys.modules and hasattr(sys.modules["frappe"], "db"):
		return

	frappe = types.ModuleType("frappe")

	def _throw(message, *args, **kwargs):
		raise Exception(message)

	frappe.throw = _throw
	frappe.bold = lambda value: value
	frappe._ = lambda message, *args, **kwargs: message
	frappe.db = types.SimpleNamespace(
		exists=lambda *args, **kwargs: True,
		get_value=lambda *args, **kwargs: None,
		get_all=lambda *args, **kwargs: [],
	)
	frappe.get_meta = lambda *args, **kwargs: types.SimpleNamespace(has_field=lambda field: False)
	frappe.get_all = lambda *args, **kwargs: []
	frappe.get_single = lambda *args, **kwargs: {}

	utils = types.ModuleType("frappe.utils")
	utils.flt = lambda value, *args, **kwargs: float(value or 0)

	sys.modules["frappe"] = frappe
	sys.modules["frappe.utils"] = utils


_install_frappe_stubs()

import frappe
from autods.service.repair_order_invoice import (
	RepairInvoiceError,
	build_invoice_groups,
	invoice_lines,
	select_invoice_group,
)
from autods.vehicle_sales.si_integration import _is_vehicle_sale, set_vehicle_links


class _Meta:
	def __init__(self, fields):
		self._fields = set(fields)

	def has_field(self, name):
		return name in self._fields


class _Doc:
	def __init__(self, meta=None, items=None, **values):
		self.meta = meta if meta is not None else _Meta(["vehicle_unit", "repair_order", "custom_vehicle_sales"])
		self.items = items or []
		self.__dict__.update(values)

	def get(self, key, default=None):
		if key == "items":
			return self.items
		return self.__dict__.get(key, default)

	def set(self, key, value):
		setattr(self, key, value)


class TestRepairOrderInvoiceGroups(unittest.TestCase):
	def setUp(self):
		self.header = {
			"customer": "CUST-1",
			"insurance_company": "INS-1",
			"warranty": "WAR-1",
			"net_total": 300,
			"insurance_participation_fee": 25,
			"insurance_other_fees_description": "Towing",
		}
		self.charges = [
			{
				"item": "LABOR",
				"item_name": "Labor",
				"qty": 1,
				"rate": 100,
				"amount": 100,
				"bill_type": "Customer",
				"uom": "Hour",
			},
			{
				"item": "PART",
				"item_name": "Pad",
				"qty": 2,
				"rate": 50,
				"amount": 100,
				"bill_type": "Insurance",
				"uom": "Nos",
			},
			{
				"item": "PART2",
				"item_name": "Filter",
				"qty": 1,
				"rate": 100,
				"amount": 100,
				"bill_type": "Warranty",
				"bill_to": "WAR-2",
				"uom": "Nos",
			},
			{"item": "SKIP", "item_name": "Skip", "amount": 0, "bill_type": "Customer"},
		]
		self.taxes = [
			{"charge_type": "On Net Total", "account_head": "VAT - C", "rate": 12, "tax_amount": 36},
			{"charge_type": "Actual", "account_head": "Fee - C", "tax_amount": 30, "description": "Env"},
		]
		self.collectible_items = {
			"insurance_participation_item": "FEE-PART",
			"insurance_participation_item_uom": "Nos",
		}

	def _groups(self, header=None, charges=None, items=None):
		return build_invoice_groups(
			self.header if header is None else header,
			self.charges if charges is None else charges,
			self.taxes,
			self.collectible_items if items is None else items,
		)

	def test_splits_one_invoice_per_payer(self):
		groups = self._groups()
		self.assertEqual([group["bill_type"] for group in groups], ["Customer", "Insurance", "Warranty"])
		self.assertEqual([group["bill_to"] for group in groups], ["CUST-1", "INS-1", "WAR-2"])

		customer = groups[0]
		self.assertEqual(customer["charge_net"], 100)
		self.assertEqual(customer["collectible_amount"], 25)
		self.assertEqual(customer["net"], 125)
		self.assertEqual(customer["lines"][0]["item_code"], "LABOR")
		self.assertEqual(customer["lines"][1]["item_code"], "FEE-PART")
		self.assertEqual(customer["lines"][1]["description"], "Insurance participation fee")
		self.assertEqual(invoice_lines(customer["lines"])[1].get("_collectible"), None)

		actual = [row for row in customer["taxes"] if row["charge_type"] == "Actual"][0]
		percent = [row for row in customer["taxes"] if row["charge_type"] == "On Net Total"][0]
		self.assertAlmostEqual(actual["tax_amount"], 10)
		self.assertEqual(percent["rate"], 12)

		self.assertEqual(groups[1]["charge_net"], 100)
		self.assertEqual(groups[1]["collectible_amount"], 0)
		self.assertAlmostEqual(groups[2]["taxes"][1]["tax_amount"], 10)

	def test_row_bill_to_overrides_header_party(self):
		warranty = select_invoice_group(self._groups(), "Warranty", "WAR-2")
		self.assertEqual(warranty["lines"][0]["item_code"], "PART2")

	def test_blank_bill_type_is_customer(self):
		groups = self._groups(
			header={"customer": "CUST-1", "net_total": 40},
			charges=[{"item": "LABOR", "item_name": "Labor", "qty": 1, "rate": 40, "amount": 40, "uom": "Nos"}],
			items={},
		)
		self.assertEqual(len(groups), 1)
		self.assertEqual(groups[0]["bill_type"], "Customer")
		self.assertEqual(groups[0]["bill_to"], "CUST-1")

	def test_collectibles_alone_still_invoice_the_customer(self):
		groups = build_invoice_groups(
			{"customer": "CUST-1", "insurance_participation_fee": 10},
			[],
			None,
			{"insurance_participation_item": "FEE-PART"},
		)
		self.assertEqual(len(groups), 1)
		self.assertEqual(groups[0]["bill_to"], "CUST-1")
		self.assertEqual(groups[0]["charge_net"], 0)
		self.assertEqual(groups[0]["net"], 10)

	def test_missing_collectible_item_raises(self):
		header = dict(self.header)
		header["insurance_depreciation_fee"] = 5
		with self.assertRaises(RepairInvoiceError):
			self._groups(header=header)

	def test_unknown_payer_raises(self):
		with self.assertRaises(RepairInvoiceError):
			select_invoice_group(self._groups(), "Insurance", "SOMEONE-ELSE")


class TestRepairInvoiceIsNotVehicleSale(unittest.TestCase):
	def test_vehicle_unit_on_a_repair_invoice_is_not_a_vehicle_sale(self):
		doc = _Doc(repair_order="RO-1", vehicle_unit="VU-1", update_stock=1)
		self.assertFalse(_is_vehicle_sale(doc))

	def test_vehicle_sale_markers_still_count(self):
		self.assertTrue(_is_vehicle_sale(_Doc(custom_vehicle_sales=1, vehicle_unit="VU-1")))
		self.assertTrue(_is_vehicle_sale(_Doc(vehicle_unit="VU-1")))
		self.assertTrue(_is_vehicle_sale(_Doc(repair_order="RO-1", custom_vehicle_sales=1, vehicle_unit="VU-1")))
		self.assertTrue(_is_vehicle_sale(_Doc(vehicle_sales_order="VSO-1")))

	def test_validate_sets_vehicle_unit_and_does_not_block_stock_flag(self):
		child = _Doc(meta=_Meta(["repair_order", "vehicle_unit"]), item_code="LABOR")
		doc = _Doc(repair_order="RO-1", update_stock=1, items=[child])
		frappe.db.exists = lambda *args, **kwargs: True
		frappe.db.get_value = lambda *args, **kwargs: "VU-9"

		set_vehicle_links(doc)

		self.assertEqual(doc.vehicle_unit, "VU-9")
		self.assertEqual(child.repair_order, "RO-1")
		self.assertEqual(child.vehicle_unit, "VU-9")
		self.assertEqual(doc.update_stock, 1)

	def test_does_not_overwrite_an_existing_vehicle_unit(self):
		doc = _Doc(repair_order="RO-1", vehicle_unit="KEEP", items=[])
		frappe.db.exists = lambda *args, **kwargs: True
		frappe.db.get_value = lambda *args, **kwargs: "VU-9"

		set_vehicle_links(doc)

		self.assertEqual(doc.vehicle_unit, "KEEP")

	def test_vehicle_sale_still_rejects_update_stock(self):
		doc = _Doc(custom_vehicle_sales=1, vehicle_unit="VU-1", update_stock=1, items=[])
		with self.assertRaises(Exception):
			set_vehicle_links(doc)

	def test_duplicate_repair_invoice_is_rejected(self):
		doc = _Doc(
			name="SINV-NEW",
			repair_order="RO-1",
			customer="CUST-1",
			custom_repair_bill_type="Customer",
			items=[],
		)

		def _throw(message, *args, **kwargs):
			raise Exception(str(message))

		with patch("autods.service.repair_order_invoice.frappe.db.exists", return_value=True), patch(
			"autods.service.repair_order_invoice.frappe.db.get_value", return_value=None
		), patch(
			"autods.service.repair_order_invoice.frappe.get_meta",
			return_value=types.SimpleNamespace(has_field=lambda field: True),
		), patch(
			"autods.service.repair_order_invoice.frappe.get_all", return_value=["SINV-EXISTING"], create=True
		), patch("autods.service.repair_order_invoice.frappe.throw", _throw):
			with self.assertRaises(Exception) as raised:
				set_vehicle_links(doc)

		self.assertIn("SINV-EXISTING", str(raised.exception))
