# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from frappe.tests.utils import FrappeTestCase


class TestPrincipalOrder(FrappeTestCase):
	def test_submit_computes_totals(self):
		import frappe

		if not frappe.db.exists("DocType", "Principal Order"):
			self.skipTest("Principal Order DocType not installed")
		frappe.db.set_single_value("Principal Dealer Settings", "site_role", "Dealer")
		frappe.db.set_single_value("Principal Dealer Settings", "party_code", "DLR-ORDER")
		if not frappe.db.exists("Principal", "OEM-ORDER"):
			frappe.get_doc(
				{"doctype": "Principal", "code": "OEM-ORDER", "principal_name": "OEM Order", "active": 1}
			).insert(ignore_permissions=True)
		if not frappe.db.exists("Dealer", "DLR-ORDER"):
			frappe.get_doc(
				{"doctype": "Dealer", "code": "DLR-ORDER", "dealer_name": "Dealer Order", "status": "Active"}
			).insert(ignore_permissions=True)
		order = frappe.get_doc(
			{
				"doctype": "Principal Order",
				"naming_series": "POR-.YYYY.-",
				"order_date": "2026-09-16",
				"order_type": "Parts",
				"principal": "OEM-ORDER",
				"dealer": "DLR-ORDER",
				"items": [{"item_code": "P-1", "item_name": "Part", "qty": 2, "rate": 15}],
			}
		)
		order.insert(ignore_permissions=True)
		self.assertEqual(order.net_total, 30)
		order.submit()
		self.assertEqual(order.status, "Submitted")
		order.cancel()
