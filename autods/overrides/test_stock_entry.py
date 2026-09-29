# Copyright (c) 2026, Agilasoft Technologies Inc. and Contributors
# See license.txt

import unittest
from unittest.mock import MagicMock, patch

import frappe

from autods.overrides.stock_entry import (
	StockEntryOverride,
	_spareparts_rows_to_issue,
	apply_service_job_card_material_issue,
	is_service_job_card,
	on_cancel,
	on_submit,
)


class TestIsServiceJobCard(unittest.TestCase):
	def test_false_when_missing(self):
		self.assertFalse(is_service_job_card(None))
		self.assertFalse(is_service_job_card(""))

	@patch("autods.overrides.stock_entry.frappe")
	def test_true_when_meta_has_spareparts_requests(self, frappe_mod):
		frappe_mod.db.exists.return_value = True
		meta = MagicMock()
		meta.has_field.return_value = True
		frappe_mod.get_meta.return_value = meta
		self.assertTrue(is_service_job_card("JC-1"))
		meta.has_field.assert_called_with("spareparts_requests")

	@patch("autods.overrides.stock_entry.frappe")
	def test_false_when_job_card_missing(self, frappe_mod):
		frappe_mod.db.exists.return_value = False
		self.assertFalse(is_service_job_card("JC-MISSING"))


class TestApplyServiceJobCardMaterialIssue(unittest.TestCase):
	def test_sets_material_issue_and_clears_manufacture_fields(self):
		doc = frappe._dict(purpose="Material Transfer for Manufacture", from_bom=1, bom_no="BOM-1")
		apply_service_job_card_material_issue(doc)
		self.assertEqual(doc.purpose, "Material Issue")
		self.assertEqual(doc.stock_entry_type, "Material Issue")
		self.assertEqual(doc.from_bom, 0)
		self.assertIsNone(doc.bom_no)
		self.assertIsNone(doc.work_order)
		self.assertEqual(doc.fg_completed_qty, 0)


class TestValidateJobCardItemSkip(unittest.TestCase):
	@patch("autods.overrides.stock_entry.is_service_job_card", return_value=True)
	def test_validate_job_card_item_is_noop_for_service_job_card(self, _is_svc):
		se = MagicMock()
		se.job_card = "JC-1"
		self.assertIsNone(StockEntryOverride.validate_job_card_item(se))

	@patch("autods.overrides.stock_entry.is_service_job_card", return_value=True)
	def test_set_job_card_data_is_noop_for_service_job_card(self, _is_svc):
		se = MagicMock()
		se.job_card = "JC-1"
		self.assertIsNone(StockEntryOverride.set_job_card_data(se))

	@patch("autods.overrides.stock_entry.is_service_job_card", return_value=True)
	@patch("autods.overrides.stock_entry.frappe")
	def test_normalize_manufacture_transfer_to_material_issue(self, frappe_mod, _is_svc):
		frappe_mod.db.get_value.return_value = "Material Issue"
		se = MagicMock()
		se.job_card = "JC-1"
		se.purpose = "Material Transfer for Manufacture"
		se.work_order = None
		se.repair_order = "RO-1"
		se.stock_entry_type = None
		se.get.return_value = [frappe._dict(material_request="MR-1")]
		StockEntryOverride._autods_normalize_purpose_for_service_job_card(se)
		self.assertEqual(se.purpose, "Material Issue")


