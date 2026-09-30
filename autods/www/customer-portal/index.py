# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe

no_cache = 1


def get_context(context):
	context.no_cache = 1
	user = frappe.session.user
	context.guest = user == "Guest"
	context.estimates = []
	context.repair_orders = []
	context.invoices = []
	context.gate_passes = []
	if context.guest:
		return
	from autods.portal import customer_for_session, get_my_service_documents

	if not customer_for_session():
		context.guest = True
		context.portal_message = (
			"Sign in with the email on your customer contact to see estimates and invoices."
		)
		return
	docs = get_my_service_documents()
	context.estimates = docs["estimates"]
	context.repair_orders = docs["repair_orders"]
	context.invoices = docs["invoices"]
	context.gate_passes = docs["gate_passes"]
