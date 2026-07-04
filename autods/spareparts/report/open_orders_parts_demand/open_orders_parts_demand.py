# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "item", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 140},
		{"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "total_qty", "label": _("Total Qty Required"), "fieldtype": "Float", "width": 120},
		{"fieldname": "order_count", "label": _("Open Orders"), "fieldtype": "Int", "width": 100},
		{"fieldname": "total_amount", "label": _("Estimated Amount"), "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = ["r.docstatus in (0, 1)", "r.status not in ('Completed', 'Cancelled')"]
	values = {}
	if filters.get("item"):
		conditions.append("p.item = %(item)s")
		values["item"] = filters["item"]
	where = " and ".join(conditions)
	query = f"""
		select
			p.item,
			max(p.item_name) as item_name,
			sum(p.qty) as total_qty,
			count(distinct p.parent) as order_count,
			sum(ifnull(p.amount, 0)) as total_amount
		from `tabRepair Order Charges` p
		inner join `tabRepair Order` r on r.name = p.parent
		where p.service_item_type = 'Spareparts' and {where}
		group by p.item
		order by total_qty desc
	"""
	return frappe.db.sql(query, values, as_dict=1)
