# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Custom number-card methods for vehicle sales."""

import frappe
from frappe.utils import add_days, date_diff, flt, getdate, nowdate


@frappe.whitelist()
def reserved_over_14_days(filters=None):
	cutoff = add_days(nowdate(), -14)
	if frappe.db.has_column("Vehicle Unit", "reserved_on"):
		return frappe.db.sql(
			"""
			select count(*) from `tabVehicle Unit`
			where status = 'Reserved' and reserved_on is not null and date(reserved_on) <= %s
			""",
			cutoff,
		)[0][0]
	return frappe.db.count("Vehicle Unit", {"status": "Reserved"})


@frappe.whitelist()
def delivered_this_month(filters=None):
	return frappe.db.sql(
		"""
		select count(*) from `tabVehicle Delivery Note`
		where docstatus = 1
			and year(posting_date) = year(curdate()) and month(posting_date) = month(curdate())
		"""
	)[0][0]


@frappe.whitelist()
def average_days_to_sell(filters=None):
	rows = frappe.db.sql(
		"""
		select d.posting_date,
			coalesce(min(r.posting_date), v.purchase_date) as received_on
		from `tabVehicle Delivery Note` d
		inner join `tabVehicle Unit` v on v.name = d.vehicle_unit
		left join `tabVehicle Receiving` r on r.vehicle_unit = v.name and r.docstatus = 1
		where d.docstatus = 1
			and year(d.posting_date) = year(curdate()) and month(d.posting_date) = month(curdate())
		group by d.name
		""",
		as_dict=True,
	)
	if not rows:
		return 0
	days = []
	for row in rows:
		if row.posting_date and row.received_on:
			days.append(date_diff(getdate(row.posting_date), getdate(row.received_on)))
	if not days:
		return 0
	return round(sum(days) / len(days), 1)


@frappe.whitelist()
def gross_this_month(filters=None):
	rows = frappe.db.sql(
		"""
		select d.net_total, d.discount_amount, abs(ifnull(l.amount, 0)) as cost
		from `tabVehicle Delivery Note` d
		left join `tabVehicle Cost Ledger` l
			on l.voucher_no = d.name and l.voucher_type = 'Vehicle Delivery Note'
			and l.cost_type = 'COGS' and l.docstatus = 1
		where d.docstatus = 1
			and year(d.posting_date) = year(curdate()) and month(d.posting_date) = month(curdate())
		""",
		as_dict=True,
	)
	return round(sum((flt(row.net_total) - flt(row.discount_amount) - flt(row.cost)) for row in rows), 2)


@frappe.whitelist()
def gross_margin_percent_this_month(filters=None):
	rows = frappe.db.sql(
		"""
		select d.net_total, d.discount_amount, abs(ifnull(l.amount, 0)) as cost
		from `tabVehicle Delivery Note` d
		left join `tabVehicle Cost Ledger` l
			on l.voucher_no = d.name and l.voucher_type = 'Vehicle Delivery Note'
			and l.cost_type = 'COGS' and l.docstatus = 1
		where d.docstatus = 1
			and year(d.posting_date) = year(curdate()) and month(d.posting_date) = month(curdate())
		""",
		as_dict=True,
	)
	selling = sum(flt(row.net_total) - flt(row.discount_amount) for row in rows)
	gross = sum((flt(row.net_total) - flt(row.discount_amount) - flt(row.cost)) for row in rows)
	if not selling:
		return 0
	return round(100 * gross / selling, 1)


@frappe.whitelist()
def quotes_expiring_this_week(filters=None):
	return frappe.db.sql(
		"""
		select count(*) from `tabVehicle Sales Quote`
		where docstatus = 1 and status = 'Open'
			and valid_till is not null
			and valid_till >= curdate()
			and valid_till <= date_add(curdate(), interval 7 day)
		"""
	)[0][0]
