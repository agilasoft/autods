# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import sys
import types
import unittest
from unittest.mock import patch


def _install_frappe_stubs():
	if "frappe" in sys.modules:
		return

	frappe = types.ModuleType("frappe")
	frappe.db = types.SimpleNamespace(
		get_value=lambda *args, **kwargs: None,
		exists=lambda *args, **kwargs: True,
	)
	frappe.bold = lambda value: value
	frappe.throw = lambda message, *args, **kwargs: (_ for _ in ()).throw(Exception(message))

	def _(message):
		return message

	sys.modules["frappe"] = frappe
	sys.modules["frappe._"] = _


_install_frappe_stubs()

from autods.service.gate_pass_utils import (
	is_exit_gate_pass,
	require_completed_job_cards_for_exit,
)


class _ValidationError(Exception):
	pass


class TestGatePassUtils(unittest.TestCase):
	def test_is_exit_gate_pass(self):
		self.assertTrue(is_exit_gate_pass(gate_pass_type="Exit", status="Entry Only"))
		self.assertTrue(is_exit_gate_pass(gate_pass_type="Both", status="Completed"))
		self.assertTrue(is_exit_gate_pass(gate_pass_type="Both", status="Exit Only"))
		self.assertFalse(is_exit_gate_pass(gate_pass_type="Both", status="Entry Only"))
		self.assertFalse(is_exit_gate_pass(gate_pass_type="Entry", status="Entry Only"))

	@patch("autods.service.gate_pass_utils.get_open_job_cards_for_repair_order", return_value=[])
	@patch("autods.service.gate_pass_utils.frappe.db.get_value")
	@patch("autods.service.gate_pass_utils.frappe.db.exists", return_value=True)
	def test_require_completed_job_cards_for_exit_linked_job_card(self, _exists, get_value, _open_cards):
		get_value.side_effect = lambda doctype, name, field: {
			("Job Card", "JC-WIP", "status"): "Work In Progress",
			("Job Card", "JC-WIP", "repair_order"): "RO-001",
			("Job Card", "JC-DONE", "status"): "Completed",
			("Job Card", "JC-DONE", "repair_order"): "RO-001",
		}.get((doctype, name, field))

		with patch("autods.service.gate_pass_utils.frappe.throw", side_effect=_ValidationError):
			with self.assertRaises(_ValidationError):
				require_completed_job_cards_for_exit(job_card="JC-WIP", repair_order="RO-001")

		require_completed_job_cards_for_exit(job_card="JC-DONE", repair_order="RO-001")

	@patch("autods.service.gate_pass_utils.get_open_job_cards_for_repair_order")
	@patch("autods.service.gate_pass_utils.frappe.throw", side_effect=_ValidationError)
	def test_require_completed_job_cards_for_exit_open_repair_order(self, throw, open_cards):
		open_cards.return_value = [{"name": "JC-WIP", "status": "Work In Progress"}]

		with self.assertRaises(_ValidationError):
			require_completed_job_cards_for_exit(repair_order="RO-001")

	@patch("autods.service.gate_pass_utils.frappe.throw", side_effect=_ValidationError)
	def test_require_completed_job_cards_for_exit_requires_link(self, throw):
		with self.assertRaises(_ValidationError):
			require_completed_job_cards_for_exit()

	@patch("autods.service.gate_pass_utils.get_open_job_cards_for_repair_order", return_value=[])
	@patch("autods.service.gate_pass_utils.frappe.db.exists", return_value=True)
	def test_require_completed_job_cards_resolves_repair_order_from_job_card(self, _exists, open_cards):
		def get_value(doctype, name, field):
			if field == "status":
				return "Completed"
			if field == "repair_order":
				return "RO-001"
			return None

		with patch("autods.service.gate_pass_utils.frappe.db.get_value", side_effect=get_value):
			require_completed_job_cards_for_exit(job_card="JC-DONE")
		open_cards.assert_called_once_with("RO-001")

	@patch("autods.service.gate_pass_utils.get_open_job_cards_for_repair_order", return_value=[])
	@patch("autods.service.gate_pass_utils.frappe.db.get_value", return_value="Completed")
	@patch("autods.service.gate_pass_utils.frappe.db.exists", return_value=False)
	@patch("autods.service.gate_pass_utils.frappe.throw", side_effect=_ValidationError)
	def test_require_completed_job_cards_missing_job_card(self, throw, _exists, _get_value, _open_cards):
		with self.assertRaises(_ValidationError):
			require_completed_job_cards_for_exit(job_card="JC-MISSING")


if __name__ == "__main__":
	unittest.main()
