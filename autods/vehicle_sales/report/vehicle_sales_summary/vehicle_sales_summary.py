# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt
# Sold vehicles in period with delivery and invoice links for sales performance.

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "name", "label": _("Vehicle Unit"), "fieldtype": "Link", "options": "Vehicle Unit", "width": 130},
		{"fieldname": "code", "label": _("Serial / VIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "make", "label": _("Make"), "fieldtype": "Link", "options": "Vehicle Make", "width": 100},
		{"fieldname": "model", "label": _("Model"), "fieldtype": "Link", "options": "Vehicle Model", "width": 100},
		{"fieldname": "delivery_date", "label": _("Delivery Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "delivery_note", "label": _("Delivery Note"), "fieldtype": "Link", "options": "Delivery Note", "width": 130},
		{"fieldname": "sales_invoice", "label": _("Sales Invoice"), "fieldtype": "Link", "options": "Sales Invoice", "width": 130},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 140},
		{"fieldname": "total_unit_cost", "label": _("Unit Cost"), "fieldtype": "Currency", "width": 110},
	]


def get_data(filters):
	conditions = ["v.status = 'Sold'", "v.delivery_note is not null"]
	values = {}
	if filters.get("from_date"):
		conditions.append("dn.posting_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("dn.posting_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("make"):
		conditions.append("v.make = %(make)s")
		values["make"] = filters["make"]
	if filters.get("model"):
		conditions.append("v.model = %(model)s")
		values["model"] = filters["model"]
	if filters.get("customer"):
		conditions.append("v.customer = %(customer)s")
		values["customer"] = filters["customer"]
	where = " and ".join(conditions)
	query = f"""
		select
			v.name,
			v.code,
			v.make,
			v.model,
			dn.posting_date as delivery_date,
			v.delivery_note,
			v.sales_invoice,
			v.customer,
			ifnull(v.total_unit_cost, v.current_cost) as total_unit_cost
		from `tabVehicle Unit` v
		inner join `tabDelivery Note` dn on dn.name = v.delivery_note
		where {where}
		order by dn.posting_date desc, v.modified desc
	"""
	return frappe.db.sql(query, values, as_dict=1)
