# Copyright (c) 2026, Agilasoft Technologies Inc. and Contributors
# See license.txt

import unittest
from unittest.mock import MagicMock, patch

from autods.service.doctype.job_card.job_card import (
	JobCard,
	_filter_material_request_payloads,
	_filter_spareparts_not_yet_requested,
	_item_codes_already_requested,
	_link_material_request_to_spareparts_rows,
	_merge_payloads_with_unlinked_jc_rows,
	_mr_items_from_unlinked_jc_rows,
	_split_charge_row_names,
	_unlinked_spareparts_request_rows,
	charge_row_to_jc_spareparts_request_row,
)
from autods.service.test_charge_service_row import _MockRO, _Row


class TestJobCardSparepartsPopulate(unittest.TestCase):
	def _make_ro(self):
		rows = [
			_Row("svc-a", "Service", item="SVC-1"),
			_Row("svc-b", "Service", item="SVC-2"),
			_Row("p1", "Spareparts", "1", item="PART-A"),
			_Row("p2", "Spareparts", "1: Oil filter", item="PART-B"),
			_Row("p3", "Spareparts", "2", item="PART-C"),
		]
		for row in rows[2:]:
			row.item_name = row.item
			row.qty = 1
			row.uom = "Nos"
		return _MockRO(rows)

	def _jc_mock(self, **kwargs):
		jc = MagicMock(spec=JobCard)
		jc.repair_order = kwargs.get("repair_order")
		jc.service_charge_row = kwargs.get("service_charge_row")
		jc.technician = kwargs.get("technician")
		jc.spareparts_requests = kwargs.get("spareparts_requests") or []
		jc.append = MagicMock()
		return jc

	def test_charge_row_to_jc_spareparts_request_row_maps_fields(self):
		row = _Row("p1", "Spareparts", "1", item="PART-A")
		row.item_name = "Part A"
		row.qty = 2
		row.uom = "Nos"

		with patch(
			"autods.service.doctype.job_card.job_card.now",
			return_value="2026-06-29 10:00:00",
		):
			mapped = charge_row_to_jc_spareparts_request_row(row, technician="EMP-001")

		self.assertEqual(
			mapped,
			{
				"item_code": "PART-A",
				"item_name": "Part A",
				"qty": 2.0,
				"uom": "Nos",
				"requested_by": "EMP-001",
				"requested_date": "2026-06-29 10:00:00",
				"status": "Requested",
			},
		)

	def test_populate_spareparts_from_charges_scoped_to_service_line(self):
		ro = self._make_ro()
		jc = self._jc_mock(
			repair_order="RO-001",
			service_charge_row="svc-a",
			technician="EMP-001",
		)

		with patch(
			"autods.service.doctype.job_card.job_card.now",
			return_value="2026-06-29 10:00:00",
		):
			JobCard.populate_spareparts_from_charges(jc, ro=ro)

		self.assertEqual(jc.append.call_count, 2)
		items = [call.args[1]["item_code"] for call in jc.append.call_args_list]
		self.assertEqual(items, ["PART-A", "PART-B"])

	def test_populate_spareparts_from_charges_populates_all_without_service_charge_row(self):
		jc = self._jc_mock(repair_order="RO-001")
		JobCard.populate_spareparts_from_charges(jc, ro=self._make_ro())
		self.assertEqual(jc.append.call_count, 3)

	def test_populate_spareparts_from_charges_skips_without_repair_order(self):
		jc = self._jc_mock(service_charge_row="svc-a")
		JobCard.populate_spareparts_from_charges(jc, ro=self._make_ro())
		jc.append.assert_not_called()

	def test_populate_spareparts_from_charges_skips_when_rows_already_exist(self):
		jc = self._jc_mock(
			repair_order="RO-001",
			service_charge_row="svc-a",
			spareparts_requests=[{"item_code": "PART-A", "qty": 1}],
		)
		JobCard.populate_spareparts_from_charges(jc, ro=self._make_ro())
		jc.append.assert_not_called()


