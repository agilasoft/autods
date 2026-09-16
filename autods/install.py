# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe

from autods.principal_portal.setup import after_install as principal_portal_after_install
from autods.principal_portal.setup import after_migrate as principal_portal_after_migrate
from autods.vehicle_sales.setup import after_install as vehicle_sales_after_install
from autods.vehicle_sales.setup import after_migrate as vehicle_sales_after_migrate


def after_install():
	vehicle_sales_after_install()
	principal_portal_after_install()


def after_migrate():
	vehicle_sales_after_migrate()
	principal_portal_after_migrate()


def before_tests():
	# AutoDS tests create their own masters. Skip Frappe's recursive ERPNext
	# test_records.json graph (Company, User, Customer, …) during discovery.
	frappe.flags.skip_test_records = True
	try:
		from erpnext.setup.utils import before_tests as erpnext_before_tests
	except ImportError:
		return
	erpnext_before_tests()
