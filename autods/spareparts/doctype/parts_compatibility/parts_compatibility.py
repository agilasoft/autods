# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PartsCompatibility(Document):
	def validate(self):
		if self.applies_to_all_vehicles:
			self.vehicle_make = None
			self.vehicle_model = None
			self.vehicle_variant = None
			self.transmission_type = None
			self.year_from = None
			self.year_to = None
		elif not self._has_vehicle_scope():
			frappe.throw(
				_(
					"Set Applies to All Vehicles or specify at least one vehicle attribute "
					"(Make, Model, Variant, Transmission Type, or Year range)."
				)
			)

		if self.year_from and self.year_to and int(self.year_from) > int(self.year_to):
			frappe.throw(_("Year From cannot be greater than Year To."))

	def _has_vehicle_scope(self):
		return any(
			[
				self.vehicle_make,
				self.vehicle_model,
				self.vehicle_variant,
				self.transmission_type,
				self.year_from,
				self.year_to,
			]
		)
