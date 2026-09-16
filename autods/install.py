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
	try:
		from erpnext.setup.utils import before_tests as erpnext_before_tests
	except ImportError:
		return
	erpnext_before_tests()
	_ensure_erpnext_test_masters()
	frappe.db.commit()


def _ensure_erpnext_test_masters():
	"""ERPNext test_records.json expect `_Test Company` / `_Test Holiday List`."""
	if not frappe.db.exists("Holiday List", "_Test Holiday List"):
		holiday_list = frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": "_Test Holiday List",
				"from_date": "2000-01-01",
				"to_date": "2099-12-31",
			}
		)
		holiday_list.append("holidays", {"description": "New Year", "holiday_date": "2000-01-01"})
		holiday_list.insert(ignore_permissions=True)

	companies = (
		{"company_name": "_Test Company", "abbr": "_TC", "country": "India", "default_currency": "INR"},
		{
			"company_name": "_Test Company 1",
			"abbr": "_TC1",
			"country": "United States",
			"default_currency": "USD",
		},
		{"company_name": "_Test Company 2", "abbr": "_TC2", "country": "Germany", "default_currency": "EUR"},
	)
	for row in companies:
		if frappe.db.exists("Company", row["company_name"]):
			continue
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": row["company_name"],
				"abbr": row["abbr"],
				"country": row["country"],
				"default_currency": row["default_currency"],
				"chart_of_accounts": "Standard",
				"domain": "Manufacturing",
				"default_holiday_list": "_Test Holiday List",
			}
		).insert(ignore_permissions=True)
