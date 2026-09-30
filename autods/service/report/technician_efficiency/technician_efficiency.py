# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
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
			"label": _("Work Area"),
			"fieldtype": "Link",
			"options": "Work Area",
			"width": 140,
		},
		{"fieldname": "standard_hours", "label": _("Standard Hours"), "fieldtype": "Float", "width": 130},
		{"fieldname": "attended_hours", "label": _("Attended Hours"), "fieldtype": "Float", "width": 130},
		{"fieldname": "efficiency", "label": _("Efficiency %"), "fieldtype": "Percent", "width": 110},
	]
	data = get_data(filters)
	return columns, data, None, get_chart(data)


def get_data(filters):
	conditions = ["j.docstatus < 2"]
	values = {}
	if filters.get("from_date"):
		conditions.append("j.repair_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("j.repair_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("technician"):
		conditions.append("j.technician = %(technician)s")
		values["technician"] = filters["technician"]
	if filters.get("work_area"):
		conditions.append("j.work_area = %(work_area)s")
		values["work_area"] = filters["work_area"]
	rows = frappe.db.sql(
		"""
		select j.technician, j.work_area,
			sum(ifnull(c.standard_hours, 0)) as standard_hours,
			sum(ifnull(j.work_details_total_hours, ifnull(j.total_hours, 0))) as attended_hours
		from `tabJob Card` j
		left join `tabRepair Order Charges` c on c.name = j.service_charge_row
		where {where}
		group by j.technician, j.work_area
		""".format(where=" and ".join(conditions)),
		values,
		as_dict=True,
	)
	kept = []
	for row in rows:
		attended = flt(row.attended_hours)
		standard = flt(row.standard_hours)
		if not attended and not standard:
			continue
		row.standard_hours = standard
		row.attended_hours = attended
		row.efficiency = round(100 * standard / attended, 1) if attended else 0
		kept.append(row)
	kept.sort(key=lambda row: row.efficiency, reverse=True)
	return kept


def get_chart(data):
	if not data:
		return None
	top = data[:12]
	return {
		"data": {
			"labels": [row.technician or _("Unassigned") for row in top],
			"datasets": [{"name": _("Efficiency %"), "values": [row.efficiency for row in top]}],
		},
		"type": "bar",
		"height": 280,
	}
