# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from autods.service.gate_pass_utils import require_completed_job_cards_for_exit


class GatePass(Document):
	def validate(self):
		self.set_missing_vehicle_details()
		self.validate_entry_exit_status()

	def set_missing_vehicle_details(self):
		if self.job_card:
			values = frappe.db.get_value(
				"Job Card",
				self.job_card,
				["repair_order", "customer", "vehicle_unit", "plate_no"],
				as_dict=True,
			)
			if values:
				self.repair_order = self.repair_order or values.repair_order
				self.customer = self.customer or values.customer
				self.vehicle_unit = self.vehicle_unit or values.vehicle_unit
				self.plate_no = self.plate_no or values.plate_no
		if self.repair_order:
			values = frappe.db.get_value(
				"Repair Order",
				self.repair_order,
				["customer", "vehicle_unit", "plate_no"],
				as_dict=True,
			)
			if values:
				self.customer = self.customer or values.customer
				self.vehicle_unit = self.vehicle_unit or values.vehicle_unit
				self.plate_no = self.plate_no or values.plate_no

	def validate_entry_exit_status(self):
		status = (self.status or "").strip()
		gate_pass_type = (self.gate_pass_type or "").strip()
		if gate_pass_type == "Entry" and status in ("Exit Only", "Completed"):
			frappe.throw(_("Gate Pass Type Entry cannot be saved as {0}.").format(status))
		if gate_pass_type == "Exit" and status == "Entry Only":
			frappe.throw(_("Gate Pass Type Exit cannot be saved as Entry Only."))
		if status not in ("Exit Only", "Completed") and gate_pass_type != "Exit":
			return
		require_completed_job_cards_for_exit(job_card=self.job_card, repair_order=self.repair_order)
