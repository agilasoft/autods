# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, time_diff_in_hours


class JobCard(Document):
	def validate(self):
		self.calculate_total_hours()

	def calculate_total_hours(self):
		"""Calculate total hours from start and end time"""
		if self.start_time and self.end_time:
			start = get_datetime(self.start_time)
			end = get_datetime(self.end_time)
			if end > start:
				self.total_hours = time_diff_in_hours(end, start)
			else:
				frappe.throw(_("End Time must be greater than Start Time"))

	def on_update(self):
		"""Update completion date when status is Completed"""
		if self.status == "Completed" and not self.actual_completion_date:
			self.actual_completion_date = frappe.utils.now()
			if not self.end_time:
				self.end_time = frappe.utils.now()

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
		technicians = frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			fields=["name", "employee_name"]
		)
		return technicians

	@frappe.whitelist()
	def create_material_request(self):
		"""Create Material Request (Material Issue) from Job Card. Items from Repair Order spareparts.
		References: Material Request -> job_card, repair_order (no Spareparts Request).
		"""
		if not self.name:
			frappe.throw(_("Please save the Job Card first"))
		if not self.repair_order:
			frappe.throw(_("Repair Order is required to create a Material Request"))

		ro = frappe.get_doc("Repair Order", self.repair_order)
		spareparts = getattr(ro, "spareparts", None) or []
		if not spareparts:
			frappe.throw(_("Add items in the Repair Order Spareparts table first"))

		material_request = _create_material_request_from_repair_order(
			repair_order=self.repair_order,
			job_card=self.name,
			items=spareparts,
		)
		frappe.msgprint(_("Material Request {0} created for issue.").format(
			frappe.bold(material_request.name)
		))
		return {"doctype": material_request.doctype, "name": material_request.name}

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
			completion_dt = get_datetime(self.expected_completion_date)
			shopfloor_schedule.scheduled_start_time = completion_dt.time()
			from datetime import timedelta
			shopfloor_schedule.scheduled_end_time = (completion_dt + timedelta(hours=1)).time()

		shopfloor_schedule.status = "Scheduled"
		shopfloor_schedule.insert()

		frappe.msgprint(_("ShopFloor Schedule {0} created").format(
			frappe.bold(shopfloor_schedule.name)
		))
		return {"doctype": shopfloor_schedule.doctype, "name": shopfloor_schedule.name}

	@frappe.whitelist()
	def check_technician_availability(self, technician, start_date, end_date):
		"""Check if technician is available for the given time period"""
		return check_technician_availability(technician, start_date, end_date, self.name)


def _create_material_request_from_repair_order(repair_order, job_card, items):
	"""Create Material Request (Material Issue) from Repair Order spareparts. References: job_card, repair_order."""
	from frappe.utils import getdate, nowdate
	try:
		import erpnext
	except ImportError:
		erpnext = None

	material_request = frappe.new_doc("Material Request")
	material_request.material_request_type = "Material Issue"
	material_request.job_card = job_card
	material_request.repair_order = repair_order
	material_request.schedule_date = getdate(nowdate())

	# Company from item warehouses so MR company matches (avoid InvalidWarehouseCompany)
	company = None
	companies = set()
	for row in items:
		wh = getattr(row, "warehouse", None)
		if wh:
			wh_company = frappe.db.get_value("Warehouse", wh, "company")
			if wh_company:
				companies.add(wh_company)
				if company is None:
					company = wh_company
	if len(companies) > 1:
		frappe.throw(_("All item warehouses must belong to the same company. Found: {0}").format(", ".join(companies)))
	if not company:
		company = erpnext.get_default_company() if erpnext else frappe.db.get_single_value("Global Defaults", "default_company")
	if company:
		material_request.company = company

	for row in items:
		item_code = getattr(row, "item", None)
		if not item_code:
			continue
		uom = getattr(row, "uom", None) or frappe.db.get_value("Item", item_code, "stock_uom")
		material_request.append("items", {
			"item_code": item_code,
			"qty": row.qty or 1,
			"uom": uom,
			"warehouse": getattr(row, "warehouse", None),
			"schedule_date": material_request.schedule_date,
		})

	material_request.insert()
	return material_request


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
