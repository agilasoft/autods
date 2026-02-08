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
		"""Update current cost from Stock Ledger Entry for serial number (inventory valuation)."""
		if self.code and self.warehouse:
			valuation_rate = frappe.db.get_value(
				"Stock Ledger Entry",
				{
					"serial_no": self.code,
					"warehouse": self.warehouse
				},
				"valuation_rate",
				order_by="posting_date desc, posting_time desc, creation desc"
			)
			if valuation_rate is not None:
				self.current_cost = valuation_rate
			elif flt(self.purchase_price):
				self.current_cost = self.purchase_price

	def update_cost_summary(self):
		"""Set total accessory/config cost and total unit cost (base + accessories)."""
		total_accessory = sum(flt(row.total_cost, 2) for row in (self.accessories or []))
		self.total_accessory_cost = total_accessory
		base = flt(self.current_cost, 2) or flt(self.purchase_price, 2)
		self.total_unit_cost = base + total_accessory