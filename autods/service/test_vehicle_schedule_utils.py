# Copyright (c) 2026, Agilasoft Technologies Inc. and Contributors
# See license.txt

import sys
import types
import unittest
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock


def _get_datetime(val):
	if isinstance(val, datetime):
		return val
	if isinstance(val, date):
		return datetime.combine(val, datetime.min.time())
	return datetime.fromisoformat(str(val))


def _getdate(val):
	if isinstance(val, date) and not isinstance(val, datetime):
		return val
	if isinstance(val, datetime):
		return val.date()
	return datetime.fromisoformat(str(val)).date()


def _add_to_date(dt, hours=0, **kwargs):
	if kwargs:
		raise NotImplementedError("test stub supports hours only")
	return dt + timedelta(hours=hours)


frappe_utils = types.SimpleNamespace(
	get_datetime=_get_datetime,
	getdate=_getdate,
	add_to_date=_add_to_date,
)
sys.modules.setdefault("frappe", types.SimpleNamespace())
sys.modules["frappe.utils"] = frappe_utils
sys.modules["frappe"].utils = frappe_utils
sys.modules["frappe"]._ = lambda x: x
sys.modules["frappe"].bold = lambda x: x
sys.modules["frappe"].throw = MagicMock(side_effect=ValueError)
sys.modules["frappe"].db = MagicMock()

from autods.service.vehicle_schedule_utils import (
	intervals_overlap,
	job_card_schedule_window,
	schedules_conflict,
	same_schedule_start,
	service_appointment_schedule_window,
)


class TestVehicleScheduleUtils(unittest.TestCase):
	def test_intervals_overlap_when_windows_share_time(self):
		self.assertTrue(
			intervals_overlap(
				"2026-07-04 10:00:00",
				"2026-07-04 11:00:00",
				"2026-07-04 10:30:00",
				"2026-07-04 12:00:00",
			)
		)

	def test_intervals_do_not_overlap_when_sequential(self):
		self.assertFalse(
			intervals_overlap(
				"2026-07-04 09:00:00",
				"2026-07-04 10:00:00",
				"2026-07-04 10:00:00",
				"2026-07-04 11:00:00",
			)
		)

	def test_same_schedule_start_detects_identical_start(self):
		self.assertTrue(
			same_schedule_start("2026-07-04 10:00:00", "2026-07-04 10:00:00"),
		)
		self.assertFalse(
			same_schedule_start("2026-07-04 10:00:00", "2026-07-04 10:30:00"),
		)

	def test_schedules_conflict_for_identical_start_times(self):
		self.assertTrue(
			schedules_conflict(
				"2026-07-04 10:00:00",
				"2026-07-04 11:00:00",
				"2026-07-04 10:00:00",
				"2026-07-04 12:00:00",
			)
		)

	def test_job_card_schedule_window_uses_start_time_when_end_missing(self):
		doc = SimpleNamespace(
			start_time="2026-07-04 14:00:00",
			end_time=None,
			expected_completion_date=None,
			repair_date="2026-07-04",
		)
		start, end = job_card_schedule_window(doc)
		self.assertEqual(str(start), "2026-07-04 14:00:00")
		self.assertEqual(str(end), "2026-07-04 15:00:00")

	def test_job_card_schedule_window_does_not_ignore_start_time(self):
		first = SimpleNamespace(
			start_time="2026-07-04 14:00:00",
			end_time=None,
			expected_completion_date=None,
			repair_date="2026-07-04",
		)
		second = SimpleNamespace(
			start_time="2026-07-04 14:00:00",
			end_time=None,
			expected_completion_date=None,
			repair_date="2026-07-04",
		)
		start_a, end_a = job_card_schedule_window(first)
		start_b, end_b = job_card_schedule_window(second)
		self.assertTrue(schedules_conflict(start_a, end_a, start_b, end_b))

	def test_service_appointment_schedule_window_builds_datetime_range(self):
		doc = SimpleNamespace(
			appointment_date="2026-07-04",
			appointment_start_time="10:00:00",
			appointment_end_time="11:00:00",
			expected_completion_date=None,
		)
		start, end = service_appointment_schedule_window(doc)
		self.assertEqual(str(start), "2026-07-04 10:00:00")
		self.assertEqual(str(end), "2026-07-04 11:00:00")


if __name__ == "__main__":
	unittest.main()
