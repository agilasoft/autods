# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import unittest

from autods.vehicle_sales.quote_status import (
	quote_status_after_order_cancel,
	quote_status_after_order_submit,
	validate_lost_reason,
)


class TestQuoteStatus(unittest.TestCase):
	def test_submit_marks_open_quote_ordered(self):
		assert quote_status_after_order_submit("Open") == "Ordered"
		assert quote_status_after_order_submit("Expired") == "Ordered"
		assert quote_status_after_order_submit("Draft") == "Ordered"

	def test_submit_does_not_revive_lost_or_cancelled(self):
		assert quote_status_after_order_submit("Lost") == "Lost"
		assert quote_status_after_order_submit("Cancelled") == "Cancelled"

	def test_cancel_reopens_only_when_no_other_order_remains(self):
		assert quote_status_after_order_cancel("Ordered", 0) == "Open"
		assert quote_status_after_order_cancel("Ordered", 1) == "Ordered"
		assert quote_status_after_order_cancel("Lost", 0) == "Lost"

	def test_lost_reason_is_trimmed(self):
		assert validate_lost_reason("  price  ") == "price"
		assert validate_lost_reason("   ") == ""
