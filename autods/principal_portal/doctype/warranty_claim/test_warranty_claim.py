# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from frappe.tests.utils import FrappeTestCase


class TestWarrantyClaim(FrappeTestCase):
	def test_submit_claim(self):
		import frappe

		if not frappe.db.exists("DocType", "Warranty Claim"):
			self.skipTest("Warranty Claim DocType not installed")
		frappe.db.set_single_value("Principal Dealer Settings", "site_role", "Dealer")
		frappe.db.set_single_value("Principal Dealer Settings", "party_code", "DLR-CLM")
		if not frappe.db.exists("Principal", "OEM-CLM"):
			frappe.get_doc(
				{"doctype": "Principal", "code": "OEM-CLM", "principal_name": "OEM Claim", "active": 1}
			).insert(ignore_permissions=True)
		claim = frappe.get_doc(
			{
				"doctype": "Warranty Claim",
				"naming_series": "WCL-.YYYY.-",
				"claim_date": "2026-09-16",
				"principal": "OEM-CLM",
				"failure_description": "Oil leak",
				"items": [{"item_code": "SEAL", "qty": 1, "amount": 50}],
			}
		)
		claim.insert(ignore_permissions=True)
		self.assertEqual(claim.claim_amount, 50)
		claim.submit()
		self.assertEqual(claim.status, "Submitted")
		claim.cancel()
