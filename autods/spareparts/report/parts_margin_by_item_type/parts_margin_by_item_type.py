# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "item_type", "label": _("Item Type"), "fieldtype": "Data", "width": 140},
		{"fieldname": "qty", "label": _("Qty"), "fieldtype": "Float", "width": 90},
		{"fieldname": "sales_amount", "label": _("Sales"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "cost_amount", "label": _("Valuation Cost"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "margin", "label": _("Margin"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "margin_percent", "label": _("Margin %"), "fieldtype": "Percent", "width": 100},
	]
	conditions = ["r.docstatus = 1", "c.service_item_type = 'Spareparts'"]
	values = {}
	if filters.get("from_date"):
		conditions.append("r.repair_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("r.repair_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	rows = frappe.db.sql(
		"""
		select ifnull(c.item_type, 'Other') as item_type,
			sum(ifnull(c.qty, 0)) as qty,
			sum(ifnull(c.amount, 0)) as sales_amount,
			sum(ifnull(c.qty, 0) * ifnull(i.valuation_rate, 0)) as cost_amount
		from `tabRepair Order Charges` c
		inner join `tabRepair Order` r on r.name = c.parent and c.parenttype = 'Repair Order'
		left join `tabItem` i on i.name = c.item
		where {where}
		group by item_type
		""".format(where=" and ".join(conditions)),
		values,
		as_dict=True,
	)
	for row in rows:
		row.margin = flt(row.sales_amount) - flt(row.cost_amount)
		row.margin_percent = (
			round(100 * row.margin / flt(row.sales_amount), 1) if flt(row.sales_amount) else 0
		)
	chart = None
	if rows:
		chart = {
			"data": {
				"labels": [row.item_type for row in rows],
				"datasets": [
					{"name": _("Sales"), "values": [flt(row.sales_amount) for row in rows]},
					{"name": _("Cost"), "values": [flt(row.cost_amount) for row in rows]},
				],
			},
			"type": "bar",
			"height": 280,
		}
	return columns, rows, None, chart
