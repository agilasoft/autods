# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class VehicleCostLedger(Document):
	def validate(self):
		if self.vehicle_unit and not self.company:
			# Best-effort: pick first company on this site
			self.company = frappe.defaults.get_user_default("Company") or self.company
		if not self.posting_date:
			self.posting_date = frappe.utils.getdate()

	def on_submit(self):
		recompute_vehicle_unit_cost(self.vehicle_unit)

	def on_cancel(self):
		recompute_vehicle_unit_cost(self.vehicle_unit)


def recompute_vehicle_unit_cost(vehicle_unit):
	"""
	Recompute the Vehicle Unit's current cost as the sum of all submitted
	Vehicle Cost Ledger amounts (Base/Freight/Accessory/Installation/Opening
	add to cost; COGS subtracts; Adjustment is signed by user).
	"""
	if not vehicle_unit or not frappe.db.exists("Vehicle Unit", vehicle_unit):
		return
	rows = frappe.get_all(
		"Vehicle Cost Ledger",
		filters={"vehicle_unit": vehicle_unit, "docstatus": 1},
		fields=["cost_type", "amount"],
	)
	current = 0.0
	accessory_cost = 0.0
	for r in rows:
		amt = flt(r.amount, 2)
		if r.cost_type == "COGS":
			current -= amt
		else:
			current += amt
		if r.cost_type in ("Accessory", "Installation"):
			accessory_cost += amt
	frappe.db.set_value(
		"Vehicle Unit",
		vehicle_unit,
		{
			"current_cost": current,
			"total_accessory_cost": accessory_cost,
			"total_unit_cost": current,
		},
	)


def add_entry(
	vehicle_unit,
	amount,
	cost_type,
	voucher_type=None,
	voucher_no=None,
	account=None,
	cost_center=None,
	posting_date=None,
	company=None,
	journal_entry=None,
	remarks=None,
	is_opening=0,
	submit=True,
):
	"""Programmatic helper to create + (optionally) submit a Vehicle Cost Ledger entry."""
	doc = frappe.new_doc("Vehicle Cost Ledger")
	doc.vehicle_unit = vehicle_unit
	doc.amount = flt(amount, 2)
	doc.cost_type = cost_type
	doc.voucher_type = voucher_type or "Manual"
	doc.voucher_no = voucher_no
	doc.account = account
	doc.cost_center = cost_center
	doc.posting_date = posting_date or frappe.utils.getdate()
	doc.company = company or frappe.defaults.get_user_default("Company")
	doc.journal_entry = journal_entry
	doc.remarks = remarks
	doc.is_opening = 1 if is_opening else 0
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	if submit:
		doc.submit()
	return doc