class TestLinkMaterialRequestToSparepartsRows(unittest.TestCase):
	def _row(self, item_code, material_request=None):
		row = MagicMock()
		row.item_code = item_code
		row.material_request = material_request
		return row

	def test_links_matching_empty_rows_only(self):
		row_a = self._row("PART-A")
		row_b = self._row("PART-B")
		row_c = self._row("PART-C", material_request="MAT-MR-OLD")
		row_d = self._row("PART-D")
		job_doc = MagicMock()
		job_doc.spareparts_requests = [row_a, row_b, row_c, row_d]

		with patch(
			"autods.service.doctype.job_card.job_card.frappe.get_doc",
			return_value=job_doc,
		):
			_link_material_request_to_spareparts_rows(
				"JC-001",
				"MAT-MR-NEW",
				{"PART-A", "PART-C", "PART-D"},
			)

		self.assertEqual(row_a.material_request, "MAT-MR-NEW")
		self.assertIsNone(row_b.material_request)
		self.assertEqual(row_c.material_request, "MAT-MR-OLD")
		self.assertEqual(row_d.material_request, "MAT-MR-NEW")
		job_doc.save.assert_called_once_with(ignore_permissions=True)

	def test_skips_save_when_nothing_to_link(self):
		row = self._row("PART-A", material_request="MAT-MR-OLD")
		job_doc = MagicMock()
		job_doc.spareparts_requests = [row]

		with patch(
			"autods.service.doctype.job_card.job_card.frappe.get_doc",
			return_value=job_doc,
		):
			_link_material_request_to_spareparts_rows("JC-001", "MAT-MR-NEW", {"PART-A"})

		self.assertEqual(row.material_request, "MAT-MR-OLD")
		job_doc.save.assert_not_called()

	def test_noop_without_item_codes(self):
		with patch("autods.service.doctype.job_card.job_card.frappe.get_doc") as get_doc:
			_link_material_request_to_spareparts_rows("JC-001", "MAT-MR-NEW", set())
			get_doc.assert_not_called()


class TestAlreadyRequestedMaterialRequestGuard(unittest.TestCase):
	def _row(self, item_code, material_request=None, name=None, qty=1, uom="Nos", item_name=None):
		row = MagicMock()
		row.item_code = item_code
		row.material_request = material_request
		row.name = name or f"jcsp-{item_code}"
		row.qty = qty
		row.uom = uom
		row.item_name = item_name or item_code
		return row

	def _jc(self, rows):
		jc = MagicMock()
		jc.spareparts_requests = rows
		return jc

	def _charge(self, item):
		row = MagicMock()
		row.item = item
		row.qty = 1
		row.uom = "Nos"
		row.warehouse = None
		return row

	def test_item_codes_already_requested_linked_only(self):
		jc = self._jc([
			self._row("PART-A", material_request="MAT-1"),
			self._row("PART-B", material_request="MAT-1"),
		])
		self.assertEqual(_item_codes_already_requested(jc), {"PART-A", "PART-B"})

	def test_item_codes_already_requested_excludes_when_unlinked_row_exists(self):
		jc = self._jc([
			self._row("PART-A", material_request="MAT-1"),
			self._row("PART-A", material_request=None, name="jcsp-PART-A-2"),
			self._row("PART-B", material_request="MAT-1"),
		])
		self.assertEqual(_item_codes_already_requested(jc), {"PART-B"})

	def test_item_codes_already_requested_empty_when_all_unlinked(self):
		jc = self._jc([self._row("PART-A"), self._row("PART-B")])
		self.assertEqual(_item_codes_already_requested(jc), set())

	def test_unlinked_spareparts_request_rows(self):
		linked = self._row("PART-A", material_request="MAT-1")
		unlinked = self._row("PART-B")
		jc = self._jc([linked, unlinked])
		self.assertEqual(_unlinked_spareparts_request_rows(jc), [unlinked])

	def test_filter_spareparts_drops_already_requested_items(self):
		jc = self._jc([
			self._row("PART-A", material_request="MAT-1"),
			self._row("PART-B"),
		])
		spareparts = [self._charge("PART-A"), self._charge("PART-B"), self._charge("PART-C")]
		filtered = _filter_spareparts_not_yet_requested(spareparts, jc)
		self.assertEqual([r.item for r in filtered], ["PART-B", "PART-C"])

	def test_filter_spareparts_keeps_item_when_new_unlinked_row_added(self):
		jc = self._jc([
			self._row("PART-A", material_request="MAT-1"),
			self._row("PART-A", material_request=None, name="jcsp-PART-A-2"),
		])
		spareparts = [self._charge("PART-A")]
		filtered = _filter_spareparts_not_yet_requested(spareparts, jc)
		self.assertEqual([r.item for r in filtered], ["PART-A"])

	def test_filter_material_request_payloads(self):
		jc = self._jc([self._row("PART-A", material_request="MAT-1")])
		payloads = [
			{"name": "p1", "item_code": "PART-A"},
			{"name": "p2", "item_code": "PART-B"},
		]
		self.assertEqual(
			_filter_material_request_payloads(payloads, jc),
			[{"name": "p2", "item_code": "PART-B"}],
		)

	def test_merge_payloads_adds_jc_only_unlinked_rows(self):
		jc = self._jc([self._row("PART-NEW", name="jcsp-new", qty=3, item_name="New Part")])
		merged = _merge_payloads_with_unlinked_jc_rows(
			[{"name": "p1", "item_code": "PART-A"}],
			jc,
		)
		self.assertEqual(len(merged), 2)
		self.assertEqual(merged[1]["name"], "jc:jcsp-new")
		self.assertEqual(merged[1]["item_code"], "PART-NEW")
		self.assertEqual(merged[1]["qty"], 3.0)

	def test_merge_payloads_skips_unlinked_item_already_in_payloads(self):
		jc = self._jc([self._row("PART-A")])
		merged = _merge_payloads_with_unlinked_jc_rows(
			[{"name": "p1", "item_code": "PART-A"}],
			jc,
		)
		self.assertEqual(len(merged), 1)

	def test_split_charge_row_names(self):
		ro_names, jc_names = _split_charge_row_names(["p1", "jc:jcsp-1", "p2"])
		self.assertEqual(ro_names, ["p1", "p2"])
		self.assertEqual(jc_names, ["jcsp-1"])

	def test_split_charge_row_names_none(self):
		self.assertEqual(_split_charge_row_names(None), (None, None))

	def test_mr_items_from_unlinked_jc_rows_skips_covered(self):
		jc = self._jc([
			self._row("PART-A", qty=2),
			self._row("PART-NEW", name="jcsp-new", qty=5, uom="Box"),
		])
		items = _mr_items_from_unlinked_jc_rows(jc, covered_item_codes={"PART-A"})
		self.assertEqual(len(items), 1)
		self.assertEqual(items[0].item, "PART-NEW")
		self.assertEqual(items[0].qty, 5.0)
		self.assertEqual(items[0].uom, "Box")


