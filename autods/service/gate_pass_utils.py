# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


ENTRY_STATUSES = ("Entry Only", "Completed")
EXIT_STATUSES = ("Exit Only", "Completed")
ACTIVE_JOB_CARD_STATUSES = ("Open", "Work In Progress", "On Hold")


def has_entry_gate_pass(vehicle_unit=None, repair_order=None, customer=None, exclude_gate_pass=None):
	"""Return True when a vehicle already has an entry/both Gate Pass for this service visit."""
	filters = [
		["Gate Pass", "status", "in", ENTRY_STATUSES],
		["Gate Pass", "gate_pass_type", "in", ("Entry", "Both")],
	]
	if exclude_gate_pass:
		filters.append(["Gate Pass", "name", "!=", exclude_gate_pass])
	if vehicle_unit:
		filters.append(["Gate Pass", "vehicle_unit", "=", vehicle_unit])
	elif customer:
		filters.append(["Gate Pass", "customer", "=", customer])
	else:
		return False
	rows = frappe.get_all("Gate Pass", filters=filters, fields=["name", "repair_order"], limit_page_length=20)
	if not repair_order:
		return bool(rows)
	return any(not row.get("repair_order") or row.get("repair_order") == repair_order for row in rows)


def require_entry_gate_pass(vehicle_unit=None, repair_order=None, customer=None, context="this service visit"):
	if has_entry_gate_pass(vehicle_unit=vehicle_unit, repair_order=repair_order, customer=customer):
		return
	frappe.throw(
		_("Create a Gate Pass Entry for {0} before proceeding with {1}.").format(
			frappe.bold(vehicle_unit or customer or _("the vehicle")),
			context,
		),
	)


def is_exit_gate_pass(gate_pass_type=None, status=None):
	"""Return True when a Gate Pass represents an exit or completed visit."""
	gate_pass_type = (gate_pass_type or "").strip()
	status = (status or "").strip()
	if gate_pass_type == "Exit":
		return True
	return status in EXIT_STATUSES


def get_open_job_cards_for_repair_order(repair_order):
	if not repair_order:
		return []
	return frappe.get_all(
		"Job Card",
		filters={
			"repair_order": repair_order,
			"status": ("in", ACTIVE_JOB_CARD_STATUSES),
		},
		fields=["name", "status"],
		order_by="name",
	)


def require_completed_job_cards_for_exit(job_card=None, repair_order=None):
	"""Block exit/completed Gate Passes until linked Job Cards are Completed."""
	if job_card:
		if not frappe.db.exists("Job Card", job_card):
			frappe.throw(_("Job Card {0} does not exist.").format(frappe.bold(job_card)))
		status = frappe.db.get_value("Job Card", job_card, "status")
		if status != "Completed":
			frappe.throw(
				_("Job Card {0} must be Completed before creating an exit/completed Gate Pass.").format(
					frappe.bold(job_card),
				),
			)
		repair_order = repair_order or frappe.db.get_value("Job Card", job_card, "repair_order")

	if not job_card and not repair_order:
		frappe.throw(
			_("Link a Repair Order or Job Card before saving an exit/completed Gate Pass."),
		)

	open_cards = get_open_job_cards_for_repair_order(repair_order)
	if open_cards:
		labels = ", ".join(f'{row["name"]} ({row["status"]})' for row in open_cards)
		frappe.throw(
			_("Complete all Job Cards before creating an exit/completed Gate Pass. Open cards: {0}").format(
				labels,
			),
		)