class TestSparepartsWriteBack(unittest.TestCase):
	def test_prefers_rows_matching_material_request_on_stock_entry(self):
		issued = {"PART-A"}
		mrs = {"MR-MATCH"}
		linked = frappe._dict(
			item_code="PART-A",
			stock_entry=None,
			material_request="MR-OTHER",
			status="Approved",
		)
		match = frappe._dict(
			item_code="PART-A",
			stock_entry=None,
			material_request="MR-MATCH",
			status="Approved",
		)
		job = frappe._dict(spareparts_requests=[linked, match])
		rows = _spareparts_rows_to_issue(job, issued, mrs)
		self.assertEqual(rows, [match])

	def test_skips_rows_already_linked_to_stock_entry(self):
		row = frappe._dict(
			item_code="PART-A",
			stock_entry="STE-OLD",
			material_request="MR-1",
			status="Issued",
		)
		job = frappe._dict(spareparts_requests=[row])
		self.assertEqual(_spareparts_rows_to_issue(job, {"PART-A"}, {"MR-1"}), [])

	@patch("autods.overrides.stock_entry.frappe")
	def test_on_submit_sets_stock_entry_and_issued(self, frappe_mod):
		frappe_mod.db.exists.return_value = True
		row = frappe._dict(
			item_code="PART-A",
			status="Approved",
			stock_entry=None,
			material_request="MR-1",
		)
		job_doc = MagicMock()
		job_doc.spareparts_requests = [row]
		job_doc.flags = MagicMock()
		frappe_mod.get_doc.return_value = job_doc

		se = frappe._dict(
			job_card="JC-1",
			purpose="Material Issue",
			name="STE-1",
			items=[frappe._dict(item_code="PART-A", material_request="MR-1")],
		)
		on_submit(se)
		self.assertEqual(row.status, "Issued")
		self.assertEqual(row.stock_entry, "STE-1")
		job_doc.save.assert_called_once_with(ignore_permissions=True)

	@patch("autods.overrides.stock_entry.frappe")
	def test_on_cancel_clears_link_and_restores_approved(self, frappe_mod):
		frappe_mod.db.exists.return_value = True
		row = frappe._dict(
			item_code="PART-A",
			status="Issued",
			stock_entry="STE-1",
			material_request="MR-1",
		)
		job_doc = MagicMock()
		job_doc.spareparts_requests = [row]
		job_doc.flags = MagicMock()
		frappe_mod.get_doc.return_value = job_doc

		se = frappe._dict(job_card="JC-1", purpose="Material Issue", name="STE-1", items=[])
		on_cancel(se)
		self.assertIsNone(row.stock_entry)
		self.assertEqual(row.status, "Approved")
		job_doc.save.assert_called_once_with(ignore_permissions=True)

	@patch("autods.overrides.stock_entry.frappe")
	def test_on_cancel_restores_requested_without_material_request(self, frappe_mod):
		frappe_mod.db.exists.return_value = True
		row = frappe._dict(
			item_code="PART-A",
			status="Issued",
			stock_entry="STE-1",
			material_request=None,
		)
		job_doc = MagicMock()
		job_doc.spareparts_requests = [row]
		job_doc.flags = MagicMock()
		frappe_mod.get_doc.return_value = job_doc

		se = frappe._dict(job_card="JC-1", purpose="Material Issue", name="STE-1", items=[])
		on_cancel(se)
		self.assertEqual(row.status, "Requested")


class TestMakeStockEntryWrap(unittest.TestCase):
	@patch("autods.overrides.material_request.is_service_job_card", return_value=True)
	@patch("autods.overrides.material_request._make_stock_entry_for_service_job_card")
	@patch("autods.overrides.material_request.frappe.get_doc")
	def test_service_job_card_keeps_material_issue_mapper(self, get_doc, make_se, _is_svc):
		mr = MagicMock()
		mr.material_request_type = "Material Issue"
		mr.get.return_value = "JC-1"
		mr.job_card = "JC-1"
		get_doc.return_value = mr
		mapped = frappe._dict(purpose="Material Issue", job_card="JC-1")
		make_se.return_value = mapped

		from autods.overrides.material_request import make_stock_entry

		doc = make_stock_entry("MAT-MR-1")
		make_se.assert_called_once_with("MAT-MR-1", None)
		self.assertEqual(doc.purpose, "Material Issue")
		self.assertEqual(doc.job_card, "JC-1")

	@patch("erpnext.stock.doctype.material_request.material_request.make_stock_entry")
	@patch("autods.overrides.material_request.is_service_job_card", return_value=False)
	@patch("autods.overrides.material_request.frappe.get_doc")
	def test_non_service_job_card_uses_erpnext(self, get_doc, _is_svc, erpnext_make):
		mr = MagicMock()
		mr.material_request_type = "Material Issue"
		mr.get.return_value = "JC-MFG"
		mr.job_card = "JC-MFG"
		get_doc.return_value = mr
		erpnext_make.return_value = frappe._dict(purpose="Material Transfer for Manufacture")

		from autods.overrides.material_request import make_stock_entry

		doc = make_stock_entry("MAT-MR-2")
		erpnext_make.assert_called_once_with("MAT-MR-2", None)
		self.assertEqual(doc.purpose, "Material Transfer for Manufacture")
