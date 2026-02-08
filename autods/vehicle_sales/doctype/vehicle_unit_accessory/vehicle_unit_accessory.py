# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class VehicleUnitAccessory(Document):
	def validate(self):
		self.set_total_cost()

	def set_total_cost(self):
		"""Total cost = (unit_cost * qty) + installation_cost. Fetch from Vehicle Accessory if not set."""
		qty = flt(self.qty, 2) or 1
		unit_cost = flt(self.unit_cost, 2)
		installation_cost = flt(self.installation_cost, 2)
		if self.accessory:
			acc = frappe.db.get_value(
				"Vehicle Accessory",
				self.accessory,
				["default_price", "installation_cost"],
				as_dict=True,
			)
			if acc:
				if not unit_cost:
					unit_cost = flt(acc.default_price, 2)
					self.unit_cost = unit_cost
				if not installation_cost:
					installation_cost = flt(acc.installation_cost, 2)
					self.installation_cost = installation_cost
		self.total_cost = (unit_cost * qty) + installation_cost
