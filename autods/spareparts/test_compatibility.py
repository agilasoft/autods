# Copyright (c) 2026, Agilasoft Technologies Inc. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from autods.spareparts.compatibility import (
	get_compatible_parts,
	is_part_compatible,
	rule_matches,
)
from autods.service.queries import spareparts_item_link_query


class TestPartsCompatibility(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._ensure_master_data()
		cls._create_test_items()
		cls._create_compatibility_rules()
		cls._create_vehicle_units()

	@classmethod
	def _ensure_master_data(cls):
		cls.make = cls._get_or_create(
			"Vehicle Make",
			{"code": "PC-TEST-TOYOTA", "description": "PC Test Toyota"},
			"PC-TEST-TOYOTA",
		)
		cls.model = cls._get_or_create(
			"Vehicle Model",
			{"code": "PC-TEST-VIOS", "description": "PC Test Vios", "make": cls.make},
			"PC-TEST-VIOS",
		)
		cls.transmission_mt = cls._get_or_create(
			"Transmission Type",
			{"code": "PC-TEST-MT", "description": "PC Test Manual"},
			"PC-TEST-MT",
		)
		cls.transmission_at = cls._get_or_create(
			"Transmission Type",
			{"code": "PC-TEST-AT", "description": "PC Test Automatic"},
			"PC-TEST-AT",
		)

	@classmethod
	def _get_or_create(cls, doctype, data, name_field_value):
		existing = frappe.db.exists(doctype, name_field_value)
		if existing:
			return name_field_value
		doc = frappe.get_doc({"doctype": doctype, **data})
		doc.insert(ignore_permissions=True)
		return doc.name

	@classmethod
	def _create_test_items(cls):
		item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups"
		cls.item_universal = cls._create_sparepart("PC-TEST-SHOP-TOWEL", item_group)
		cls.item_model = cls._create_sparepart("PC-TEST-OIL-FILTER", item_group)
		cls.item_manual = cls._create_sparepart("PC-TEST-CLUTCH-KIT", item_group)
		cls.item_auto = cls._create_sparepart("PC-TEST-AT-FLUID", item_group)

	@classmethod
	def _create_sparepart(cls, item_code, item_group):
		if frappe.db.exists("Item", item_code):
			return item_code
		doc = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": item_group,
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"custom_service_item_type": "Spareparts",
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	@classmethod
	def _create_compatibility_rules(cls):
		cls.rule_universal = cls._create_rule(
			part=cls.item_universal,
			applies_to_all_vehicles=1,
		)
		cls.rule_model = cls._create_rule(
			part=cls.item_model,
			vehicle_model=cls.model,
			year_from=2018,
			year_to=2024,
		)
		cls.rule_manual = cls._create_rule(
			part=cls.item_manual,
			vehicle_model=cls.model,
			transmission_type=cls.transmission_mt,
		)
		cls.rule_auto = cls._create_rule(
			part=cls.item_auto,
			vehicle_model=cls.model,
			transmission_type=cls.transmission_at,
		)

	@classmethod
	def _create_rule(cls, **kwargs):
		filters = {"part": kwargs.get("part")}
		for field in ("vehicle_model", "transmission_type", "applies_to_all_vehicles"):
			if field in kwargs:
				filters[field] = kwargs[field]
		existing = frappe.db.get_value("Parts Compatibility", filters, "name")
		if existing:
			doc = frappe.get_doc("Parts Compatibility", existing)
			for field, value in kwargs.items():
				doc.set(field, value)
			doc.is_active = kwargs.get("is_active", doc.is_active or 1)
			doc.save(ignore_permissions=True)
			return doc.name
		doc = frappe.get_doc(
			{
				"doctype": "Parts Compatibility",
				"naming_series": "PC.#########",
				"is_active": 1,
				**kwargs,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	@classmethod
	def _create_vehicle_units(cls):
		cls.vu_manual = cls._create_vehicle_unit(
			"PC-TEST-VU-MT",
			transmission_type=cls.transmission_mt,
			year_model=2022,
		)
		cls.vu_auto = cls._create_vehicle_unit(
			"PC-TEST-VU-AT",
			transmission_type=cls.transmission_at,
			year_model=2020,
		)

	@classmethod
	def _create_vehicle_unit(cls, code, transmission_type, year_model):
		if frappe.db.exists("Vehicle Unit", code):
			frappe.db.set_value(
				"Vehicle Unit",
				code,
				{
					"make": cls.make,
					"model": cls.model,
					"year_model": year_model,
					"transmission_type": transmission_type,
				},
			)
			frappe.clear_document_cache("Vehicle Unit", code)
			return code
		doc = frappe.get_doc(
			{
				"doctype": "Vehicle Unit",
				"code": code,
				"make": cls.make,
				"model": cls.model,
				"year_model": year_model,
				"transmission_type": transmission_type,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_universal_part_matches_any_vehicle(self):
		specs = {"make": "X", "model": "Y", "variant": None, "year": 2020, "transmission_type": "Z"}
		rule = {"is_active": 1, "applies_to_all_vehicles": 1}
		self.assertTrue(rule_matches(rule, specs))
		self.assertTrue(is_part_compatible(self.item_universal, vehicle_unit=self.vu_manual))

	def test_model_rule_matches_both_transmissions(self):
		self.assertTrue(is_part_compatible(self.item_model, vehicle_unit=self.vu_manual))
		self.assertTrue(is_part_compatible(self.item_model, vehicle_unit=self.vu_auto))

	def test_transmission_specific_rules(self):
		self.assertTrue(is_part_compatible(self.item_manual, vehicle_unit=self.vu_manual))
		self.assertFalse(is_part_compatible(self.item_manual, vehicle_unit=self.vu_auto))
		self.assertTrue(is_part_compatible(self.item_auto, vehicle_unit=self.vu_auto))
		self.assertFalse(is_part_compatible(self.item_auto, vehicle_unit=self.vu_manual))

	def test_year_range(self):
		specs_in_range = {
			"make": self.make,
			"model": self.model,
			"variant": None,
			"year": 2022,
			"transmission_type": self.transmission_mt,
		}
		specs_out_of_range = dict(specs_in_range, year=2016)
		rule = {
			"is_active": 1,
			"applies_to_all_vehicles": 0,
			"vehicle_model": self.model,
			"vehicle_make": None,
			"vehicle_variant": None,
			"transmission_type": None,
			"year_from": 2018,
			"year_to": 2024,
		}
		self.assertTrue(rule_matches(rule, specs_in_range))
		self.assertFalse(rule_matches(rule, specs_out_of_range))

	def test_inactive_rule_excluded(self):
		frappe.db.set_value("Parts Compatibility", self.rule_auto, "is_active", 0)
		self.assertFalse(is_part_compatible(self.item_auto, vehicle_unit=self.vu_auto))
		frappe.db.set_value("Parts Compatibility", self.rule_auto, "is_active", 1)

	def test_get_compatible_parts_for_manual_vehicle(self):
		parts = {row["part"] for row in get_compatible_parts(vehicle_unit=self.vu_manual)}
		self.assertEqual(
			parts,
			{self.item_universal, self.item_model, self.item_manual},
		)

	def test_spareparts_item_link_query_filters_by_specs(self):
		results = spareparts_item_link_query(
			"Item",
			"PC-TEST",
			"name",
			0,
			20,
			{
				"vehicle_unit": self.vu_manual,
			},
		)
		names = {row[0] if isinstance(row, (list, tuple)) else row.name for row in results}
		self.assertIn(self.item_universal, names)
		self.assertIn(self.item_manual, names)
		self.assertNotIn(self.item_auto, names)

	def test_parts_compatibility_validation_requires_scope(self):
		doc = frappe.get_doc(
			{
				"doctype": "Parts Compatibility",
				"part": self.item_universal,
				"naming_series": "PC.#########",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)

	def test_universal_flag_clears_vehicle_fields(self):
		item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups"
		temp_part = self._create_sparepart("PC-TEST-UNIVERSAL-FLAG", item_group)
		doc = frappe.get_doc(
			{
				"doctype": "Parts Compatibility",
				"part": temp_part,
				"naming_series": "PC.#########",
				"applies_to_all_vehicles": 1,
				"vehicle_model": self.model,
			}
		)
		doc.insert(ignore_permissions=True)
		self.assertFalse(doc.vehicle_model)
		doc.delete(ignore_permissions=True)
