# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import unittest

from autods.service.shop_status import OPEN_SHOP_STATUSES, normalize_shop_status


class TestShopStatus(unittest.TestCase):
	def test_legacy_estimate_statuses_map_to_shop_status(self):
		assert normalize_shop_status("Draft") == "Open"
		assert normalize_shop_status("Submitted") == "Open"
		assert normalize_shop_status("Approved") == "Open"
		assert normalize_shop_status("Rejected") == "Cancelled"
		assert normalize_shop_status("Converted to RO") == "Open"

	def test_blank_and_unknown_default_to_open(self):
		assert normalize_shop_status(None) == "Open"
		assert normalize_shop_status("") == "Open"
		assert normalize_shop_status("Something Else") == "Open"

	def test_shop_statuses_are_unchanged(self):
		for status in OPEN_SHOP_STATUSES:
			assert normalize_shop_status(status) == status
		assert normalize_shop_status("Completed") == "Completed"
		assert normalize_shop_status("Cancelled") == "Cancelled"
