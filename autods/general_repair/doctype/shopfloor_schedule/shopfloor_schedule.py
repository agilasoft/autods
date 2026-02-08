# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ShopFloorSchedule(Document):
	def validate(self):
		self.validate_time_slot()
		self.validate_work_area_capacity()
	
	def validate_time_slot(self):
		"""Validate that end time is after start time"""
		if self.scheduled_start_time and self.scheduled_end_time:
			if self.scheduled_end_time <= self.scheduled_start_time:
				frappe.throw(_("Scheduled End Time must be after Scheduled Start Time"))
	
	def validate_work_area_capacity(self):
		"""Validate work area capacity and check for overlapping schedules"""
		if self.work_area and self.scheduled_date:
			# Get work area capacity
			work_area = frappe.get_doc("Work Area", self.work_area)
			
			# Check for overlapping schedules
			overlapping = frappe.db.sql("""
				SELECT name, status
				FROM `tabShopFloor Schedule`
				WHERE work_area = %s
				AND scheduled_date = %s
				AND name != %s
				AND status NOT IN ('Completed', 'Cancelled')
				AND (
					(scheduled_start_time <= %s AND scheduled_end_time > %s)
					OR (scheduled_start_time < %s AND scheduled_end_time >= %s)
					OR (scheduled_start_time >= %s AND scheduled_end_time <= %s)
				)
			""", (self.work_area, self.scheduled_date, self.name or '',
				  self.scheduled_start_time, self.scheduled_start_time,
				  self.scheduled_end_time, self.scheduled_end_time,
				  self.scheduled_start_time, self.scheduled_end_time))
			
			if work_area.capacity and len(overlapping) >= work_area.capacity:
				frappe.throw(_("Work Area {0} has reached its capacity of {1} vehicles").format(
					frappe.bold(self.work_area), work_area.capacity
				))
			
			if overlapping:
				frappe.msgprint(_("Warning: Work Area {0} has overlapping schedules").format(
					frappe.bold(self.work_area)
				))
