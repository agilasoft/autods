# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import sys
import types
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch


def _install_frappe_stubs():
	if "frappe" in sys.modules:
		return

	frappe = types.ModuleType("frappe")

	def identity_decorator(*args, **kwargs):
		if args and callable(args[0]):
			return args[0]
		return lambda fn: fn

	def _throw(msg, *args, **kwargs):
		raise Exception(msg.format(*args, **kwargs) if args else msg)

	frappe._ = lambda s, *args, **kwargs: s.format(*args, **kwargs) if args else s
	frappe.throw = _throw
	frappe.bold = lambda value: value
	frappe.whitelist = identity_decorator
	frappe.get_cached_doc = lambda *args, **kwargs: None
	frappe.get_all = lambda *args, **kwargs: []
	frappe.db = types.SimpleNamespace(
		get_value=lambda *args, **kwargs: None,
		sql=lambda *args, **kwargs: ((0,),),
		exists=lambda *args, **kwargs: False,
		count=lambda *args, **kwargs: 0,
	)

	utils = types.ModuleType("frappe.utils")
	utils.add_to_date = lambda dt, **kwargs: dt
	utils.cint = lambda value: int(value or 0)
	utils.flt = lambda value, precision=None: float(value or 0)
	utils.get_datetime = lambda value: value if isinstance(value, datetime) else datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S")
	utils.getdate = lambda value: str(value)[:10]
	utils.today = lambda: "2026-06-16"

	sys.modules["frappe"] = frappe
	sys.modules["frappe.utils"] = utils


_install_frappe_stubs()

from autods.service.job_card_planning import build_plan


class _ChargeRow:
	def __init__(self, name, item, description="", standard_hours=0, hours=0, service_type=None, idx=0):
		self.name = name
		self.service_item_type = "Service"
		self.item = item
		self.item_name = item
		self.description = description
		self.standard_hours = standard_hours
		self.hours = hours
		self.service_type = service_type
		self.idx = idx


class _MockRO:
	def __init__(self, name, charges, repair_date="2026-06-16"):
		self.name = name
		self.charges = charges
		self.repair_date = repair_date
		self.customer = "CUST-001"
		self.vehicle_unit = "VU-001"
		self.plate_no = "ABC-123"
		self.repair_type = "General"

	def get(self, key, default=None):
		return getattr(self, key, default)


class _Settings:
	auto_assign_work_area = 0
	auto_assign_technician = 0
	respect_work_area_capacity = 0
	respect_technician_load = 0
	allow_overlapping_schedules = 0
	planning_max_extra_days = 0
	planning_shop_opens = "09:00:00"
	planning_shop_closes = "17:00:00"
	planning_slot_hours = 2
	planning_work_area_full = "warn_only"
	planning_past_shop_close = "warn_only"
	planning_technician_overlap = "warn_only"


class TestBuildPlanConsolidatedJobCard(unittest.TestCase):
	def _build(self, ro, existing_job_cards=None):
		existing_job_cards = existing_job_cards or []

		def fake_get_all(doctype, filters=None, pluck=None, order_by=None, limit=None):
			if doctype == "Job Card" and filters and filters.get("repair_order") == ro.name:
				return list(existing_job_cards)
			return []

		with patch("autods.service.job_card_planning._planning_settings", return_value=_Settings()), patch(
			"autods.service.job_card_planning.frappe.get_all", side_effect=fake_get_all
		), patch("autods.service.job_card_planning.frappe.db.get_value", return_value=None), patch(
			"autods.service.job_card_planning.frappe.db.sql", return_value=((0,),)
		), patch(
			"autods.service.job_card_planning.frappe.db.exists", return_value=False
		), patch(
			"autods.service.job_card_planning.frappe.db.count", return_value=0
		):
			return build_plan(ro)

	def test_build_plan_returns_one_line_for_multiple_service_rows(self):
		ro = _MockRO(
			"RO-00054",
			[
				_ChargeRow("svc-1", "CHNG-L", "Change Oil", standard_hours=2, idx=1),
				_ChargeRow("svc-2", "TRNSMSSN-NSPCTN", "Transmission inspection", standard_hours=1, idx=2),
			],
		)
		plan = self._build(ro)

		self.assertEqual(plan["service_line_count"], 2)
		self.assertEqual(len(plan["lines"]), 1)
		line = plan["lines"][0]
		self.assertEqual(line["seq"], 1)
		self.assertEqual(line["standard_hours"], 3)
		self.assertEqual(len(line["work_details"]), 2)
		self.assertEqual(line["charge_rows"], ["svc-1", "svc-2"])
		self.assertIn("Change Oil", line["description"])
		self.assertIn("Transmission inspection", line["description"])

	def test_build_plan_warns_when_multiple_job_cards_exist(self):
		ro = _MockRO("RO-00054", [_ChargeRow("svc-1", "CHNG-L", "Change Oil", standard_hours=2, idx=1)])
		plan = self._build(ro, existing_job_cards=["JC-00001", "JC-00002"])
		line = plan["lines"][0]

		self.assertEqual(line["existing_job_card"], "JC-00001")
		self.assertEqual(line["existing_job_cards"], ["JC-00001", "JC-00002"])
		self.assertTrue(any("Multiple Job Cards" in w for w in line["warnings"]))


if __name__ == "__main__":
	unittest.main()
