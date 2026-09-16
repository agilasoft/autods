# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from frappe.tests.utils import FrappeTestCase


class TestPrincipal(FrappeTestCase):
	def test_create_principal(self):
		import frappe

		if not frappe.db.exists("DocType", "Principal"):
			self.skipTest("Principal DocType not installed")
		if frappe.db.exists("Principal", "OEM-TEST"):
			frappe.delete_doc("Principal", "OEM-TEST", force=1)
		doc = frappe.get_doc(
			{"doctype": "Principal", "code": "OEM-TEST", "principal_name": "Test OEM", "active": 1}
		).insert(ignore_permissions=True)
		self.assertEqual(doc.name, "OEM-TEST")
		doc.delete()
