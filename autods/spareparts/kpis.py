# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Custom number-card methods for the parts counter."""

import frappe
from frappe.utils import flt


@frappe.whitelist()
def open_demand_lines(filters=None):
	return frappe.db.sql(
		"""
		select count(*)
		from `tabRepair Order Charges` c
		inner join `tabRepair Order` r on r.name = c.parent
		where c.service_item_type = 'Spareparts'
			and r.docstatus < 2
			and r.status not in ('Completed', 'Cancelled')
		"""
	)[0][0]


@frappe.whitelist()
def short_line_count(filters=None):
	from autods.spareparts.report.short_parts.short_parts import get_data

	return len(get_data())


@frappe.whitelist()
def spareparts_stock_value(filters=None):
	warehouse = None
	if frappe.db.exists("DocType", "Spareparts Settings"):
		warehouse = frappe.db.get_single_value("Spareparts Settings", "default_spareparts_warehouse")
	if not warehouse or not frappe.db.table_exists("Bin"):
		return 0
	value = frappe.db.sql(
		"""
		select coalesce(sum(actual_qty * valuation_rate), 0)
		from `tabBin` where warehouse = %s
		""",
		warehouse,
	)[0][0]
	return round(flt(value), 2)


@frappe.whitelist()
def consumption_this_month(filters=None):
	return frappe.db.sql(
		"""
		select coalesce(sum(c.amount), 0)
		from `tabRepair Order Charges` c
		inner join `tabRepair Order` r on r.name = c.parent
		where c.service_item_type = 'Spareparts' and r.docstatus = 1
			and year(r.repair_date) = year(curdate()) and month(r.repair_date) = month(curdate())
		"""
	)[0][0]


@frappe.whitelist()
def supersession_opportunity_count(filters=None):
	from autods.spareparts.report.supersession_opportunities.supersession_opportunities import execute

	_columns, data = execute()
	return len(data)


@frappe.whitelist()
def parts_fill_rate(filters=None):
	row = frappe.db.sql(
		"""
		select sum(ifnull(si.qty, 0)) as requested,
			sum(case when s.status = 'Issued' then ifnull(si.qty, 0) else 0 end) as issued
		from `tabSpareparts Request` s
		inner join `tabSpareparts Request Item` si on si.parent = s.name
		where s.docstatus < 2 and s.status != 'Cancelled'
			and year(s.creation) = year(curdate()) and month(s.creation) = month(curdate())
		""",
		as_dict=True,
	)[0]
	requested = flt(row.requested)
	if not requested:
		return 0
	return round(100 * flt(row.issued) / requested, 1)
