# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from autods.principal_portal.permissions import (
	apply_party_filters,
	get_permission_query_conditions_for_order,
	has_permission_transaction,
)
from autods.principal_portal.sync import METHOD_BY_EVENT, build_payload, inbound_guard, set_inbound_guard
from autods.principal_portal.utils import CLAIM_STATUSES, ORDER_STATUSES, ROLES


class DummyDoc:
	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)

	def get(self, key, default=None):
		return getattr(self, key, default)


class TestPortalConstants(unittest.TestCase):
	def test_roles_and_statuses(self):
		self.assertIn("Portal Sync User", ROLES)
		self.assertIn("Submitted", ORDER_STATUSES)
		self.assertIn("Settled", CLAIM_STATUSES)

	def test_method_map(self):
		self.assertEqual(METHOD_BY_EVENT[("Principal Order", "submit")], "upsert_principal_order")
		self.assertEqual(METHOD_BY_EVENT[("Warranty Claim", "status")], "update_warranty_claim_status")
		self.assertEqual(METHOD_BY_EVENT[("Dealer Circular", "circular")], "publish_circular")


class TestSyncPayload(unittest.TestCase):
	@patch("autods.principal_portal.sync.get_party_code", return_value="DEALER-001")
	def test_build_order_payload(self, _code):
		doc = DummyDoc(
			doctype="Principal Order",
			name="POR-0001",
			status="Submitted",
			principal_code="OEM-1",
			dealer_code="DEALER-001",
			principal="OEM-1",
			dealer="DEALER-001",
			order_date="2026-09-16",
			order_type="Parts",
			net_total=100,
			vin="VIN1",
			chassis_number="CH1",
			items=[
				DummyDoc(
					item_code="P1",
					item_name="Filter",
					description="",
					qty=2,
					rate=50,
					amount=100,
					delivered_qty=0,
				)
			],
		)
		payload = build_payload(doc, "submit")
		self.assertEqual(payload["origin_site"], "DEALER-001")
		self.assertEqual(payload["origin_name"], "POR-0001")
		self.assertEqual(payload["items"][0]["item_code"], "P1")
		self.assertEqual(payload["principal_code"], "OEM-1")

	def test_inbound_guard(self):
		import frappe

		set_inbound_guard(False)
		self.assertFalse(inbound_guard())
		set_inbound_guard(True)
		self.assertTrue(inbound_guard())
		set_inbound_guard(False)


class TestPermissions(unittest.TestCase):
	@patch("autods.principal_portal.permissions.user_roles", return_value={"Dealer Portal User"})
	@patch("autods.principal_portal.permissions.get_user_dealer", return_value="D-1")
	@patch("autods.principal_portal.permissions.is_system_manager", return_value=False)
	@patch("autods.principal_portal.permissions.get_site_role", return_value="Principal")
	def test_dealer_user_query_and_has_permission(self, *_args):
		condition = get_permission_query_conditions_for_order("dealer@example.com")
		self.assertIn("dealer", condition)
		allowed = DummyDoc(dealer="D-1", principal="P-1")
		denied = DummyDoc(dealer="OTHER", principal="P-1")
		self.assertTrue(has_permission_transaction(allowed, user="dealer@example.com"))
		self.assertFalse(has_permission_transaction(denied, user="dealer@example.com"))

	@patch("autods.principal_portal.permissions.user_roles", return_value={"Dealers Portal User"})
	@patch("autods.principal_portal.permissions.is_system_manager", return_value=False)
	def test_principal_staff_unrestricted(self, *_args):
		self.assertEqual(get_permission_query_conditions_for_order("staff@example.com"), "")
		self.assertEqual(apply_party_filters({"docstatus": 1}, user="staff@example.com")["docstatus"], 1)


class TestWarrantyFromRepairOrder(unittest.TestCase):
	def test_warranty_rows_from_charges(self):
		from autods.principal_portal.doctype.warranty_claim.warranty_claim import _warranty_charge_rows

		ro = DummyDoc(
			charges=[
				DummyDoc(bill_type="Customer", item="A"),
				DummyDoc(bill_type="Warranty", item="B", qty=1, amount=10, item_name="Pad"),
			],
			services=[],
			spareparts=[],
			overhead=[],
		)
		rows = _warranty_charge_rows(ro)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].item, "B")


class TestHandshakeMismatch(unittest.TestCase):
	def test_party_code_mismatch_message(self):
		from autods.principal_portal.doctype.portal_connection.portal_connection import PortalConnection

		conn = MagicMock()
		conn.party_code = "OEM-1"
		with patch(
			"autods.principal_portal.sync.handshake",
			return_value={"party_code": "OTHER", "site_role": "Principal"},
		):
			with patch(
				"autods.principal_portal.doctype.portal_connection.portal_connection.frappe"
			) as frappe_mod:
				frappe_mod.throw.side_effect = Exception("mismatch")
				with self.assertRaises(Exception):
					PortalConnection.test_connection(conn)


class TestLoopGuard(unittest.TestCase):
	@patch("autods.principal_portal.sync.frappe.enqueue")
	def test_enqueue_skipped_when_inbound(self, enqueue):
		set_inbound_guard(True)
		from autods.principal_portal.sync import enqueue_sync

		enqueue_sync(DummyDoc(doctype="Principal Order", name="x"), "submit")
		enqueue.assert_not_called()
		set_inbound_guard(False)


class TestApiIdempotency(unittest.TestCase):
	@patch("autods.principal_portal.api.frappe")
	def test_find_by_origin_prefers_remote_keys(self, frappe_mod):
		from autods.principal_portal import api

		frappe_mod.db.get_value.return_value = "LOCAL-1"
		self.assertEqual(api._find_by_origin("Principal Order", "OEM", "POR-1"), "LOCAL-1")
		frappe_mod.db.get_value.assert_called()
