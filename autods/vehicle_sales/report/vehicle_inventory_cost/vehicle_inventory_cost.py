# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt
# Vehicle inventory cost aligned with ERPNext Stock Ledger and accounting.

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "name", "label": _("Vehicle Unit"), "fieldtype": "Link", "options": "Vehicle Unit", "width": 140},
		{"fieldname": "code", "label": _("Serial / VIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "item", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 120},
		{"fieldname": "make", "label": _("Make"), "fieldtype": "Link", "options": "Vehicle Make", "width": 100},
		{"fieldname": "model", "label": _("Model"), "fieldtype": "Link", "options": "Vehicle Model", "width": 100},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 90},
		{"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 120},
		{"fieldname": "current_cost", "label": _("Inventory Cost (Cost Ledger)"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "total_accessory_cost", "label": _("Accessory/Config Cost"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_unit_cost", "label": _("Total Unit Cost"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "vehicle_receiving", "label": _("Vehicle Receiving"), "fieldtype": "Link", "options": "Vehicle Receiving", "width": 140},
		{"fieldname": "vehicle_delivery_note", "label": _("Vehicle Delivery Note"), "fieldtype": "Link", "options": "Vehicle Delivery Note", "width": 150},
		{"fieldname": "sales_invoice", "label": _("Sales Invoice"), "fieldtype": "Link", "options": "Sales Invoice", "width": 130},
	]


def get_data(filters):
	conditions = []
	values = {}
	if filters.get("status"):
		conditions.append("v.status = %(status)s")
		values["status"] = filters["status"]
	if filters.get("warehouse"):
		conditions.append("v.warehouse = %(warehouse)s")
		values["warehouse"] = filters["warehouse"]
	if filters.get("company"):
		conditions.append("v.warehouse in (select name from tabWarehouse where company = %(company)s)")
		values["company"] = filters["company"]
	where = " and " + " and ".join(conditions) if conditions else ""
	query = f"""
		select
			v.name,
			v.code,
			v.item,
			v.make,
			v.model,
			v.status,
			v.warehouse,
			v.current_cost,
			v.total_accessory_cost,
			v.total_unit_cost,
			v.vehicle_receiving,
			v.vehicle_delivery_note,
			v.sales_invoice
		from `tabVehicle Unit` v
		where 1=1 {where}
		order by v.status, v.modified desc
	"""
	return frappe.db.sql(query, values, as_dict=1)
