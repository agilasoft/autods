# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Lead conversion overrides for AutoDS CRM."""

import frappe
from frappe.contacts.doctype.contact.contact import (
	get_contact_name,
	get_contact_with_phone_number,
)
from erpnext.crm.doctype.lead.lead import make_opportunity as erpnext_make_opportunity


@frappe.whitelist()
def make_opportunity(source_name, target_doc=None):
	"""Map Lead → Opportunity and ensure Primary Contact → Contact Person is set.

	ERPNext already maps lead_name → contact_display and only sets contact_person when a
	Contact is linked to the Lead. This override fills contact_person from the Lead's
	Full Name by finding or creating a Contact.
	"""
	target_doc = erpnext_make_opportunity(source_name, target_doc)
	_ensure_contact_person(source_name, target_doc)
	return target_doc


def _ensure_contact_person(lead_name: str, opportunity) -> None:
	if getattr(opportunity, "contact_person", None):
		return

	lead = frappe.get_doc("Lead", lead_name)
	if not (lead.lead_name or lead.first_name):
		return

	try:
		contact_name = _resolve_contact_for_lead(lead)
		if not contact_name:
			return
		opportunity.contact_person = contact_name
		if not opportunity.contact_display and lead.lead_name:
			opportunity.contact_display = lead.lead_name
	except Exception:
		frappe.log_error(
			title="AutoDS Lead→Opportunity Contact Person",
			message=frappe.get_traceback(),
		)


def _resolve_contact_for_lead(lead) -> str | None:
	"""Find or create a Contact for the Lead; prefer linked / email / mobile / name."""
	linked = frappe.get_all(
		"Dynamic Link",
		{
			"link_doctype": "Lead",
			"link_name": lead.name,
			"parenttype": "Contact",
		},
		pluck="parent",
		limit=1,
	)
	if linked:
		return linked[0]

	if lead.email_id:
		contact = get_contact_name(lead.email_id)
		if contact:
			_link_contact_to_lead(contact, lead)
			return contact

	if lead.mobile_no:
		contact = get_contact_with_phone_number(lead.mobile_no)
		if contact:
			_link_contact_to_lead(contact, lead)
			return contact

	# Covers Contact created by the convert dialog but not linked to the Lead
	name_filters = {"first_name": lead.first_name or lead.lead_name}
	if lead.last_name:
		name_filters["last_name"] = lead.last_name
	contact = frappe.db.get_value("Contact", name_filters, "name")
	if contact:
		_link_contact_to_lead(contact, lead)
		return contact

	contact_doc = lead.create_contact()
	if not contact_doc:
		return None
	_link_contact_to_lead(contact_doc.name, lead)
	return contact_doc.name


def _link_contact_to_lead(contact_name: str, lead) -> None:
	contact = frappe.get_doc("Contact", contact_name)
	already_linked = any(
		row.link_doctype == "Lead" and row.link_name == lead.name
		for row in (contact.get("links") or [])
	)
	if already_linked:
		return

	contact.append(
		"links",
		{
			"link_doctype": "Lead",
			"link_name": lead.name,
			"link_title": lead.lead_name,
		},
	)
	contact.flags.ignore_permissions = True
	contact.save()
