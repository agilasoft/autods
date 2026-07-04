# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe


def _table_name(doctype: str) -> str:
	return "tab" + doctype


def _remove_empty_placeholder_doctype(name: str) -> None:
	"""If this DocType already exists from a partial sync with an empty table, drop it so rename_doc can claim the name."""
	if not frappe.db.exists("DocType", name):
		return
	if not frappe.db.has_table(name):
		try:
			frappe.delete_doc("DocType", name, force=True, ignore_permissions=True)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
		return
	try:
		row_count = frappe.db.count(name)
	except Exception:
		row_count = -1
	if row_count and row_count > 0:
		frappe.log_error(
			title="rename_charge_child_doctypes: target DocType not empty",
			message=f"{name} has {row_count} rows; manual merge may be needed before migrate.",
		)
		return
	tn = _table_name(name)
	frappe.db.sql(f"DROP TABLE IF EXISTS `{tn}`")
	try:
		frappe.delete_doc("DocType", name, force=True, ignore_permissions=True)
	except Exception:
		frappe.db.rollback()
		raise
	frappe.db.commit()


def _rename_doctype(old: str, new: str) -> None:
	if not frappe.db.exists("DocType", old):
		return
	_remove_empty_placeholder_doctype(new)
	if not frappe.db.exists("DocType", old):
		return
	frappe.rename_doc("DocType", old, new, force=True)
	frappe.db.commit()


def execute():
	"""Rename charge-line child DocTypes before schema sync; resolve legacy Repair Order Services collision."""
	frappe.db.commit()

	# Legacy quantity-based "Repair Order Services" must move before Service Items can take the name
	if frappe.db.exists("DocType", "Repair Order Services"):
		meta = frappe.get_meta("Repair Order Services")
		if meta.has_field("quantity") and not meta.has_field("hours"):
			_remove_empty_placeholder_doctype("RO Legacy Service Row")
			frappe.rename_doc("DocType", "Repair Order Services", "RO Legacy Service Row", force=True)
			frappe.db.commit()

	if frappe.db.exists("DocType", "Repair Order Service Items"):
		_remove_empty_placeholder_doctype("Repair Order Services")
		frappe.rename_doc("DocType", "Repair Order Service Items", "Repair Order Services", force=True)
		frappe.db.commit()

	for old, new in (
		("Repair Estimate Service Items", "Repair Estimate Services"),
		("Repair Estimate Parts", "Repair Estimate Spareparts"),
		("Repair Estimate Sundry Items", "Repair Estimate Overhead"),
	):
		_rename_doctype(old, new)

	_rename_doctype("Repair Order Parts", "Repair Order Spareparts")
	_rename_doctype("Repair Order Sundry Items", "Repair Order Overhead")

	frappe.clear_cache()
