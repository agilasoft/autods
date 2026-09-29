# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import sys
import types
import unittest
from datetime import datetime
from unittest.mock import patch


def _install_frappe_stubs():
	frappe = sys.modules.get("frappe")
	if frappe is None:
		frappe = types.ModuleType("frappe")
		sys.modules["frappe"] = frappe

	def identity_decorator(*args, **kwargs):
		if args and callable(args[0]):
			return args[0]
		return lambda fn: fn

	def _throw(msg, *args, **kwargs):
		raise Exception(msg.format(*args, **kwargs) if args else msg)

	frappe._ = getattr(frappe, "_", None) or (lambda s, *args, **kwargs: s.format(*args, **kwargs) if args else s)
	frappe.throw = getattr(frappe, "throw", None) or _throw
	frappe.bold = getattr(frappe, "bold", None) or (lambda value: value)
	frappe.whitelist = getattr(frappe, "whitelist", None) or identity_decorator
	frappe.get_cached_doc = getattr(frappe, "get_cached_doc", None) or (lambda *args, **kwargs: None)
	frappe.get_all = getattr(frappe, "get_all", None) or (lambda *args, **kwargs: [])
	if not getattr(frappe, "db", None):
		frappe.db = types.SimpleNamespace(
			get_value=lambda *args, **kwargs: None,
			sql=lambda *args, **kwargs: ((0,),),
			exists=lambda *args, **kwargs: False,
			count=lambda *args, **kwargs: 0,
		)

	utils = sys.modules.get("frappe.utils")
	if utils is None:
		utils = types.ModuleType("frappe.utils")
		sys.modules["frappe.utils"] = utils
	frappe.utils = utils

	def _add_to_date(dt, days=0, hours=0, **kwargs):
		from datetime import timedelta

		if isinstance(dt, str):
			try:
				dt = datetime.strptime(str(dt)[:19], "%Y-%m-%d %H:%M:%S")
			except ValueError:
				dt = datetime.strptime(str(dt)[:10], "%Y-%m-%d")
		return dt + timedelta(days=int(days or 0), hours=int(hours or 0))

	# Always own these helpers so other test modules' stubs do not leak in.
	utils.add_to_date = _add_to_date
	utils.cint = lambda value: int(value or 0)
	utils.flt = lambda value, precision=None: float(value or 0)
	utils.get_datetime = (
		lambda value: value if isinstance(value, datetime) else datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S")
	)
	utils.getdate = lambda value: str(value)[:10]
	utils.today = lambda: "2026-06-16"


_install_frappe_stubs()

from autods.service.job_card_planning import (
	build_plan,
	build_service_selection,
	get_locked_charge_row_names,
	validate_charges_not_locked,
	validate_no_new_links_to_locked_services,
)


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
	def __init__(self, name, charges, repair_date="2026-06-16", **kwargs):
		self.name = name
		self.charges = charges
		self.repair_date = repair_date
		self.customer = kwargs.get("customer", "CUST-001")
		self.vehicle_unit = kwargs.get("vehicle_unit", "VU-001")
		self.plate_no = kwargs.get("plate_no", "ABC-123")
		self.repair_type = kwargs.get("repair_type", "General")
		self.vehicle_year_model = kwargs.get("vehicle_year_model")
		self.vehicle_make = kwargs.get("vehicle_make")
		self.vehicle_model = kwargs.get("vehicle_model")

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


