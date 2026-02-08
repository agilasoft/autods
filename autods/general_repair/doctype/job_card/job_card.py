# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, time_diff_in_hours


class JobCard(Document):
	def validate(self):
		self.calculate_total_hours()
		self.validate_work_area_availability()
	
	def calculate_total_hours(self):
		"""Calculate total hours from start and end time"""
		if self.start_time and self.end_time:
			start = get_datetime(self.start_time)
			end = get_datetime(self.end_time)
			if end > start:
				self.total_hours = time_diff_in_hours(end, start)
			else:
				frappe.throw(_("End Time must be greater than Start Time"))
	
	def validate_work_area_availability(self):
		"""Validate if work area is available for the scheduled time"""
		if self.work_area and self.repair_date and self.expected_completion_date:
			# Check for overlapping schedules
			overlapping = frappe.db.sql("""
				SELECT name 
				FROM `tabJob Card`
				WHERE work_area = %s
				AND name != %s
				AND status NOT IN ('Completed', 'Cancelled')
				AND (
					(repair_date <= %s AND expected_completion_date >= %s)
					OR (repair_date <= %s AND expected_completion_date >= %s)
				)
			""", (self.work_area, self.name or '', 
				  self.repair_date, self.repair_date,
				  self.expected_completion_date, self.expected_completion_date))
			
			if overlapping:
				frappe.throw(_("Work Area {0} is already scheduled for this time period").format(
					frappe.bold(self.work_area)
				))
	
	def on_update(self):
		"""Update status and completion date"""
		if self.status == "Completed" and not self.actual_completion_date:
			self.actual_completion_date = frappe.utils.now()
			if not self.end_time:
				self.end_time = frappe.utils.now()
		
		# Update Repair Order if it has a job_cards child table (e.g. for dashboard sync)
		repair_order = getattr(self, "repair_order", None)
		if repair_order:
			self._update_repair_order_job_card()
	
	def _update_repair_order_job_card(self):
		"""Update job card status on Repair Order if it has job_cards child table."""
		repair_order = getattr(self, "repair_order", None)
		if not repair_order:
			return
		try:
			ro_doc = frappe.get_doc("Repair Order", repair_order)
			updated = False
			if hasattr(ro_doc, "job_cards") and ro_doc.job_cards:
				for jc in ro_doc.job_cards:
					if jc.job_card == self.name:
						jc.status = self.status
						jc.technician = self.technician
						jc.work_area = self.work_area
						updated = True
						break
			if updated:
				ro_doc.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(f"Error updating Repair Order job card: {str(e)}")
	
	@frappe.whitelist()
	def assign_technician_by_skills(self):
		"""Assign technician based on required skills group"""
		if not self.technician_skills_group:
			frappe.throw(_("Please select Required Skills Group first"))
		
		# Get skills from the skills group
		skills_group = frappe.get_doc("Technician Skills Group", self.technician_skills_group)
		required_skills = [skill.skill_name for skill in skills_group.skills]
		
		if not required_skills:
			frappe.msgprint(_("No skills defined in the selected skills group"))
			return []
		
		# Get all active technicians
		technicians = frappe.get_all("Employee", 
			filters={"status": "Active"},
			fields=["name", "employee_name"])
		
		# For now, return all active technicians
		# In a real implementation, you would match against employee skills
		# This requires a custom Employee Skill DocType or using a different approach
		return technicians
	
	@frappe.whitelist()
	def create_spareparts_request(self):
		"""Create Spareparts Request from Job Card"""
		if not self.name:
			frappe.throw(_("Please save the Job Card first"))
		
		spareparts_request = frappe.new_doc("Spareparts Request")
		spareparts_request.job_card = self.name
		spareparts_request.repair_order = self.repair_order
		spareparts_request.requested_by = self.technician
		spareparts_request.status = "Draft"
		
		spareparts_request.insert()
		
		frappe.msgprint(_("Spareparts Request {0} created").format(
			frappe.bold(spareparts_request.name)
		))
		
		# Return dict with doctype and name for JavaScript
		return {
			"doctype": spareparts_request.doctype,
			"name": spareparts_request.name
		}
	
	@frappe.whitelist()
	def create_shopfloor_schedule(self):
		"""Create ShopFloor Schedule from Job Card"""
		if not self.name:
			frappe.throw(_("Please save the Job Card first"))
		
		if not self.work_area:
			frappe.throw(_("Please select Work Area first"))
		
		if not self.repair_date:
			frappe.throw(_("Please select Repair Date first"))
		
		shopfloor_schedule = frappe.new_doc("ShopFloor Schedule")
		shopfloor_schedule.job_card = self.name
		shopfloor_schedule.repair_order = self.repair_order
		shopfloor_schedule.work_area = self.work_area
		shopfloor_schedule.vehicle_unit = self.vehicle_unit
		shopfloor_schedule.plate_no = self.plate_no
		shopfloor_schedule.technician = self.technician
		shopfloor_schedule.scheduled_date = self.repair_date
		
		if self.expected_completion_date:
			from frappe.utils import get_datetime
			completion_dt = get_datetime(self.expected_completion_date)
			shopfloor_schedule.scheduled_start_time = completion_dt.time()
			# Default end time as 1 hour after start
			from datetime import timedelta
			shopfloor_schedule.scheduled_end_time = (completion_dt + timedelta(hours=1)).time()
		
		shopfloor_schedule.status = "Scheduled"
		
		shopfloor_schedule.insert()
		
		frappe.msgprint(_("ShopFloor Schedule {0} created").format(
			frappe.bold(shopfloor_schedule.name)
		))
		
		# Return dict with doctype and name for JavaScript
		return {
			"doctype": shopfloor_schedule.doctype,
			"name": shopfloor_schedule.name
		}
	
	@frappe.whitelist()
	def check_technician_availability(self, technician, start_date, end_date):
		"""Check if technician is available for the given time period"""
		return check_technician_availability(technician, start_date, end_date, self.name)


@frappe.whitelist()
def check_technician_availability(technician, start_date, end_date, docname=None):
	"""Check if technician is available for the given time period (module-level for RPC)."""
	overlapping = frappe.db.sql("""
		SELECT name, status
		FROM `tabJob Card`
		WHERE technician = %s
		AND (name != %s OR %s IS NULL)
		AND status NOT IN ('Completed', 'Cancelled')
		AND (
			(repair_date <= %s AND expected_completion_date >= %s)
			OR (repair_date <= %s AND expected_completion_date >= %s)
		)
	""", (technician, docname or '', docname, start_date, start_date, end_date, end_date))
	
	return {
		"available": len(overlapping) == 0,
		"overlapping_jobs": overlapping
	}
