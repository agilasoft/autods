# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import now_datetime

from autods.principal_portal.sync import set_inbound_guard
from autods.principal_portal.utils import get_party_code, get_site_role, is_sync_user, is_system_manager


def _parse_payload(payload):
	if payload is None:
		payload = frappe.form_dict.get("payload")
	if isinstance(payload, str):
		payload = frappe.parse_json(payload) if payload else {}
	return payload or {}


def _require_sync_user():
	if not (is_sync_user() or is_system_manager()):
		frappe.throw(_("Portal Sync User role is required."), frappe.PermissionError)


def _log_inbound(doctype, name, event, payload, status="Success", error=""):
	try:
		frappe.get_doc(
			{
				"doctype": "Portal Sync Log",
				"direction": "Inbound",
				"event": event,
				"status": status,
				"reference_doctype": doctype,
				"local_name": name,
				"remote_name": (payload or {}).get("origin_name"),
				"request_payload": json.dumps(payload or {}, default=str)[:8000],
				"error": (error or "")[:500],
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Portal inbound log failed")


def _resolve_principal(code):
	if not code:
		return None
	return frappe.db.get_value("Principal", {"code": code})


def _resolve_dealer(code):
	if not code:
		return None
	return frappe.db.get_value("Dealer", {"code": code})


def _find_by_origin(doctype, origin_site, origin_name):
	if origin_site and origin_name:
		name = frappe.db.get_value(doctype, {"remote_site": origin_site, "remote_name": origin_name})
		if name:
			return name
	if origin_name:
		if frappe.db.exists(doctype, origin_name):
			return origin_name
	return None


def _apply_items(doc, table, items, fields):
	doc.set(table, [])
	for row in items or []:
		values = {field: row.get(field) for field in fields}
		if not values.get("item_code") and values.get("item_name"):
			values["description"] = values.get("description") or values.get("item_name")
		doc.append(table, values)


@frappe.whitelist()
def handshake(payload: str | dict | None = None):
	_require_sync_user()
	return {"site_role": get_site_role(), "party_code": get_party_code()}


@frappe.whitelist()
def upsert_principal_order(payload: str | dict | None = None):
	_require_sync_user()
	data = _parse_payload(payload)
	set_inbound_guard(True)
	try:
		doc = _upsert_order(data, event="submit")
		_log_inbound("Principal Order", doc.name, "submit", data)
		return {"name": doc.name, "status": doc.status}
	except Exception as exc:
		_log_inbound("Principal Order", data.get("origin_name"), "submit", data, "Failed", str(exc))
		raise


@frappe.whitelist()
def update_principal_order_status(payload: str | dict | None = None):
	_require_sync_user()
	data = _parse_payload(payload)
	set_inbound_guard(True)
	try:
		doc = _upsert_order(data, event=data.get("event") or "status")
		_log_inbound("Principal Order", doc.name, data.get("event") or "status", data)
		return {"name": doc.name, "status": doc.status}
	except Exception as exc:
		_log_inbound("Principal Order", data.get("origin_name"), "status", data, "Failed", str(exc))
		raise


@frappe.whitelist()
def upsert_warranty_claim(payload: str | dict | None = None):
	_require_sync_user()
	data = _parse_payload(payload)
	set_inbound_guard(True)
	try:
		doc = _upsert_claim(data, event="submit")
		_log_inbound("Warranty Claim", doc.name, "submit", data)
		return {"name": doc.name, "status": doc.status}
	except Exception as exc:
		_log_inbound("Warranty Claim", data.get("origin_name"), "submit", data, "Failed", str(exc))
		raise


@frappe.whitelist()
def update_warranty_claim_status(payload: str | dict | None = None):
	_require_sync_user()
	data = _parse_payload(payload)
	set_inbound_guard(True)
	try:
		doc = _upsert_claim(data, event=data.get("event") or "status")
		_log_inbound("Warranty Claim", doc.name, data.get("event") or "status", data)
		return {"name": doc.name, "status": doc.status}
	except Exception as exc:
		_log_inbound("Warranty Claim", data.get("origin_name"), "status", data, "Failed", str(exc))
		raise


@frappe.whitelist()
def publish_circular(payload: str | dict | None = None):
	_require_sync_user()
	data = _parse_payload(payload)
	set_inbound_guard(True)
	try:
		existing = _find_by_origin("Dealer Circular", data.get("origin_site"), data.get("origin_name"))
		doc = frappe.get_doc("Dealer Circular", existing) if existing else frappe.new_doc("Dealer Circular")
		doc.title = data.get("title") or doc.title
		doc.body = data.get("body")
		doc.audience = "All Dealers"
		doc.published = 1
		doc.published_on = now_datetime()
		doc.remote_site = data.get("origin_site")
		doc.remote_name = data.get("origin_name")
		doc.sync_origin = data.get("origin_site")
		doc.sync_status = "Synced"
		doc.flags.skip_circular_sync = True
		if existing:
			doc.save(ignore_permissions=True)
		else:
			doc.insert(ignore_permissions=True)
		_log_inbound("Dealer Circular", doc.name, "circular", data)
		return {"name": doc.name}
	except Exception as exc:
		_log_inbound("Dealer Circular", data.get("origin_name"), "circular", data, "Failed", str(exc))
		raise


def _upsert_order(data, event):
	principal = _resolve_principal(data.get("principal_code"))
	dealer = _resolve_dealer(data.get("dealer_code"))
	if get_site_role() == "Principal" and not dealer:
		frappe.throw(_("Unknown dealer code {0}").format(data.get("dealer_code")))
	if get_site_role() == "Dealer" and not principal:
		frappe.throw(_("Unknown principal code {0}").format(data.get("principal_code")))
	existing = _find_by_origin("Principal Order", data.get("origin_site"), data.get("origin_name"))
	doc = frappe.get_doc("Principal Order", existing) if existing else frappe.new_doc("Principal Order")
	if principal:
		doc.principal = principal
	if dealer:
		doc.dealer = dealer
	if data.get("order_date"):
		doc.order_date = data.get("order_date")
	if data.get("order_type"):
		doc.order_type = data.get("order_type")
	doc.vin = data.get("vin")
	doc.chassis_number = data.get("chassis_number")
	_apply_items(
		doc,
		"items",
		data.get("items"),
		("item_code", "item_name", "description", "qty", "rate", "amount", "delivered_qty"),
	)
	doc.remote_site = data.get("origin_site")
	doc.remote_name = data.get("origin_name")
	doc.sync_origin = data.get("origin_site")
	doc.sync_status = "Synced"
	status = data.get("status") or "Submitted"
	if not existing:
		doc.status = "Draft"
		doc.insert(ignore_permissions=True)
		if event in ("submit", "status", "cancel") and status != "Draft":
			doc.submit()
	if doc.docstatus == 1:
		if event == "cancel" or status == "Cancelled":
			if doc.docstatus == 1:
				doc.cancel()
		elif status and status != doc.status:
			doc.db_set("status", status, update_modified=False)
	else:
		doc.save(ignore_permissions=True)
		if status and status not in ("Draft",):
			doc.submit()
			if status not in ("Submitted",):
				doc.db_set("status", status, update_modified=False)
	return doc


def _upsert_claim(data, event):
	principal = _resolve_principal(data.get("principal_code"))
	dealer = _resolve_dealer(data.get("dealer_code"))
	if get_site_role() == "Principal" and not dealer:
		frappe.throw(_("Unknown dealer code {0}").format(data.get("dealer_code")))
	if get_site_role() == "Dealer" and not principal:
		frappe.throw(_("Unknown principal code {0}").format(data.get("principal_code")))
	existing = _find_by_origin("Warranty Claim", data.get("origin_site"), data.get("origin_name"))
	doc = frappe.get_doc("Warranty Claim", existing) if existing else frappe.new_doc("Warranty Claim")
	if principal:
		doc.principal = principal
	if dealer:
		doc.dealer = dealer
	if data.get("claim_date"):
		doc.claim_date = data.get("claim_date")
	doc.vin = data.get("vin")
	doc.chassis_number = data.get("chassis_number")
	doc.odometer = data.get("odometer")
	doc.failure_description = data.get("failure_description")
	_apply_items(
		doc,
		"items",
		data.get("items"),
		("item_code", "item_name", "description", "qty", "amount"),
	)
	doc.remote_site = data.get("origin_site")
	doc.remote_name = data.get("origin_name")
	doc.sync_origin = data.get("origin_site")
	doc.sync_status = "Synced"
	status = data.get("status") or "Submitted"
	if not existing:
		doc.status = "Draft"
		doc.insert(ignore_permissions=True)
		if status != "Draft":
			doc.submit()
	if doc.docstatus == 1:
		if event == "cancel":
			if doc.docstatus == 1:
				doc.cancel()
		elif status and status != doc.status:
			doc.db_set("status", status, update_modified=False)
	else:
		doc.save(ignore_permissions=True)
		if status and status not in ("Draft",):
			doc.submit()
			if status not in ("Submitted",):
				doc.db_set("status", status, update_modified=False)
	return doc
