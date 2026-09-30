# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate


def execute(filters=None):
	filters = filters or {}
	day = filters.get("scheduled_date") or nowdate()
	columns = [
		{
			"fieldname": "technician",
			"label": _("Technician"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 160,
		},
		{
			"fieldname": "work_area",
			"label": _("Bay"),
			"fieldtype": "Link",
			"options": "Work Area",
			"width": 140,
		},
		{
			"fieldname": "job_card",
			"label": _("Job Card"),
			"fieldtype": "Link",
			"options": "Job Card",
			"width": 140,
		},
		{
			"fieldname": "repair_order",
			"label": _("Repair Order"),
			"fieldtype": "Link",
			"options": "Repair Order",
			"width": 140,
		},
		{"fieldname": "plate_no", "label": _("Plate"), "fieldtype": "Data", "width": 100},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "scheduled_start_time", "label": _("Start"), "fieldtype": "Time", "width": 90},
		{"fieldname": "scheduled_end_time", "label": _("End"), "fieldtype": "Time", "width": 90},
	]
	data = frappe.db.sql(
		"""
		select technician, work_area, job_card, repair_order, plate_no, status,
			scheduled_start_time, scheduled_end_time
		from `tabShopFloor Schedule`
		where docstatus < 2 and status != 'Cancelled' and scheduled_date = %(day)s
		order by scheduled_start_time, technician
		""",
		{"day": day},
		as_dict=True,
	)
	return columns, data
