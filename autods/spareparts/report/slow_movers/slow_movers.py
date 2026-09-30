# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint


def execute(filters=None):
	filters = filters or {}
	days = cint(filters.get("days")) or 90
	columns = [
		{"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 140},
		{"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 180},
		{
			"fieldname": "compatibility_rules",
			"label": _("Compatibility Rules"),
			"fieldtype": "Int",
			"width": 140,
		},
		{"fieldname": "last_used", "label": _("Last Used"), "fieldtype": "Date", "width": 110},
	]
	data = frappe.db.sql(
		"""
		select pc.part as item_code, i.item_name, count(pc.name) as compatibility_rules,
			max(r.repair_date) as last_used
		from `tabParts Compatibility` pc
		left join `tabItem` i on i.name = pc.part
		left join `tabRepair Order Charges` c
			on c.item = pc.part and c.service_item_type = 'Spareparts' and c.parenttype = 'Repair Order'
		left join `tabRepair Order` r on r.name = c.parent and r.docstatus = 1
		where ifnull(pc.is_active, 1) = 1
		group by pc.part
		having last_used is null or last_used < date_sub(curdate(), interval %(days)s day)
		order by last_used
		""",
		{"days": days},
		as_dict=True,
	)
	return columns, data
