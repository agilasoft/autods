# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Custom number-card methods for the service desk."""

import frappe
from frappe.utils import flt, now_datetime, nowdate, time_diff_in_hours


@frappe.whitelist()
def overdue_promise_count(filters=None):
	return frappe.db.sql(
		"""
		select count(*)
		from `tabRepair Order`
		where docstatus < 2
			and status not in ('Completed', 'Cancelled')
			and expected_completion_date is not null
			and expected_completion_date < %s
		""",
		now_datetime(),
	)[0][0]


@frappe.whitelist()
def waiting_on_parts_count(filters=None):
	return frappe.db.sql(
		"""
		select count(distinct r.name)
		from `tabRepair Order` r
		inner join `tabRepair Order Charges` c
			on c.parent = r.name and c.service_item_type = 'Spareparts'
		where r.docstatus < 2 and r.status not in ('Completed', 'Cancelled')
			and not exists (
				select 1 from `tabSpareparts Request` s
				where s.repair_order = r.name and s.status = 'Issued' and s.docstatus < 2
			)
		"""
	)[0][0]


@frappe.whitelist()
def uninvoiced_completed_count(filters=None):
	if not frappe.db.has_column("Sales Invoice", "repair_order"):
		return frappe.db.count("Repair Order", {"docstatus": 1, "status": "Completed"})
	return frappe.db.sql(
		"""
		select count(*)
		from `tabRepair Order` r
		where r.docstatus = 1 and r.status = 'Completed'
			and not exists (
				select 1 from `tabSales Invoice` si
				where si.repair_order = r.name and si.docstatus = 1
			)
		"""
	)[0][0]


@frappe.whitelist()
def bay_utilization_today(filters=None):
	opens = "08:00:00"
	closes = "17:00:00"
	if frappe.db.exists("DocType", "Service Settings"):
		opens = frappe.db.get_single_value("Service Settings", "planning_shop_opens") or opens
		closes = frappe.db.get_single_value("Service Settings", "planning_shop_closes") or closes
	day_hours = time_diff_in_hours(str(closes), str(opens)) or 8
	rows = frappe.db.sql(
		"""
		select s.scheduled_start_time, s.scheduled_end_time, ifnull(w.capacity, 1) as capacity
		from `tabShopFloor Schedule` s
		left join `tabWork Area` w on w.name = s.work_area
		where s.docstatus < 2 and s.status != 'Cancelled' and s.scheduled_date = %s
		""",
		nowdate(),
		as_dict=True,
	)
	if not rows:
		return 0
	scheduled = 0
	for row in rows:
		hours = 0
		if row.scheduled_start_time and row.scheduled_end_time:
			hours = time_diff_in_hours(str(row.scheduled_end_time), str(row.scheduled_start_time)) or 0
		scheduled += max(hours, 0)
	areas = frappe.db.sql(
		"""
		select w.name, ifnull(w.capacity, 1) as capacity
		from `tabWork Area` w
		where exists (
			select 1 from `tabShopFloor Schedule` s
			where s.work_area = w.name and s.scheduled_date = %s and s.docstatus < 2 and s.status != 'Cancelled'
		)
		""",
		nowdate(),
		as_dict=True,
	)
	available = sum((flt(area.capacity) or 1) * day_hours for area in areas) or day_hours
	return round(100 * scheduled / available, 1) if available else 0


@frappe.whitelist()
def open_repair_order_count(filters=None):
	return frappe.db.sql(
		"""
		select count(*) from `tabRepair Order`
		where docstatus < 2 and status not in ('Completed', 'Cancelled')
		"""
	)[0][0]
