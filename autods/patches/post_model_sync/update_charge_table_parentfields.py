# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""After migrate, point child rows at new parent table fieldnames."""
	rows = (
		("Repair Estimate Services", "Repair Estimate", "service_items", "repair_estimate_services"),
		("Repair Estimate Spareparts", "Repair Estimate", "spareparts", "repair_estimate_spareparts"),
		("Repair Estimate Overhead", "Repair Estimate", "sundry_items", "repair_estimate_overhead"),
		("Repair Order Services", "Repair Order", "service_items", "repair_order_services"),
		("Repair Order Spareparts", "Repair Order", "spareparts", "repair_order_spareparts"),
		("Repair Order Overhead", "Repair Order", "sundry_items", "repair_order_overhead"),
		("Repair Order Charges", "Repair Order", "service_items", "charges"),
		("Repair Order Charges", "Repair Order", "spareparts", "charges"),
		("Repair Order Charges", "Repair Order", "sundry_items", "charges"),
		("Repair Estimate Charges", "Repair Estimate", "service_items", "charges"),
		("Repair Estimate Charges", "Repair Estimate", "spareparts", "charges"),
		("Repair Estimate Charges", "Repair Estimate", "sundry_items", "charges"),
	)
	for child_doctype, parent_type, old_pf, new_pf in rows:
		if not frappe.db.exists("DocType", child_doctype):
			continue
		if not frappe.db.has_table(child_doctype):
			continue
		try:
			frappe.db.sql(
				f"update `tab{child_doctype}` set parentfield=%s where parenttype=%s and parentfield=%s",
				(new_pf, parent_type, old_pf),
			)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "update_charge_table_parentfields")

	frappe.db.commit()
