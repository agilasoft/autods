# Copyright (c) 2026, Agilasoft Technologies Inc. and Contributors
# See license.txt

import frappe
from frappe.tests import UnitTestCase


class TestVehicleUnit(UnitTestCase):
	def setUp(self):
		self._created = []

	def tearDown(self):
		for name in reversed(self._created):
			if frappe.db.exists("Vehicle Unit", name):
				frappe.delete_doc("Vehicle Unit", name, force=True, ignore_permissions=True)
		self._created = []

	def _uid(self, length=8):
		return frappe.generate_hash(length=length)

	def _make_vehicle_unit(self, code, **kwargs):
		doc = frappe.get_doc(
			{
				"doctype": "Vehicle Unit",
				"code": code,
				**kwargs,
			}
		)
		doc.insert(ignore_permissions=True)
		self._created.append(doc.name)
		return doc

	def test_duplicate_plate_no_raises(self):
		plate = f"PLATE-{self._uid()}"
		self._make_vehicle_unit(f"VU-PLATE-{self._uid()}", plate_no=plate)
		with self.assertRaises(frappe.ValidationError):
			self._make_vehicle_unit(f"VU-PLATE-{self._uid()}", plate_no=plate)

	def test_duplicate_engine_number_raises(self):
		engine = f"ENG-{self._uid()}"
		self._make_vehicle_unit(f"VU-ENG-{self._uid()}", engine_number=engine)
		with self.assertRaises(frappe.ValidationError):
			self._make_vehicle_unit(f"VU-ENG-{self._uid()}", engine_number=engine)

	def test_duplicate_chassis_number_raises(self):
		chassis = f"CHS-{self._uid()}"
		self._make_vehicle_unit(f"VU-CHS-{self._uid()}", chassis_number=chassis)
		with self.assertRaises(frappe.ValidationError):
			self._make_vehicle_unit(f"VU-CHS-{self._uid()}", chassis_number=chassis)

	def test_case_insensitive_and_trimmed_duplicates_raise(self):
		token = self._uid()
		self._make_vehicle_unit(f"VU-CASE-{self._uid()}", plate_no=f"Abc-{token}")
		with self.assertRaises(frappe.ValidationError):
			self._make_vehicle_unit(f"VU-CASE-{self._uid()}", plate_no=f"  abc-{token}  ")

	def test_blank_identifiers_allowed_on_multiple_docs(self):
		a = self._make_vehicle_unit(f"VU-BLANK-{self._uid()}")
		b = self._make_vehicle_unit(f"VU-BLANK-{self._uid()}", plate_no="   ")
		self.assertFalse(a.plate_no)
		self.assertEqual(b.plate_no, "")

	def test_update_same_document_identifiers_succeeds(self):
		token = self._uid()
		plate = f"KEEP-PLATE-{token}"
		doc = self._make_vehicle_unit(
			f"VU-UPD-{self._uid()}",
			plate_no=plate,
			engine_number=f"KEEP-ENG-{token}",
			chassis_number=f"KEEP-CHS-{token}",
		)
		doc.reload()
		doc.description = "Updated description"
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.plate_no, plate)
