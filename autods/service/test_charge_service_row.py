# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import unittest

from autods.service.charge_service_row import (
	service_line_index_for_charge_row_name,
	sparepart_rows_for_material_request,
)


class _Row:
	def __init__(self, name, service_item_type, service_row=None, item="ITEM"):
		self.name = name
		self.service_item_type = service_item_type
		self.service_row = service_row
		self.item = item


class _MockRO:
	def __init__(self, charges):
		self.charges = charges


class TestChargeServiceRow(unittest.TestCase):
	def test_service_line_index_for_charge_row_name(self):
		ro = _MockRO(
			[
				_Row("svc-a", "Service"),
				_Row("svc-b", "Service"),
			]
		)
		self.assertEqual(service_line_index_for_charge_row_name(ro, "svc-a"), 1)
		self.assertEqual(service_line_index_for_charge_row_name(ro, "svc-b"), 2)
		self.assertIsNone(service_line_index_for_charge_row_name(ro, "missing"))
		self.assertIsNone(service_line_index_for_charge_row_name(ro, None))

	def test_sparepart_rows_scoped_and_explicit(self):
		ro = _MockRO(
			[
				_Row("svc-a", "Service"),
				_Row("svc-b", "Service"),
				_Row("p1", "Spareparts", "1"),
				_Row("p2", "Spareparts", "1: Oil filter"),
				_Row("p3", "Spareparts", "2"),
			]
		)
		scoped = sparepart_rows_for_material_request(ro, "svc-a", None)
		self.assertEqual({r.name for r in scoped}, {"p1", "p2"})
		scoped_b = sparepart_rows_for_material_request(ro, "svc-b", None)
		self.assertEqual({r.name for r in scoped_b}, {"p3"})
		explicit = sparepart_rows_for_material_request(ro, None, ["p3", "p1"])
		self.assertEqual({r.name for r in explicit}, {"p1", "p3"})
		all_parts = sparepart_rows_for_material_request(ro, None, None)
		self.assertEqual({r.name for r in all_parts}, {"p1", "p2", "p3"})
