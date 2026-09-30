# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Daily dealer alerts: overdue promises, expiring quotes, aged reservations, parts below reorder."""

import frappe
from frappe.utils import add_days, nowdate


def daily():
	users = _users_for_roles(("Service Manager", "Sales Manager", "Stock Manager", "System Manager"))
	if not users:
		return
	for row in _overdue_promises():
		_notify(
			users,
			"Repair Order",
			row.name,
			f"Repair order {row.name} is past its promise date",
		)
	for row in _expiring_quotes():
		_notify(
			users,
			"Vehicle Sales Quote",
			row.name,
			f"Quote {row.name} expires on {row.valid_till}",
		)
	for row in _aged_reservations():
		_notify(
			users,
			"Vehicle Unit",
			row.name,
			f"Vehicle {row.name} has been reserved for more than 14 days",
		)
	for row in _below_reorder():
		_notify(
			users,
			"Item",
			row.item_code,
			f"Part {row.item_code} is below its reorder level",
		)


def _users_for_roles(roles):
	return frappe.db.sql_list(
		"""
		select distinct parent
		from `tabHas Role`
		where parenttype = 'User' and role in %(roles)s
		""",
		{"roles": roles},
	)


def _overdue_promises():
	return frappe.db.sql(
		"""
		select name from `tabRepair Order`
		where docstatus < 2
			and status not in ('Completed', 'Cancelled')
			and expected_completion_date is not null
			and expected_completion_date < now()
		limit 50
		""",
		as_dict=True,
	)


def _expiring_quotes():
	return frappe.db.sql(
		"""
		select name, valid_till from `tabVehicle Sales Quote`
		where docstatus = 1 and status = 'Open'
			and valid_till is not null
			and valid_till >= %s and valid_till <= %s
		limit 50
		""",
		(nowdate(), add_days(nowdate(), 7)),
		as_dict=True,
	)


def _aged_reservations():
	if not frappe.db.has_column("Vehicle Unit", "reserved_on"):
		return []
	return frappe.db.sql(
		"""
		select name from `tabVehicle Unit`
		where status = 'Reserved' and reserved_on is not null
			and reserved_on < %s
		limit 50
		""",
		add_days(nowdate(), -14),
		as_dict=True,
	)


def _below_reorder():
	if not frappe.db.table_exists("Item Reorder"):
		return []
	return frappe.db.sql(
		"""
		select ir.parent as item_code
		from `tabItem Reorder` ir
		left join `tabBin` b on b.item_code = ir.parent and b.warehouse = ir.warehouse
		where ifnull(b.actual_qty, 0) < ir.warehouse_reorder_level
			and ir.warehouse_reorder_level > 0
		limit 50
		""",
		as_dict=True,
	)


def _notify(users, document_type, document_name, subject):
	for user in users:
		if not user or user == "Guest":
			continue
		exists = frappe.db.exists(
			"Notification Log",
			{
				"for_user": user,
				"document_type": document_type,
				"document_name": document_name,
				"subject": subject,
			},
		)
		if exists:
			continue
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"document_type": document_type,
				"document_name": document_name,
				"subject": subject,
				"from_user": "Administrator",
			}
		).insert(ignore_permissions=True)
