# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import frappe
from frappe.utils import cint, now_datetime

from autods.principal_portal.utils import (
	enqueue_on_submit_enabled,
	get_party_code,
	get_site_role,
	max_sync_retries,
)

METHOD_BY_EVENT = {
	("Principal Order", "submit"): "upsert_principal_order",
	("Principal Order", "status"): "update_principal_order_status",
	("Principal Order", "cancel"): "update_principal_order_status",
	("Warranty Claim", "submit"): "upsert_warranty_claim",
	("Warranty Claim", "status"): "update_warranty_claim_status",
	("Warranty Claim", "cancel"): "update_warranty_claim_status",
	("Dealer Circular", "circular"): "publish_circular",
}

PAYLOAD_TRUNCATE = 8000


def inbound_guard():
	return bool(getattr(frappe.flags, "in_portal_sync", False))


def set_inbound_guard(value=True):
	frappe.flags.in_portal_sync = value


def enqueue_sync(doc, event):
	if inbound_guard():
		return
	if getattr(frappe.flags, "in_test", False) and not getattr(frappe.flags, "portal_sync_in_test", False):
		return
	if not enqueue_on_submit_enabled():
		return
	if not frappe.db.exists("DocType", "Portal Connection"):
		return
	method = METHOD_BY_EVENT.get((doc.doctype, event))
	if not method:
		return
	connections = list_connections_for(doc)
	if not connections:
		return
	if getattr(doc, "sync_status", None) != "Pending":
		try:
			doc.db_set("sync_status", "Pending", update_modified=False)
		except Exception:
			pass
	for connection_name in connections:
		frappe.enqueue(
			"autods.principal_portal.sync.push_document",
			queue="short",
			enqueue_after_commit=True,
			doc_type=doc.doctype,
			name=doc.name,
			event=event,
			connection_name=connection_name,
		)


def list_connections_for(doc):
	filters = {"enabled": 1}
	if doc.doctype == "Dealer Circular":
		filters["party_type"] = "Dealer"
		names = frappe.get_all("Portal Connection", filters=filters, pluck="name")
		if doc.audience == "Selected Dealers":
			allowed = {row.dealer for row in (doc.get("recipients") or []) if row.dealer}
			return [
				name for name in names if frappe.db.get_value("Portal Connection", name, "party") in allowed
			]
		return names
	site_role = get_site_role()
	if site_role == "Dealer" and getattr(doc, "principal", None):
		filters.update({"party_type": "Principal", "party": doc.principal})
	elif site_role == "Principal" and getattr(doc, "dealer", None):
		filters.update({"party_type": "Dealer", "party": doc.dealer})
	else:
		return []
	return frappe.get_all("Portal Connection", filters=filters, pluck="name")


def push_document(doc_type, name, event, connection_name, log_name=None):
	doc = frappe.get_doc(doc_type, name)
	connection = frappe.get_doc("Portal Connection", connection_name)
	method = METHOD_BY_EVENT.get((doc_type, event))
	if not method:
		return
	payload = build_payload(doc, event)
	log = _ensure_log(log_name, connection.name, doc, event, payload, "Outbound")
	try:
		result = post_to_remote(connection, method, payload)
		message = result.get("message") if isinstance(result, dict) else result
		remote_name = None
		if isinstance(message, dict):
			remote_name = message.get("name") or message.get("remote_name")
		_mark_log_success(log, result, remote_name)
		_mark_doc_synced(doc, connection, remote_name)
	except Exception as exc:
		_mark_log_failed(log, exc)
		try:
			doc.db_set("sync_status", "Error", update_modified=False)
		except Exception:
			pass


def retry_log(log_name):
	log = frappe.get_doc("Portal Sync Log", log_name)
	if log.direction != "Outbound":
		frappe.throw("Only outbound logs can be retried.")
	push_document(log.reference_doctype, log.local_name, log.event, log.connection, log_name=log.name)
	return log.name


def retry_failed_logs():
	if not frappe.db.exists("DocType", "Portal Sync Log"):
		return
	limit = max_sync_retries()
	logs = frappe.get_all(
		"Portal Sync Log",
		filters={"status": "Failed", "direction": "Outbound", "retry_count": ["<", limit]},
		pluck="name",
		limit=50,
	)
	for name in logs:
		try:
			log = frappe.get_doc("Portal Sync Log", name)
			log.db_set("retry_count", cint(log.retry_count) + 1, update_modified=False)
			push_document(log.reference_doctype, log.local_name, log.event, log.connection, log_name=log.name)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Portal sync retry failed")


def handshake(connection):
	result = post_to_remote(connection, "handshake", {})
	if isinstance(result, dict) and "message" in result:
		return result["message"]
	return result