class TestBuildPlanPerServiceJobCard(unittest.TestCase):
	def _selection_get_all(self, jc_mapping=None, item_images=None, sibling_job_cards=None):
		jc_mapping = jc_mapping or {}
		item_images = item_images or {}
		sibling_job_cards = sibling_job_cards or []

		def fake_get_all(doctype, filters=None, pluck=None, order_by=None, limit=None, or_filters=None, fields=None):
			if doctype == "Job Card" and filters:
				charge_row = filters.get("service_charge_row")
				if charge_row:
					if charge_row in jc_mapping:
						return [jc_mapping[charge_row]]
					return []
				# Sibling Job Cards for planning seed (no service_charge_row filter).
				if filters.get("repair_order") and fields:
					return list(sibling_job_cards)
				return []
			if doctype == "Item" and filters:
				names = filters.get("name")
				if isinstance(names, tuple) and names[0] == "in":
					codes = names[1]
					return [
						{"name": code, "image": item_images[code]}
						for code in codes
						if code in item_images
					]
			return []

		return fake_get_all

	def _build(self, ro, existing_by_charge_row=None, selected_charge_rows=None, sibling_job_cards=None):
		existing_by_charge_row = existing_by_charge_row or {}
		fake_get_all = self._selection_get_all(
			jc_mapping=existing_by_charge_row,
			sibling_job_cards=sibling_job_cards,
		)

		with patch("autods.service.job_card_planning._planning_settings", return_value=_Settings()), patch(
			"autods.service.job_card_planning.frappe.get_all", side_effect=fake_get_all
		), patch("autods.service.job_card_planning.frappe.db.get_value", return_value=None), patch(
			"autods.service.job_card_planning.frappe.db.sql", return_value=((0,),)
		), patch(
			"autods.service.job_card_planning.frappe.db.exists", return_value=False
		), patch(
			"autods.service.job_card_planning.frappe.db.count", return_value=0
		):
			return build_plan(ro, selected_charge_rows)

	def test_build_plan_returns_one_line_per_service_row(self):
		ro = _MockRO(
			"RO-00054",
			[
				_ChargeRow("svc-1", "CHNG-L", "Change Oil", standard_hours=2, idx=1),
				_ChargeRow("svc-2", "TRNSMSSN-NSPCTN", "Transmission inspection", standard_hours=1, idx=2),
			],
		)
		plan = self._build(ro)

		self.assertEqual(plan["service_line_count"], 2)
		self.assertEqual(len(plan["lines"]), 2)
		self.assertEqual(plan["lines"][0]["charge_row"], "svc-1")
		self.assertEqual(plan["lines"][1]["charge_row"], "svc-2")
		self.assertEqual(plan["lines"][0]["standard_hours"], 2)
		self.assertEqual(plan["lines"][1]["standard_hours"], 1)
		self.assertEqual(len(plan["lines"][0]["work_details"]), 1)
		self.assertEqual(len(plan["lines"][1]["work_details"]), 1)
		self.assertEqual(plan["lines"][0]["charge_rows"], ["svc-1"])
		self.assertEqual(plan["lines"][1]["charge_rows"], ["svc-2"])

	def test_build_plan_filters_selected_charge_rows(self):
		ro = _MockRO(
			"RO-00054",
			[
				_ChargeRow("svc-1", "CHNG-L", "Change Oil", standard_hours=2, idx=1),
				_ChargeRow("svc-2", "TRNSMSSN-NSPCTN", "Transmission inspection", standard_hours=1, idx=2),
			],
		)
		plan = self._build(ro, selected_charge_rows=["svc-2"])

		self.assertEqual(plan["service_line_count"], 1)
		self.assertEqual(len(plan["lines"]), 1)
		self.assertEqual(plan["lines"][0]["charge_row"], "svc-2")
		self.assertEqual(plan["lines"][0]["description"], "Transmission inspection")

	def test_build_plan_marks_existing_job_card_per_service_line(self):
		ro = _MockRO(
			"RO-00054",
			[
				_ChargeRow("svc-1", "CHNG-L", "Change Oil", standard_hours=2, idx=1),
				_ChargeRow("svc-2", "TRNSMSSN-NSPCTN", "Transmission inspection", standard_hours=1, idx=2),
			],
		)
		plan = self._build(ro, existing_by_charge_row={"svc-1": "JC-00001"})

		self.assertEqual(plan["lines"][0]["existing_job_card"], "JC-00001")
		self.assertIsNone(plan["lines"][1]["existing_job_card"])

	def test_build_plan_seeds_cursor_from_existing_sibling_job_card(self):
		ro = _MockRO(
			"RO-00054",
			[
				_ChargeRow("svc-1", "CHNG-L", "Change Oil", standard_hours=2, idx=1),
				_ChargeRow("svc-2", "TRNSMSSN-NSPCTN", "Transmission inspection", standard_hours=1, idx=2),
			],
		)
		sibling = {
			"name": "JC-00001",
			"start_time": "2026-06-16 09:00:00",
			"end_time": "2026-06-16 11:00:00",
			"work_area": None,
			"service_charge_row": "svc-1",
			"technician": None,
		}
		plan = self._build(
			ro,
			existing_by_charge_row={"svc-1": "JC-00001"},
			selected_charge_rows=["svc-2"],
			sibling_job_cards=[sibling],
		)

		self.assertEqual(len(plan["lines"]), 1)
		self.assertEqual(plan["lines"][0]["charge_row"], "svc-2")
		# Shop open is 09:00; sibling JC ends at 11:00, so the next Service starts there.
		self.assertEqual(plan["lines"][0]["planned_start"], "2026-06-16 11:00:00")

	def test_build_service_selection_lists_services_with_existing_job_cards(self):
		ro = _MockRO(
			"RO-00054",
			[
				_ChargeRow("svc-1", "CHNG-L", "Change Oil", standard_hours=2, idx=1),
				_ChargeRow("svc-2", "TRNSMSSN-NSPCTN", "Transmission inspection", standard_hours=1, idx=2),
			],
		)
		fake_get_all = self._selection_get_all(jc_mapping={"svc-2": "JC-00010"})

		with patch("autods.service.job_card_planning._planning_settings", return_value=_Settings()), patch(
			"autods.service.job_card_planning.frappe.get_all", side_effect=fake_get_all
		), patch("autods.service.job_card_planning.frappe.db.get_value", return_value=None):
			selection = build_service_selection(ro)

		self.assertEqual(selection["service_line_count"], 2)
		self.assertEqual(selection["services"][0]["existing_job_card"], None)
		self.assertEqual(selection["services"][1]["existing_job_card"], "JC-00010")

	def test_build_service_selection_includes_vehicle_header(self):
		ro = _MockRO(
			"RO-00054",
			[_ChargeRow("svc-1", "CHNG-L", "Change Oil", standard_hours=2, idx=1)],
			vehicle_year_model=2024,
			vehicle_make="Nissan",
			vehicle_model="GT-R",
			plate_no="ABC-123",
		)

		def fake_get_value(doctype, name, fieldname, as_dict=False):
			if doctype == "Vehicle Unit" and name == "VU-001":
				return {
					"image": "/files/gtr.jpg",
					"make": "Nissan",
					"model": "GT-R",
					"year_model": 2024,
				}
			return None

		with patch("autods.service.job_card_planning._planning_settings", return_value=_Settings()), patch(
			"autods.service.job_card_planning.frappe.get_all", return_value=[]
		), patch(
			"autods.service.job_card_planning.frappe.db.get_value", side_effect=fake_get_value
		):
			selection = build_service_selection(ro)

		self.assertEqual(selection["vehicle_image"], "/files/gtr.jpg")
		self.assertEqual(selection["vehicle_title"], "2024 Nissan GT-R")
		self.assertEqual(selection["plate_no"], "ABC-123")
		self.assertEqual(selection["repair_date"], "2026-06-16")
		self.assertEqual(selection["vehicle_unit"], "VU-001")

	def test_build_plan_includes_vehicle_header(self):
		ro = _MockRO(
			"RO-00054",
			[_ChargeRow("svc-1", "CHNG-L", "Change Oil", standard_hours=2, idx=1)],
			vehicle_year_model=2024,
			vehicle_make="Nissan",
			vehicle_model="GT-R",
			plate_no="ABC-123",
		)

		def fake_get_value(doctype, name, fieldname, as_dict=False):
			if doctype == "Vehicle Unit" and name == "VU-001":
				return {
					"image": "/files/gtr.jpg",
					"make": "Nissan",
					"model": "GT-R",
					"year_model": 2024,
				}
			return None

		with patch("autods.service.job_card_planning._planning_settings", return_value=_Settings()), patch(
			"autods.service.job_card_planning.frappe.get_all", return_value=[]
		), patch(
			"autods.service.job_card_planning.frappe.db.get_value", side_effect=fake_get_value
		), patch(
			"autods.service.job_card_planning.frappe.db.sql", return_value=((0,),)
		), patch(
			"autods.service.job_card_planning.frappe.db.exists", return_value=False
		), patch(
			"autods.service.job_card_planning.frappe.db.count", return_value=0
		):
			plan = build_plan(ro)

		self.assertEqual(plan["vehicle_image"], "/files/gtr.jpg")
		self.assertEqual(plan["vehicle_title"], "2024 Nissan GT-R")
		self.assertEqual(plan["plate_no"], "ABC-123")
		self.assertEqual(plan["repair_date"], "2026-06-16")
		self.assertEqual(plan["vehicle_unit"], "VU-001")

	def test_build_service_selection_includes_item_image_per_service(self):
		ro = _MockRO(
			"RO-00054",
			[
				_ChargeRow("svc-1", "PMS", "PMS", standard_hours=2, idx=1),
				_ChargeRow("svc-2", "NO-IMG", "No image service", standard_hours=1, idx=2),
			],
		)
		fake_get_all = self._selection_get_all(item_images={"PMS": "/files/pms.jpg"})

		with patch("autods.service.job_card_planning._planning_settings", return_value=_Settings()), patch(
			"autods.service.job_card_planning.frappe.get_all", side_effect=fake_get_all
		), patch("autods.service.job_card_planning.frappe.db.get_value", return_value=None):
			selection = build_service_selection(ro)

		self.assertEqual(selection["services"][0]["item_image"], "/files/pms.jpg")
		self.assertEqual(selection["services"][0]["description"], "PMS")
		self.assertIsNone(selection["services"][1]["item_image"])
		self.assertEqual(selection["services"][1]["description"], "No image service")


