# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now, getdate, get_time
from datetime import datetime, timedelta


class GatePass(Document):
	def validate(self):
		self.update_status()
		self.validate_entry_exit()
	
	def update_status(self):
		"""Update status based on entry and exit information"""
		if self.entry_date and self.entry_time and self.exit_date and self.exit_time:
			self.status = "Completed"
		elif self.entry_date and self.entry_time:
			self.status = "Entry Only"
		elif self.exit_date and self.exit_time:
			self.status = "Exit Only"
	
	def validate_entry_exit(self):
		"""Validate that exit is after entry"""
		if self.entry_date and self.exit_date:
			entry_time = self.entry_time or get_time("00:00:00")
			exit_time = self.exit_time or get_time("00:00:00")
			
			# Convert timedelta to time if needed
			if isinstance(entry_time, timedelta):
				entry_time = (datetime.min + entry_time).time()
			if isinstance(exit_time, timedelta):
				exit_time = (datetime.min + exit_time).time()
			
			entry_datetime = datetime.combine(getdate(self.entry_date), entry_time)
			exit_datetime = datetime.combine(getdate(self.exit_date), exit_time)
			
			if exit_datetime < entry_datetime:
				frappe.throw(_("Exit Date/Time must be after Entry Date/Time"))
		
		if self.entry_odometer and self.exit_odometer:
			if self.exit_odometer < self.entry_odometer:
				frappe.msgprint(_("Warning: Exit odometer reading is less than entry reading"))
	
	@frappe.whitelist()
	def validate(self):
		self.update_status()
		self.validate_entry_exit()
		# Auto-fetch vehicle details from linked Repair Order
		if self.repair_order and not self.vehicle_unit:
			vehicle = frappe.db.get_value("Repair Order", self.repair_order, "vehicle_unit")
			if vehicle:
				self.vehicle_unit = vehicle
	
	@frappe.whitelist()
	def record_entry(self):
		"""Record vehicle entry"""
		if not self.entry_date:
			self.entry_date = getdate()
		if not self.entry_time:
			self.entry_time = get_time(now())
		if not self.entry_guard:
			self.entry_guard = frappe.session.user
		
		self.update_status()
		self.save()
		frappe.msgprint(_("Entry recorded for Gate Pass {0}").format(
			frappe.bold(self.name)
		))
	
	@frappe.whitelist()
	def record_exit(self):
		"""Record vehicle exit"""
		if not self.entry_date:
			frappe.throw(_("Please record entry first"))
		
		if not self.exit_date:
			self.exit_date = getdate()
		if not self.exit_time:
			self.exit_time = get_time(now())
		if not self.exit_guard:
			self.exit_guard = frappe.session.user
		
		self.update_status()
		self.save()
		frappe.msgprint(_("Exit recorded for Gate Pass {0}").format(
			frappe.bold(self.name)
		))
