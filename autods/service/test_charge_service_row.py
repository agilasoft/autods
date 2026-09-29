# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import unittest

from autods.service.charge_service_row import (
	bind_charge_service_link,
	resolve_charge_parent_service_links,
	service_line_index_for_charge_row_name,
	sparepart_linked_to_service,
	sparepart_rows_for_material_request,
	sync_service_row_label,
	validate_charge_service_links,
)


class _Row:
	def __init__(
		self,
		name,
		service_item_type,
		service_row=None,
		parent_service_charge=None,
		item="ITEM",
		item_name=None,
	):
		self.name = name
		self.service_item_type = service_item_type
		self.service_row = service_row
		self.parent_service_charge = parent_service_charge
		self.item = item
		self.item_name = item_name


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

	def test_sparepart_rows_scoped_by_index_legacy(self):
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

	def test_sparepart_rows_scoped_by_parent_service_charge(self):
		ro = _MockRO(
			[
				_Row("svc-a", "Service", item="A"),
				_Row("svc-b", "Service", item="B"),
				_Row("p1", "Spareparts", "2: B", parent_service_charge="svc-b"),
				_Row("p2", "Spareparts", "1: A", parent_service_charge="svc-a"),
			]
		)
		scoped = sparepart_rows_for_material_request(ro, "svc-b", None)
		self.assertEqual({r.name for r in scoped}, {"p1"})
		# Reorder should not affect stable link: svc-b is still second in list but p1 stays on svc-b
		ro.charges = [
			ro.charges[1],
			ro.charges[0],
			ro.charges[2],
			ro.charges[3],
		]
		scoped_after_reorder = sparepart_rows_for_material_request(ro, "svc-b", None)
		self.assertEqual({r.name for r in scoped_after_reorder}, {"p1"})

	def test_sparepart_rows_explicit_and_all(self):
		ro = _MockRO(
			[
				_Row("svc-a", "Service"),
				_Row("p1", "Spareparts", "1", parent_service_charge="svc-a"),
				_Row("p2", "Spareparts", "1", parent_service_charge="svc-a"),
				_Row("p3", "Spareparts", "1", parent_service_charge="svc-a"),
			]
		)
		explicit = sparepart_rows_for_material_request(ro, None, ["p3", "p1"])
		self.assertEqual({r.name for r in explicit}, {"p1", "p3"})
		all_parts = sparepart_rows_for_material_request(ro, None, None)
		self.assertEqual({r.name for r in all_parts}, {"p1", "p2", "p3"})

	def test_sparepart_linked_to_service_prefers_parent(self):
		spare = _Row("p1", "Spareparts", "1: A", parent_service_charge="svc-b")
		self.assertTrue(sparepart_linked_to_service(spare, "svc-b", 1))
		self.assertFalse(sparepart_linked_to_service(spare, "svc-a", 1))

	def test_resolve_charge_parent_service_links_from_index(self):
		doc = _MockRO(
			[
				_Row("svc-a", "Service", item="Oil change", item_name="Oil change"),
				_Row("p1", "Spareparts", "1"),
			]
		)
		resolve_charge_parent_service_links(doc)
		self.assertEqual(doc.charges[1].parent_service_charge, "svc-a")
		self.assertEqual(doc.charges[1].service_row, "1: Oil change")

	def test_sync_service_row_label_after_service_rename(self):
		doc = _MockRO(
			[
				_Row("svc-a", "Service", item="OLD", item_name="New label"),
				_Row("p1", "Spareparts", "1: OLD", parent_service_charge="svc-a"),
			]
		)
		sync_service_row_label(doc, doc.charges[1])
		self.assertEqual(doc.charges[1].service_row, "1: New label")

	def test_validate_charge_service_links_rebinds_stale_parent(self):
		doc = _MockRO(
			[
				_Row("svc-a", "Service", item="Oil", item_name="Oil"),
				_Row(
					"p1",
					"Spareparts",
					"1: Oil",
					parent_service_charge="new-repair-estimate-charges-stale",
				),
			]
		)
		validate_charge_service_links(doc)
		self.assertEqual(doc.charges[1].parent_service_charge, "svc-a")
		self.assertEqual(doc.charges[1].service_row, "1: Oil")

	def test_bind_charge_service_link_rebinds_from_index(self):
		services = [_Row("svc-a", "Service", item="Brake", item_name="Brake")]
		spare = _Row("p1", "Spareparts", "1: Old label", parent_service_charge="stale-name")
		bind_charge_service_link(spare, services, 1)
		self.assertEqual(spare.parent_service_charge, "svc-a")
		self.assertEqual(spare.service_row, "1: Brake")

	def test_bind_prefers_valid_parent_over_stale_ordinal(self):
		services = [
			_Row("svc-a", "Service", item="A", item_name="A"),
			_Row("svc-b", "Service", item="B", item_name="B"),
		]
		# Stale label says service 1, but stable parent is svc-b.
		spare = _Row("p1", "Spareparts", "1: A", parent_service_charge="svc-b")
		bind_charge_service_link(spare, services, 2)
		self.assertEqual(spare.parent_service_charge, "svc-b")
		self.assertEqual(spare.service_row, "2: B")

	def test_validate_prefers_valid_parent_after_service_reorder(self):
		# Reordered services: svc-b first, svc-a second. Spare still has stale "2: B"
		# label but valid parent svc-b — must stay on svc-b and refresh label to "1: B".
		doc = _MockRO(
			[
				_Row("svc-b", "Service", item="B", item_name="B"),
				_Row("svc-a", "Service", item="A", item_name="A"),
				_Row("p1", "Spareparts", "2: B", parent_service_charge="svc-b"),
			]
		)
		validate_charge_service_links(doc)
		self.assertEqual(doc.charges[2].parent_service_charge, "svc-b")
		self.assertEqual(doc.charges[2].service_row, "1: B")

	def test_resolve_refreshes_label_from_valid_parent_without_service_row(self):
		doc = _MockRO(
			[
				_Row("svc-a", "Service", item="Oil", item_name="Oil"),
				_Row("p1", "Spareparts", None, parent_service_charge="svc-a"),
			]
		)
		resolve_charge_parent_service_links(doc)
		self.assertEqual(doc.charges[1].parent_service_charge, "svc-a")
		self.assertEqual(doc.charges[1].service_row, "1: Oil")

	def test_validate_charge_service_links_resolves_legacy_index(self):
		doc = _MockRO(
			[
				_Row("svc-a", "Service", item="Brake", item_name="Brake"),
				_Row("p1", "Spareparts", "1"),
			]
		)
		validate_charge_service_links(doc)
		self.assertEqual(doc.charges[1].parent_service_charge, "svc-a")

	def test_validate_charge_service_links_allows_duplicate_service_items(self):
		doc = _MockRO(
			[
				_Row("svc-a", "Service", item="PMS", item_name="PMS"),
				_Row("svc-b", "Service", item="PMS", item_name="PMS"),
				_Row("p1", "Spareparts", "1"),
			]
		)
		validate_charge_service_links(doc)
		self.assertEqual(doc.charges[2].parent_service_charge, "svc-a")
		self.assertEqual(doc.charges[2].service_row, "1: PMS")
