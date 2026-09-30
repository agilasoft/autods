# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Customer portal API: appointment requests, estimate approval, and document status."""

import frappe
from frappe import _
from frappe.utils import today


def customer_for_session():
	user = frappe.session.user
	if not user or user == "Guest":
		return None
	rows = frappe.db.sql(
		"""
		select dl.link_name
		from `tabContact Email` ce
		inner join `tabDynamic Link` dl on dl.parent = ce.parent and dl.parenttype = 'Contact'
		where ce.email_id = %s and dl.link_doctype = 'Customer'
		limit 1
		""",
		user,
	)
	return rows[0][0] if rows else None


@frappe.whitelist(allow_guest=True)
def request_service_appointment(customer_name, mobile, vehicle, concern):
	"""Create a Lead so the workshop can book the visit. Guests cannot open a repair order."""
	if not customer_name or not concern:
		frappe.throw(_("Name and concern are required."))
	lead = frappe.get_doc(
		{
			"doctype": "Lead",
			"lead_name": customer_name,
			"mobile_no": mobile,
			"status": "Lead",
		}
	)
	lead.insert(ignore_permissions=True)
	lead.add_comment("Comment", f"Vehicle: {vehicle or ''}\nConcern: {concern}")
	return {"lead": lead.name}


@frappe.whitelist()
def get_my_service_documents():
	customer = customer_for_session()
	if not customer:
		frappe.throw(_("No customer is linked to this user."), frappe.PermissionError)
	return {
		"customer": customer,
		"estimates": frappe.get_all(
			"Repair Estimate",
			filters={"customer": customer, "docstatus": 1},
			fields=["name", "status", "estimate_date", "grand_total", "vehicle_unit"],
			order_by="estimate_date desc",
			limit=20,
			ignore_permissions=True,
		),
		"repair_orders": frappe.get_all(
			"Repair Order",
			filters={"customer": customer, "docstatus": ["<", 2]},
			fields=[
				"name",
				"status",
				"repair_date",
				"grand_total",
				"expected_completion_date",
				"vehicle_unit",
			],
			order_by="repair_date desc",
			limit=20,
			ignore_permissions=True,
		),
		"invoices": _invoices(customer),
		"gate_passes": frappe.get_all(
			"Gate Pass",
			filters={"customer": customer},
			fields=["name", "status", "gate_pass_type", "vehicle_unit"],
			order_by="modified desc",
			limit=10,
			ignore_permissions=True,
		)
		if frappe.db.table_exists("Gate Pass")
		else [],
	}


def _invoices(customer):
	fields = ["name", "posting_date", "grand_total", "outstanding_amount", "status"]
	filters = {"customer": customer, "docstatus": 1}
	return frappe.get_all(
		"Sales Invoice",
		filters=filters,
		fields=fields,
		order_by="posting_date desc",
		limit=20,
		ignore_permissions=True,
	)


@frappe.whitelist()
def approve_estimate(estimate):
	customer = customer_for_session()
	if not customer:
		frappe.throw(_("No customer is linked to this user."), frappe.PermissionError)
	row = frappe.db.get_value("Repair Estimate", estimate, ["customer", "docstatus", "status"], as_dict=True)
	if not row:
		frappe.throw(_("Estimate {0} was not found.").format(estimate))
	if row.customer != customer:
		frappe.throw(_("This estimate belongs to another customer."), frappe.PermissionError)
	if row.docstatus != 1:
		frappe.throw(_("Only a submitted estimate can be approved."))
	if row.status not in ("Submitted", "Approved"):
		frappe.throw(_("Estimate {0} cannot be approved from status {1}.").format(estimate, row.status))
	frappe.db.set_value("Repair Estimate", estimate, "status", "Approved")
	return {"name": estimate, "status": "Approved", "approved_on": today()}
