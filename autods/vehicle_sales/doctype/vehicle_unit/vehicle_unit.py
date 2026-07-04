# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class VehicleUnit(Document):
	def validate(self):
		self.update_current_cost()
		self.update_cost_summary()

	def update_current_cost(self):
		"""
		Compute current cost from the Vehicle Cost Ledger (sum of submitted entries:
		Base/Freight/Landed Cost/Accessory/Installation/Adjustment/Opening add to cost,
		COGS subtracts). Falls back to ``purchase_price`` if no ledger entries exist.
		"""
		if not self.name:
			# New (unsaved) doc; just keep current_cost as-is or fallback
			if not flt(self.current_cost) and flt(self.purchase_price):
				self.current_cost = flt(self.purchase_price, 2)
			return
		rows = frappe.get_all(
			"Vehicle Cost Ledger",
			filters={"vehicle_unit": self.name, "docstatus": 1},
			fields=["cost_type", "amount"],
		)
		if not rows:
			if flt(self.purchase_price):
				self.current_cost = flt(self.purchase_price, 2)
			return
		total = 0.0
		for r in rows:
			amt = flt(r.amount, 2)
			if r.cost_type == "COGS":
				total -= amt
			else:
				total += amt
		self.current_cost = flt(total, 2)

	def update_cost_summary(self):
		"""Set total accessory/config cost from Vehicle Cost Ledger and total unit cost."""
		accessory_total = 0.0
		if self.name:
			rows = frappe.get_all(
				"Vehicle Cost Ledger",
				filters={
					"vehicle_unit": self.name,
					"docstatus": 1,
					"cost_type": ["in", ["Accessory", "Installation"]],
				},
				fields=["amount"],
			)
			accessory_total = sum(flt(r.amount, 2) for r in rows)
		# Fall back to the configured accessories child rows if no ledger entries exist
		if not accessory_total:
			accessory_total = sum(flt(row.total_cost, 2) for row in (self.accessories or []))
		self.total_accessory_cost = flt(accessory_total, 2)
		# Total unit cost reflects the Vehicle Cost Ledger which already includes accessory entries.
		# When no ledger exists, fall back to base + accessory cost.
		ledger_based = self.name and frappe.db.exists(
			"Vehicle Cost Ledger", {"vehicle_unit": self.name, "docstatus": 1}
		)
		if ledger_based:
			self.total_unit_cost = flt(self.current_cost, 2)
		else:
			self.total_unit_cost = flt(self.current_cost, 2) + flt(accessory_total, 2)
