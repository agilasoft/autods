# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint


def execute(filters=None):
	filters = filters or {}
	window = cint(filters.get("window_days")) or _default_window()
	columns = [
		{
			"fieldname": "repair_order",
			"label": _("Repair Order"),
			"fieldtype": "Link",
			"options": "Repair Order",
			"width": 140,
		},
		{"fieldname": "repair_date", "label": _("Repair Date"), "fieldtype": "Date", "width": 110},
		{
			"fieldname": "vehicle_unit",
			"label": _("Vehicle"),
			"fieldtype": "Link",
			"options": "Vehicle Unit",
			"width": 140,
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 160,
		},
		{
			"fieldname": "concern",
			"label": _("Concern"),
			"fieldtype": "Link",
			"options": "Repair Concern",
			"width": 160,
		},
		{
			"fieldname": "previous_order",
			"label": _("Previous Order"),
			"fieldtype": "Link",
			"options": "Repair Order",
			"width": 140,
		},
		{"fieldname": "previous_date", "label": _("Previous Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "days_between", "label": _("Days Between"), "fieldtype": "Int", "width": 110},
	]
	data = get_data(window)
	return columns, data


def _default_window():
	if frappe.db.exists("DocType", "Service Settings"):
		return cint(frappe.db.get_single_value("Service Settings", "comeback_window_days")) or 30
	return 30


def get_data(window):
	return frappe.db.sql(
		"""
		select r.name as repair_order, r.repair_date, r.vehicle_unit, r.customer,
			c.concern, prev.name as previous_order, prev.repair_date as previous_date,
			datediff(r.repair_date, prev.repair_date) as days_between
		from `tabRepair Order` r
		inner join `tabRepair Order Concerns` c on c.parent = r.name and c.parenttype = 'Repair Order'
		inner join `tabRepair Order` prev
			on prev.vehicle_unit = r.vehicle_unit
			and prev.name != r.name
			and prev.docstatus < 2
			and prev.repair_date <= r.repair_date
			and prev.repair_date >= date_sub(r.repair_date, interval %(window)s day)
		inner join `tabRepair Order Concerns` pc
			on pc.parent = prev.name and pc.parenttype = 'Repair Order' and pc.concern = c.concern
		where r.docstatus < 2 and c.concern is not null and c.concern != ''
		order by r.repair_date desc, r.name
		""",
		{"window": window},
		as_dict=True,
	)
