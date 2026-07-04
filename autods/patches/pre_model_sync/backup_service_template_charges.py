# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import json

import frappe

BACKUP_TABLE = "_st_charge_migration"


def execute():
	"""Backup Service Template legacy charge rows before schema sync drops child tables."""
	if frappe.db.table_exists(BACKUP_TABLE):
		return

	legacy_sources = (
		("Service Template Service Items", "Service", _map_service_item),
		("Service Template Parts", "Spareparts", _map_part),
		("Service Template Sundry Items", "Overhead", _map_sundry),
	)
	has_data = False
	for doctype, _type, _mapper in legacy_sources:
		if frappe.db.table_exists(f"tab{doctype}"):
			has_data = bool(frappe.db.count(doctype))
			if has_data:
				break

	if not has_data:
		return

	frappe.db.sql(
		f"""
		CREATE TABLE `{BACKUP_TABLE}` (
			`name` varchar(140) NOT NULL,
			`parent` varchar(140),
			`idx` int NOT NULL DEFAULT 0,
			`service_item_type` varchar(140),
			`row_json` longtext,
			PRIMARY KEY (`name`),
			KEY `parent_idx` (`parent`, `idx`)
		) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
		"""
	)

	backup_idx = 0
	for doctype, default_type, mapper in legacy_sources:
		if not frappe.db.table_exists(f"tab{doctype}"):
			continue
		rows = frappe.db.get_all(
			doctype,
			filters={"parenttype": "Service Template"},
			fields=["*"],
			order_by="parent asc, idx asc",
		)
		for row in rows:
			backup_idx += 1
			payload = mapper(row)
			frappe.db.sql(
				f"""
				INSERT INTO `{BACKUP_TABLE}`
					(name, parent, idx, service_item_type, row_json)
				VALUES (%s, %s, %s, %s, %s)
				""",
				(
					f"STCM-{backup_idx:06d}",
					row.parent,
					row.idx,
					payload.get("service_item_type") or default_type,
					json.dumps(payload),
				),
			)

	frappe.db.commit()


def _map_service_item(row):
	return {
		"service_item_type": "Service",
		"item": row.get("service_item"),
		"service_type": row.get("service_type"),
		"description": row.get("description"),
		"bill_type": row.get("bill_type"),
		"bill_to": row.get("bill_to"),
		"hours": row.get("hours"),
		"rate": row.get("rate"),
		"amount": _amount_service(row),
	}


def _map_part(row):
	return {
		"service_item_type": "Spareparts",
		"item": row.get("item"),
		"item_name": row.get("item_name"),
		"item_type": row.get("item_type"),
		"qty": row.get("qty"),
		"uom": row.get("uom"),
		"rate": row.get("rate"),
		"bill_type": row.get("bill_type"),
		"bill_to": row.get("bill_to"),
		"warehouse": row.get("warehouse"),
		"color_code": row.get("color_code"),
		"paint_type": row.get("paint_type"),
		"description": row.get("description"),
		"amount": _amount_qty(row),
	}


def _map_sundry(row):
	return {
		"service_item_type": "Overhead",
		"item": row.get("item"),
		"item_name": row.get("item_name"),
		"description": row.get("description"),
		"qty": row.get("qty"),
		"uom": row.get("uom"),
		"rate": row.get("rate"),
		"bill_type": row.get("bill_type"),
		"bill_to": row.get("bill_to"),
		"amount": _amount_qty(row),
	}


def _flt(val):
	try:
		return float(val or 0)
	except (TypeError, ValueError):
		return 0.0


def _amount_service(row):
	hours = _flt(row.get("hours"))
	rate = _flt(row.get("rate"))
	return hours * rate if hours and rate else 0


def _amount_qty(row):
	qty = _flt(row.get("qty"))
	rate = _flt(row.get("rate"))
	return qty * rate if qty and rate else 0
