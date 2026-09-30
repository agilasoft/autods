# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns = [
		{"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 140},
		{"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "demand_qty", "label": _("Open Demand"), "fieldtype": "Float", "width": 110},
		{"fieldname": "stock_qty", "label": _("Bin Qty"), "fieldtype": "Float", "width": 100},
		{"fieldname": "short_qty", "label": _("Short Qty"), "fieldtype": "Float", "width": 100},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 150,
		},
		{
			"fieldname": "last_purchase_rate",
			"label": _("Last Purchase Rate"),
			"fieldtype": "Currency",
			"width": 140,
		},
	]
	return columns, get_data(), None, None


def get_data():
	demand = frappe.db.sql(
		"""
		select c.item as item_code, i.item_name, sum(ifnull(c.qty, 0)) as demand_qty,
			i.last_purchase_rate
		from `tabRepair Order Charges` c
		inner join `tabRepair Order` r on r.name = c.parent and c.parenttype = 'Repair Order'
		left join `tabItem` i on i.name = c.item
		where c.service_item_type = 'Spareparts'
			and r.docstatus < 2
			and r.status not in ('Completed', 'Cancelled')
			and c.item is not null and c.item != ''
		group by c.item
		""",
		as_dict=True,
	)
	if not demand:
		return []
	codes = [row.item_code for row in demand]
	bins = (
		frappe.db.sql(
			"""
		select item_code, sum(actual_qty) as stock_qty
		from `tabBin`
		where item_code in %(codes)s
		group by item_code
		""",
			{"codes": codes},
			as_dict=True,
		)
		if frappe.db.table_exists("Bin")
		else []
	)
	stock = {row.item_code: flt(row.stock_qty) for row in bins}
	suppliers = {}
	if frappe.db.table_exists("Item Supplier"):
		for row in frappe.db.sql(
			"""
			select parent as item_code, supplier
			from `tabItem Supplier`
			where parent in %(codes)s
			order by idx
			""",
			{"codes": codes},
			as_dict=True,
		):
			suppliers.setdefault(row.item_code, row.supplier)
	out = []
	for row in demand:
		on_hand = stock.get(row.item_code, 0)
		short = flt(row.demand_qty) - on_hand
		if short <= 0:
			continue
		row.stock_qty = on_hand
		row.short_qty = short
		row.supplier = suppliers.get(row.item_code)
		out.append(row)
	out.sort(key=lambda row: row.short_qty, reverse=True)
	return out
