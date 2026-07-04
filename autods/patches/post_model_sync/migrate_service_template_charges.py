# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import json

import frappe

from autods.patches.pre_model_sync.backup_service_template_charges import BACKUP_TABLE

CHARGE_FIELDS = (
	"service_item_type",
	"item",
	"item_name",
	"service_type",
	"description",
	"service_row",
	"hours",
	"qty",
	"uom",
	"rate",
	"amount",
	"bill_type",
	"bill_to",
	"item_type",
	"warehouse",
	"color_code",
	"paint_type",
)


def execute():
	"""Restore Service Template charge rows into unified charges table."""
	if not frappe.db.table_exists("Service Template Charges"):
		return

	if frappe.db.table_exists(BACKUP_TABLE):
		_restore_from_backup()
	else:
		_migrate_from_legacy_tables()

	_cleanup_backup()
	_remove_legacy_doctypes()
	frappe.db.commit()


def _restore_from_backup():
	rows = frappe.db.sql(
		f"""
		SELECT parent, idx, service_item_type, row_json
		FROM `{BACKUP_TABLE}`
		ORDER BY parent ASC, idx ASC
		""",
		as_dict=True,
	)
	if not rows:
		return

	by_parent = {}
	for row in rows:
		by_parent.setdefault(row.parent, []).append(row)

	for parent, parent_rows in by_parent.items():
		if not frappe.db.exists("Service Template", parent):
			continue
		if frappe.db.count("Service Template Charges", {"parent": parent}):
			continue
		_insert_rows(parent, parent_rows)


def _migrate_from_legacy_tables():
	legacy_sources = (
		("Service Template Service Items", "Service"),
		("Service Template Parts", "Spareparts"),
		("Service Template Sundry Items", "Overhead"),
	)
	templates = frappe.get_all("Service Template", pluck="name")
	for parent in templates:
		if frappe.db.count("Service Template Charges", {"parent": parent}):
			continue
		parent_rows = []
		for doctype, default_type in legacy_sources:
			if not frappe.db.table_exists(f"tab{doctype}"):
				continue
			for row in frappe.db.get_all(
				doctype,
				filters={"parent": parent, "parenttype": "Service Template"},
				fields=["*"],
				order_by="idx asc",
			):
				parent_rows.append(
					{
						"service_item_type": default_type,
						"row_json": json.dumps(_legacy_row_to_charge(default_type, row)),
					}
				)
		if parent_rows:
			_insert_rows(parent, parent_rows)


def _insert_rows(parent, parent_rows):
	service_count = sum(
		1 for r in parent_rows if _payload(r).get("service_item_type") == "Service"
	)
	default_service_row = "1" if service_count else None
	idx = 0

	# Services first, then spareparts/overhead (backup table order preserves per-table idx)
	ordered = sorted(
		parent_rows,
		key=lambda r: (
			0 if _payload(r).get("service_item_type") == "Service" else 1,
			r.get("idx") or 0,
		),
	)

	for row in ordered:
		payload = _payload(row)
		if payload.get("service_item_type") in ("Spareparts", "Overhead") and default_service_row:
			payload.setdefault("service_row", default_service_row)
		idx += 1
		charge = frappe.new_doc("Service Template Charges")
		charge.update(
			{
				"parent": parent,
				"parenttype": "Service Template",
				"parentfield": "charges",
				"idx": idx,
			}
		)
		for field in CHARGE_FIELDS:
			if payload.get(field) is not None:
				charge.set(field, payload[field])
		charge.db_insert()


def _payload(row):
	data = row.get("row_json")
	if isinstance(data, str):
		return json.loads(data)
	return data or row


def _legacy_row_to_charge(service_item_type, row):
	from autods.patches.pre_model_sync import backup_service_template_charges as backup

	if service_item_type == "Service":
		return backup._map_service_item(row)
	if service_item_type == "Spareparts":
		return backup._map_part(row)
	return backup._map_sundry(row)


def _cleanup_backup():
	if frappe.db.table_exists(BACKUP_TABLE):
		frappe.db.sql(f"DROP TABLE `{BACKUP_TABLE}`")


def _remove_legacy_doctypes():
	for name in (
		"Service Template Service Items",
		"Service Template Parts",
		"Service Template Sundry Items",
	):
		if frappe.db.exists("DocType", name):
			frappe.delete_doc("DocType", name, force=1)
