# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class VehicleSalesSettings(Document):
	def validate(self):
		self._validate_unique_companies()

	def _validate_unique_companies(self):
		seen = set()
		for row in self.get("company_settings") or []:
			if not row.company:
				continue
			if row.company in seen:
				frappe.throw(
					_("Company {0} appears more than once in Per-Company Settings").format(row.company)
				)
			seen.add(row.company)


def get_settings():
	"""Return the singleton (cached)."""
	return frappe.get_cached_doc("Vehicle Sales Settings")


def get_company_settings(company):
	"""
	Return the per-company settings row (as a dict) for ``company``.
	Falls back to a dict of ``None`` values if no row is configured so callers
	can still safely use .get(...).
	"""
	if not company:
		return _empty_company_settings()
	settings = get_settings()
	for row in settings.get("company_settings") or []:
		if row.company == company:
			return row.as_dict()
	return _empty_company_settings(company)


def _empty_company_settings(company=None):
	return frappe._dict(
		{
			"company": company,
			"default_vehicle_inventory_account": None,
			"default_cogs_account": None,
			"default_stock_received_but_not_billed": None,
			"default_cost_center": None,
			"default_vehicle_warehouse": None,
			"default_supplier_account": None,
		}
	)


def get_naming_series(field):
	"""Get a naming series with a sane fallback if settings are not set up."""
	defaults = {
		"vehicle_quote_naming_series": "VSQ-.YYYY.-",
		"vehicle_sales_order_naming_series": "VSO-.YYYY.-",
		"vehicle_delivery_naming_series": "VDN-.YYYY.-",
		"vehicle_receiving_naming_series": "VRC-.YYYY.-",
		"vehicle_cost_ledger_naming_series": "VCL-.YYYY.-",
	}
	if field not in defaults:
		return None
	try:
		val = frappe.db.get_single_value("Vehicle Sales Settings", field)
		return val or defaults[field]
	except Exception:
		return defaults[field]