def post_to_remote(connection, method, payload):
	url = f"{connection.site_url.rstrip('/')}/api/method/autods.principal_portal.api.{method}"
	secret = connection.get_password("api_secret") if connection.api_secret else ""
	if not connection.api_key or not secret:
		frappe.throw("Portal Connection is missing API key or secret.")
	body = urlencode({"payload": json.dumps(payload, default=str)}).encode()
	request = Request(url, data=body, method="POST")
	request.add_header("Authorization", f"token {connection.api_key}:{secret}")
	request.add_header("Content-Type", "application/x-www-form-urlencoded")
	request.add_header("Accept", "application/json")
	with urlopen(request, timeout=30) as response:
		raw = response.read().decode()
	try:
		return json.loads(raw)
	except json.JSONDecodeError:
		return {"raw": raw}


def build_payload(doc, event):
	origin_site = get_party_code() or frappe.local.site
	payload = {
		"origin_site": origin_site,
		"origin_name": doc.name,
		"event": event,
		"status": getattr(doc, "status", None),
		"principal_code": getattr(doc, "principal_code", None)
		or (
			frappe.db.get_value("Principal", doc.principal, "code")
			if getattr(doc, "principal", None)
			else None
		),
		"dealer_code": getattr(doc, "dealer_code", None)
		or (
			frappe.db.get_value("Dealer", doc.dealer, "code")
			if getattr(doc, "dealer", None)
			else get_party_code()
		),
	}
	if doc.doctype == "Principal Order":
		payload.update(
			{
				"order_date": str(doc.order_date) if doc.order_date else None,
				"order_type": doc.order_type,
				"net_total": doc.net_total,
				"vin": doc.vin,
				"chassis_number": doc.chassis_number,
				"items": [
					{
						"item_code": row.item_code,
						"item_name": row.item_name,
						"description": row.description,
						"qty": row.qty,
						"rate": row.rate,
						"amount": row.amount,
						"delivered_qty": row.delivered_qty,
					}
					for row in (doc.get("items") or [])
				],
			}
		)
	elif doc.doctype == "Warranty Claim":
		payload.update(
			{
				"claim_date": str(doc.claim_date) if doc.claim_date else None,
				"vin": doc.vin,
				"chassis_number": doc.chassis_number,
				"odometer": doc.odometer,
				"failure_description": doc.failure_description,
				"claim_amount": doc.claim_amount,
				"items": [
					{
						"item_code": row.item_code,
						"item_name": row.item_name,
						"description": row.description,
						"qty": row.qty,
						"amount": row.amount,
					}
					for row in (doc.get("items") or [])
				],
			}
		)
	elif doc.doctype == "Dealer Circular":
		payload.update(
			{
				"title": doc.title,
				"body": doc.body,
				"audience": doc.audience,
				"published": 1,
				"recipient_codes": [
					row.dealer_code for row in (doc.get("recipients") or []) if row.dealer_code
				],
			}
		)
	return payload


def _ensure_log(log_name, connection, doc, event, payload, direction):
	serialized = json.dumps(payload, default=str)[:PAYLOAD_TRUNCATE]
	if log_name and frappe.db.exists("Portal Sync Log", log_name):
		log = frappe.get_doc("Portal Sync Log", log_name)
		log.request_payload = serialized
		log.status = "Queued"
		log.save(ignore_permissions=True)
		return log
	log = frappe.get_doc(
		{
			"doctype": "Portal Sync Log",
			"connection": connection,
			"direction": direction,
			"event": event,
			"status": "Queued",
			"reference_doctype": doc.doctype,
			"local_name": doc.name,
			"request_payload": serialized,
			"retry_count": 0,
		}
	)
	log.insert(ignore_permissions=True)
	return log


def _mark_log_success(log, result, remote_name):
	log.status = "Success"
	log.response = json.dumps(result, default=str)[:PAYLOAD_TRUNCATE]
	log.error = ""
	if remote_name:
		log.remote_name = remote_name
	log.save(ignore_permissions=True)


def _mark_log_failed(log, exc):
	log.status = "Failed"
	log.error = str(exc)[:500]
	log.retry_count = cint(log.retry_count) + 1
	log.save(ignore_permissions=True)


def _mark_doc_synced(doc, connection, remote_name):
	updates = {"sync_status": "Synced", "last_synced_at": now_datetime()}
	if remote_name:
		updates["remote_name"] = remote_name
		updates["remote_site"] = connection.site_url
	for field, value in updates.items():
		if hasattr(doc, field):
			doc.db_set(field, value, update_modified=False)
