# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = [
		{
			"fieldname": "repair_order",
			"label": _("Repair Order"),
			"fieldtype": "Link",
			"options": "Repair Order",
			"width": 140,
		},
		{
			"fieldname": "vehicle_unit",
			"label": _("Vehicle"),
			"fieldtype": "Link",
			"options": "Vehicle Unit",
			"width": 140,
		},
		{"fieldname": "plate_no", "label": _("Plate"), "fieldtype": "Data", "width": 100},
		{"fieldname": "item_code", "label": _("Part"), "fieldtype": "Link", "options": "Item", "width": 140},
		{"fieldname": "qty", "label": _("Qty"), "fieldtype": "Float", "width": 80},
		{
			"fieldname": "request",
			"label": _("Spareparts Request"),
			"fieldtype": "Link",
			"options": "Spareparts Request",
			"width": 160,
		},
		{"fieldname": "request_status", "label": _("Request Status"), "fieldtype": "Data", "width": 130},
	]
	return columns, get_data()


def get_data():
	return frappe.db.sql(
		"""
		select r.name as repair_order, r.vehicle_unit, r.plate_no,
			c.item as item_code, c.qty,
			s.name as request, coalesce(s.status, 'Not Requested') as request_status
		from `tabRepair Order` r
		inner join `tabRepair Order Charges` c
			on c.parent = r.name and c.parenttype = 'Repair Order' and c.service_item_type = 'Spareparts'
		left join `tabSpareparts Request` s
			on s.repair_order = r.name and s.docstatus < 2
			and s.status not in ('Cancelled', 'Rejected', 'Issued')
		where r.docstatus < 2
			and r.status not in ('Completed', 'Cancelled')
			and (
				s.name is not null
				or not exists (
					select 1 from `tabSpareparts Request` issued
					where issued.repair_order = r.name
						and issued.status = 'Issued'
						and issued.docstatus < 2
				)
			)
		order by r.name, c.item
		""",
		as_dict=True,
	)
