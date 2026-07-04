# Copyright (c) 2026, Agilasoft Technologies Inc. and Contributors
# See license.txt

import unittest
from unittest.mock import MagicMock, patch

from autods.service.doctype.job_card.job_card import (
	JobCard,
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

	def test_populate_spareparts_from_charges_skips_without_service_charge_row(self):
		jc = self._jc_mock(repair_order="RO-001")
		JobCard.populate_spareparts_from_charges(jc, ro=self._make_ro())
		jc.append.assert_not_called()

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
