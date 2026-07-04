import unittest
from unittest.mock import patch

from autods.service.queries import _repair_type_flag_for_service_type


class TestRepairTypeQuery(unittest.TestCase):
	def test_body_and_paint_service_types_use_body_repair_types(self):
		for category in ("Body", "Paint"):
			with self.subTest(category=category):
				with patch("autods.service.queries.frappe.db.get_value", return_value=category):
					self.assertEqual(_repair_type_flag_for_service_type("SERVICE-TYPE"), "is_body_repair")

	def test_general_service_categories_use_general_repair_types(self):
		for category in ("General", "Special", "Other"):
			with self.subTest(category=category):
				with patch("autods.service.queries.frappe.db.get_value", return_value=category):
					self.assertEqual(_repair_type_flag_for_service_type("SERVICE-TYPE"), "is_general_repair")

	def test_missing_service_type_has_no_flag_filter(self):
		self.assertIsNone(_repair_type_flag_for_service_type(None))
