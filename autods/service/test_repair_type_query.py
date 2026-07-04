import sys
import types
import unittest
from unittest.mock import patch


def _install_frappe_stubs():
	if "frappe" in sys.modules:
		return

	frappe = types.ModuleType("frappe")
	frappe.db = types.SimpleNamespace(get_value=lambda *args, **kwargs: None)
	frappe.scrub = lambda value: value

	def identity_decorator(*args, **kwargs):
		if args and callable(args[0]):
			return args[0]
		return lambda fn: fn

	frappe.whitelist = identity_decorator

	desk = types.ModuleType("frappe.desk")
	reportview = types.ModuleType("frappe.desk.reportview")
	reportview.get_filters_cond = lambda *args, **kwargs: ""
	reportview.get_match_cond = lambda *args, **kwargs: ""
	search = types.ModuleType("frappe.desk.search")
	search.validate_and_sanitize_search_inputs = identity_decorator
	utils = types.ModuleType("frappe.utils")
	utils.nowdate = lambda: "2026-01-01"

	sys.modules["frappe"] = frappe
	sys.modules["frappe.desk"] = desk
	sys.modules["frappe.desk.reportview"] = reportview
	sys.modules["frappe.desk.search"] = search
	sys.modules["frappe.utils"] = utils


_install_frappe_stubs()

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
