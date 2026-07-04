# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt
#
# Migration patch: for each Vehicle Unit with a non-zero purchase_price and no
# Vehicle Cost Ledger entries yet, create one Opening Vehicle Cost Ledger entry
# of type "Opening" so cost-per-VIN reporting becomes immediately available.
# This DOES NOT post to GL (Opening entries are operational only).

import frappe
from frappe.utils import flt


def execute():
	if not frappe.db.has_table("Vehicle Unit"):
		return
	if not frappe.db.has_table("Vehicle Cost Ledger"):
		return

	rows = frappe.db.sql(
		"""
		select v.name, v.code, v.purchase_price, v.purchase_date, v.warehouse
		from `tabVehicle Unit` v
		left join `tabVehicle Cost Ledger` vcl on vcl.vehicle_unit = v.name and vcl.docstatus = 1
		where vcl.name is null and ifnull(v.purchase_price, 0) > 0
		""",
		as_dict=True,
	)
	if not rows:
		return

	default_company = frappe.defaults.get_user_default("Company")
	if not default_company:
		companies = frappe.get_all("Company", limit=1, pluck="name")
		default_company = companies[0] if companies else None
	if not default_company:
		frappe.log_error(
			"backfill_vehicle_cost_ledger: no Company found, skipping.",
			"AutoDS: backfill_vehicle_cost_ledger",
		)
		return

	created = 0
	for vu in rows:
		try:
			doc = frappe.new_doc("Vehicle Cost Ledger")
			doc.vehicle_unit = vu.name
			doc.company = default_company
			doc.posting_date = vu.purchase_date or frappe.utils.getdate()
			doc.voucher_type = "Manual"
			doc.cost_type = "Opening"
			doc.amount = flt(vu.purchase_price, 2)
			doc.is_opening = 1
			doc.remarks = f"Opening cost backfilled for VIN {vu.code or vu.name}"
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
			doc.submit()
			created += 1
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"backfill_vehicle_cost_ledger: failed for Vehicle Unit {vu.name}",
			)
	frappe.db.commit()
	if created:
		print(f"AutoDS: backfilled {created} Vehicle Cost Ledger opening entries.")