class TestJobCardUniquePerServiceLine(unittest.TestCase):
	def _jc(self, **kwargs):
		jc = JobCard.__new__(JobCard)
		jc.name = kwargs.get("name", "JC-NEW")
		jc.repair_order = kwargs.get("repair_order", "RO-001")
		jc.service_charge_row = kwargs.get("service_charge_row", "")
		jc.status = kwargs.get("status", "Open")
		return jc

	def test_allows_multiple_job_cards_on_same_ro_for_different_service_lines(self):
		jc = self._jc(service_charge_row="svc-b")
		with patch("autods.service.doctype.job_card.job_card.frappe.get_all", return_value=[]):
			JobCard.validate_unique_job_card_per_service_line(jc)

	def test_blocks_duplicate_job_card_for_same_service_line(self):
		jc = self._jc(service_charge_row="svc-a")
		with patch(
			"autods.service.doctype.job_card.job_card.frappe.get_all",
			return_value=["JC-00001"],
		), self.assertRaises(Exception):
			JobCard.validate_unique_job_card_per_service_line(jc)

	def test_blocks_second_legacy_consolidated_job_card(self):
		jc = self._jc(service_charge_row="")
		with patch(
			"autods.service.doctype.job_card.job_card.frappe.get_all",
			return_value=["JC-LEGACY"],
		), self.assertRaises(Exception):
			JobCard.validate_unique_job_card_per_service_line(jc)


class TestJobCardClose(unittest.TestCase):
	def _work_detail(self, status="Pending"):
		row = MagicMock()
		row.status = status
		return row

	def test_mark_completed_for_close_updates_status_work_rows_and_timestamps(self):
		jc = MagicMock(spec=JobCard)
		jc.status = "Work In Progress"
		jc.actual_completion_date = None
		jc.end_time = None
		jc.work_details = [self._work_detail("Pending"), self._work_detail("Completed")]

		with patch(
			"autods.service.doctype.job_card.job_card.now",
			return_value="2026-07-04 16:00:00",
		):
			JobCard.mark_completed_for_close(jc)

		self.assertEqual(jc.status, "Completed")
		self.assertEqual(jc.actual_completion_date, "2026-07-04 16:00:00")
		self.assertEqual(jc.end_time, "2026-07-04 16:00:00")
		self.assertEqual(jc.work_details[0].status, "Completed")
		self.assertEqual(jc.work_details[1].status, "Completed")

	def test_before_submit_marks_job_card_completed(self):
		jc = MagicMock(spec=JobCard)
		jc.status = "Open"
		jc.work_details = [self._work_detail("Pending")]

		with patch.object(JobCard, "mark_completed_for_close") as mark_completed:
			JobCard.before_submit(jc)
			mark_completed.assert_called_once_with()
