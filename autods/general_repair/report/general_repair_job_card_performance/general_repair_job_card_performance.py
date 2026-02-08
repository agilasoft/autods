# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_datetime, time_diff_in_hours


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "job_card",
			"label": _("Job Card"),
			"fieldtype": "Link",
			"options": "Job Card",
			"width": 120
		},
		{
			"fieldname": "repair_order",
			"label": _("Repair Order"),
			"fieldtype": "Link",
			"options": "Repair Order",
			"width": 150
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "plate_no",
			"label": _("Plate No"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "technician",
			"label": _("Technician"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120
		},
		{
			"fieldname": "work_area",
			"label": _("Work Area"),
			"fieldtype": "Link",
			"options": "Work Area",
			"width": 120
		},
		{
			"fieldname": "service_category",
			"label": _("Service Category"),
			"fieldtype": "Link",
			"options": "Service Category",
			"width": 150
		},
		{
			"fieldname": "repair_type",
			"label": _("Repair Type"),
			"fieldtype": "Link",
			"options": "Repair Type",
			"width": 120
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "repair_date",
			"label": _("Repair Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "expected_completion_date",
			"label": _("Expected Completion"),
			"fieldtype": "Datetime",
			"width": 150
		},
		{
			"fieldname": "actual_completion_date",
			"label": _("Actual Completion"),
			"fieldtype": "Datetime",
			"width": 150
		},
		{
			"fieldname": "total_hours",
			"label": _("Total Hours"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "on_time",
			"label": _("On Time"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "delay_hours",
			"label": _("Delay Hours"),
			"fieldtype": "Float",
			"width": 100
		}
	]


def get_data(filters):
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT 
			jc.name as job_card,
			jc.repair_order,
			jc.customer,
			jc.plate_no,
			jc.technician,
			jc.work_area,
			jc.service_category,
			jc.repair_type,
			jc.status,
			jc.repair_date,
			jc.expected_completion_date,
			jc.actual_completion_date,
			jc.total_hours,
			CASE 
				WHEN jc.expected_completion_date IS NOT NULL 
					AND jc.actual_completion_date IS NOT NULL 
					AND jc.actual_completion_date <= jc.expected_completion_date 
				THEN 'Yes'
				WHEN jc.expected_completion_date IS NOT NULL 
					AND jc.actual_completion_date IS NOT NULL 
					AND jc.actual_completion_date > jc.expected_completion_date 
				THEN 'No'
				ELSE 'N/A'
			END as on_time,
			CASE 
				WHEN jc.expected_completion_date IS NOT NULL 
					AND jc.actual_completion_date IS NOT NULL 
					AND jc.actual_completion_date > jc.expected_completion_date 
				THEN TIMESTAMPDIFF(HOUR, jc.expected_completion_date, jc.actual_completion_date)
				ELSE 0
			END as delay_hours
		FROM `tabJob Card` jc
		WHERE {conditions}
		ORDER BY jc.repair_date DESC, jc.name DESC
	"""
	
	return frappe.db.sql(query, as_dict=1)


def get_conditions(filters):
	conditions = ["jc.repair_order IS NOT NULL"]
	
	if filters.get("from_date"):
		conditions.append(f"jc.repair_date >= '{filters.get('from_date')}'")
	
	if filters.get("to_date"):
		conditions.append(f"jc.repair_date <= '{filters.get('to_date')}'")
	
	if filters.get("technician"):
		conditions.append(f"jc.technician = '{filters.get('technician')}'")
	
	if filters.get("work_area"):
		conditions.append(f"jc.work_area = '{filters.get('work_area')}'")
	
	if filters.get("status"):
		conditions.append(f"jc.status = '{filters.get('status')}'")
	
	if filters.get("service_category"):
		conditions.append(f"jc.service_category = '{filters.get('service_category')}'")
	
	return " AND ".join(conditions) if conditions else "1=1"
