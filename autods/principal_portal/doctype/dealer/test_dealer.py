# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from frappe.tests.utils import FrappeTestCase


class TestDealer(FrappeTestCase):
	def test_create_dealer(self):
		import frappe

		if not frappe.db.exists("DocType", "Dealer"):
			self.skipTest("Dealer DocType not installed")
		if frappe.db.exists("Dealer", "DLR-TEST"):
			frappe.delete_doc("Dealer", "DLR-TEST", force=1)
		doc = frappe.get_doc(
			{"doctype": "Dealer", "code": "DLR-TEST", "dealer_name": "Test Dealer", "status": "Active"}
		).insert(ignore_permissions=True)
		self.assertEqual(doc.name, "DLR-TEST")
		doc.delete()
