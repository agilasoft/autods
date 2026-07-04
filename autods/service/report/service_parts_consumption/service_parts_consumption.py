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
		{"fieldname": "item_type", "label": _("Item Type"), "fieldtype": "Data", "width": 120},
		{"fieldname": "bill_type", "label": _("Bill Type"), "fieldtype": "Data", "width": 100},
		{"fieldname": "total_qty", "label": _("Total Qty"), "fieldtype": "Float", "width": 100},
		{"fieldname": "total_amount", "label": _("Total Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "order_count", "label": _("Repair Orders"), "fieldtype": "Int", "width": 100},
	]


def get_data(filters):
	conditions = ["r.docstatus = 1"]
	values = {}
	if filters.get("from_date"):
		conditions.append("r.repair_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("r.repair_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("item"):
		conditions.append("p.item = %(item)s")
		values["item"] = filters["item"]
	if filters.get("item_type"):
		conditions.append("p.item_type = %(item_type)s")
		values["item_type"] = filters["item_type"]
	if filters.get("bill_type"):
		conditions.append("p.bill_type = %(bill_type)s")
		values["bill_type"] = filters["bill_type"]
	where = " and ".join(conditions)
	query = f"""
		select
			p.item,
			max(p.item_name) as item_name,
			p.item_type,
			p.bill_type,
			sum(p.qty) as total_qty,
			sum(ifnull(p.amount, 0)) as total_amount,
			count(distinct p.parent) as order_count
		from `tabRepair Order Charges` p
		inner join `tabRepair Order` r on r.name = p.parent
		where p.service_item_type = 'Spareparts' and {where}
		group by p.item, p.item_type, p.bill_type
		order by total_amount desc, total_qty desc
	"""
	return frappe.db.sql(query, values, as_dict=1)