class _LockChargeRow:
	def __init__(
		self,
		name,
		service_item_type="Service",
		item="ITEM",
		qty=1,
		rate=100,
		standard_hours=0,
		service_row=None,
		parent_service_charge=None,
		description="",
		bill_type="Customer",
		uom="Nos",
		bill_to="",
		item_type="",
		warehouse="",
		color_code="",
		paint_type="",
		idx=0,
	):
		self.name = name
		self.service_item_type = service_item_type
		self.item = item
		self.item_name = item
		self.qty = qty
		self.rate = rate
		self.standard_hours = standard_hours
		self.service_row = service_row
		self.parent_service_charge = parent_service_charge
		self.description = description
		self.bill_type = bill_type
		self.uom = uom
		self.bill_to = bill_to
		self.item_type = item_type
		self.warehouse = warehouse
		self.color_code = color_code
		self.paint_type = paint_type
		self.idx = idx


class _LockRO:
	def __init__(self, name, charges, is_new=False):
		self.name = name
		self.charges = charges
		self._is_new = is_new
		self._before = None

	def get(self, key, default=None):
		return getattr(self, key, default)

	def is_new(self):
		return self._is_new

	def get_doc_before_save(self):
		return self._before


class TestChargesLockedByJobCard(unittest.TestCase):
	def _jc_get_all(self, jc_by_service):
		def fake_get_all(doctype, filters=None, pluck=None, order_by=None, limit=None, fields=None, **kwargs):
			if doctype != "Job Card":
				return []
			filters = filters or {}
			if fields and "service_charge_row" in (fields or []):
				return [
					{"name": jc, "service_charge_row": svc}
					for svc, jc in jc_by_service.items()
				]
			charge_row = filters.get("service_charge_row")
			if charge_row and charge_row in jc_by_service:
				return [jc_by_service[charge_row]] if pluck else [{"name": jc_by_service[charge_row]}]
			return []

		return fake_get_all

	def test_get_locked_includes_service_and_linked_sparepart(self):
		ro = _LockRO(
			"RO-LOCK-1",
			[
				_LockChargeRow("svc-a", "Service", "PMS", idx=1),
				_LockChargeRow(
					"sp-1",
					"Spareparts",
					"OIL",
					service_row="1: PMS",
					parent_service_charge="svc-a",
					idx=2,
				),
				_LockChargeRow("svc-b", "Service", "Camera", idx=3),
				_LockChargeRow(
					"sp-2",
					"Spareparts",
					"CAM",
					service_row="2: Camera",
					parent_service_charge="svc-b",
					idx=4,
				),
			],
		)
		with patch(
			"autods.service.job_card_planning.frappe.get_all",
			side_effect=self._jc_get_all({"svc-a": "JC-001"}),
		):
			locked = get_locked_charge_row_names(ro)

		self.assertEqual(locked.get("svc-a"), "JC-001")
		self.assertEqual(locked.get("sp-1"), "JC-001")
		self.assertNotIn("svc-b", locked)
		self.assertNotIn("sp-2", locked)

	def test_cancelled_job_card_does_not_lock(self):
		ro = _LockRO(
			"RO-LOCK-2",
			[
				_LockChargeRow("svc-a", "Service", "PMS", idx=1),
				_LockChargeRow(
					"sp-1",
					"Spareparts",
					"OIL",
					parent_service_charge="svc-a",
					idx=2,
				),
			],
		)
		with patch("autods.service.job_card_planning.frappe.get_all", return_value=[]):
			locked = get_locked_charge_row_names(ro)
		self.assertEqual(locked, {})

	def test_validate_blocks_delete_of_locked_row(self):
		before = _LockRO(
			"RO-LOCK-3",
			[
				_LockChargeRow("svc-a", "Service", "PMS", idx=1),
				_LockChargeRow("sp-1", "Spareparts", "OIL", parent_service_charge="svc-a", idx=2),
			],
		)
		current = _LockRO(
			"RO-LOCK-3",
			[
				_LockChargeRow("svc-a", "Service", "PMS", idx=1),
			],
		)
		current._before = before

		with patch(
			"autods.service.job_card_planning.frappe.get_all",
			side_effect=self._jc_get_all({"svc-a": "JC-009"}),
		):
			with self.assertRaises(Exception) as ctx:
				validate_charges_not_locked(current)
		self.assertIn("JC-009", str(ctx.exception))

	def test_validate_blocks_edit_of_locked_row(self):
		before = _LockRO(
			"RO-LOCK-4",
			[
				_LockChargeRow("svc-a", "Service", "PMS", qty=1, rate=100, idx=1),
			],
		)
		current = _LockRO(
			"RO-LOCK-4",
			[
				_LockChargeRow("svc-a", "Service", "PMS", qty=2, rate=100, idx=1),
			],
		)
		current._before = before

		with patch(
			"autods.service.job_card_planning.frappe.get_all",
			side_effect=self._jc_get_all({"svc-a": "JC-010"}),
		):
			with self.assertRaises(Exception) as ctx:
				validate_charges_not_locked(current)
		self.assertIn("JC-010", str(ctx.exception))

	def test_validate_blocks_new_sparepart_link_to_locked_service(self):
		before = _LockRO(
			"RO-LOCK-5",
			[
				_LockChargeRow("svc-a", "Service", "PMS", idx=1),
			],
		)
		current = _LockRO(
			"RO-LOCK-5",
			[
				_LockChargeRow("svc-a", "Service", "PMS", idx=1),
				_LockChargeRow(
					"sp-new",
					"Spareparts",
					"FILTER",
					parent_service_charge="svc-a",
					idx=2,
				),
			],
		)
		current._before = before

		with patch(
			"autods.service.job_card_planning.frappe.get_all",
			side_effect=self._jc_get_all({"svc-a": "JC-011"}),
		):
			with self.assertRaises(Exception) as ctx:
				validate_no_new_links_to_locked_services(current)
		self.assertIn("JC-011", str(ctx.exception))

	def test_validate_allows_edit_when_unlocked(self):
		before = _LockRO(
			"RO-LOCK-6",
			[
				_LockChargeRow("svc-a", "Service", "PMS", qty=1, idx=1),
			],
		)
		current = _LockRO(
			"RO-LOCK-6",
			[
				_LockChargeRow("svc-a", "Service", "PMS", qty=5, idx=1),
			],
		)
		current._before = before

		with patch("autods.service.job_card_planning.frappe.get_all", return_value=[]):
			validate_charges_not_locked(current)

	def test_get_locked_includes_linked_overhead(self):
		ro = _LockRO(
			"RO-LOCK-7",
			[
				_LockChargeRow("svc-a", "Service", "PMS", idx=1),
				_LockChargeRow(
					"oh-1",
					"Overhead",
					"MISC",
					service_row="1: PMS",
					parent_service_charge="svc-a",
					idx=2,
				),
				_LockChargeRow("svc-b", "Service", "Camera", idx=3),
				_LockChargeRow(
					"oh-2",
					"Overhead",
					"FEE",
					service_row="2: Camera",
					parent_service_charge="svc-b",
					idx=4,
				),
			],
		)
		with patch(
			"autods.service.job_card_planning.frappe.get_all",
			side_effect=self._jc_get_all({"svc-a": "JC-020"}),
		):
			locked = get_locked_charge_row_names(ro)

		self.assertEqual(locked.get("svc-a"), "JC-020")
		self.assertEqual(locked.get("oh-1"), "JC-020")
		self.assertNotIn("svc-b", locked)
		self.assertNotIn("oh-2", locked)

	def test_validate_blocks_warehouse_edit_on_locked_row(self):
		before = _LockRO(
			"RO-LOCK-8",
			[
				_LockChargeRow(
					"sp-1",
					"Spareparts",
					"OIL",
					parent_service_charge="svc-a",
					warehouse="Stores - A",
					idx=1,
				),
				_LockChargeRow("svc-a", "Service", "PMS", idx=2),
			],
		)
		current = _LockRO(
			"RO-LOCK-8",
			[
				_LockChargeRow(
					"sp-1",
					"Spareparts",
					"OIL",
					parent_service_charge="svc-a",
					warehouse="Stores - B",
					idx=1,
				),
				_LockChargeRow("svc-a", "Service", "PMS", idx=2),
			],
		)
		current._before = before

		with patch(
			"autods.service.job_card_planning.frappe.get_all",
			side_effect=self._jc_get_all({"svc-a": "JC-021"}),
		):
			with self.assertRaises(Exception) as ctx:
				validate_charges_not_locked(current)
		self.assertIn("JC-021", str(ctx.exception))

	def test_validate_blocks_bill_to_edit_on_locked_row(self):
		before = _LockRO(
			"RO-LOCK-9",
			[
				_LockChargeRow("svc-a", "Service", "PMS", bill_to="CUST-A", idx=1),
			],
		)
		current = _LockRO(
			"RO-LOCK-9",
			[
				_LockChargeRow("svc-a", "Service", "PMS", bill_to="CUST-B", idx=1),
			],
		)
		current._before = before

		with patch(
			"autods.service.job_card_planning.frappe.get_all",
			side_effect=self._jc_get_all({"svc-a": "JC-022"}),
		):
			with self.assertRaises(Exception) as ctx:
				validate_charges_not_locked(current)
		self.assertIn("JC-022", str(ctx.exception))


if __name__ == "__main__":
	unittest.main()
