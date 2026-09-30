# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, flt, nowdate


def execute(filters=None):
	columns = [
		{"fieldname": "exception_type", "label": _("Exception"), "fieldtype": "Data", "width": 220},
		{"fieldname": "document_type", "label": _("Document Type"), "fieldtype": "Data", "width": 160},
		{
			"fieldname": "document_name",
			"label": _("Document"),
			"fieldtype": "Dynamic Link",
			"options": "document_type",
			"width": 160,
		},
		{"fieldname": "detail", "label": _("Detail"), "fieldtype": "Data", "width": 280},
		{"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "width": 120},
	]
	return columns, get_data()


def get_data():
	rows = []
	today = nowdate()
	soon = add_days(today, 7)
	for quote in frappe.db.sql(
		"""
		select name, party_name, valid_till, grand_total
		from `tabVehicle Sales Quote`
		where docstatus = 1 and status = 'Open'
			and valid_till is not null and valid_till >= %s and valid_till <= %s
		""",
		(today, soon),
		as_dict=True,
	):
		rows.append(
			{
				"exception_type": _("Quote expiring in 7 days"),
				"document_type": "Vehicle Sales Quote",
				"document_name": quote.name,
				"detail": f"{quote.party_name or ''} · {quote.valid_till}",
				"amount": flt(quote.grand_total),
			}
		)

	for unit in frappe.db.sql(
		"""
		select v.name, v.customer
		from `tabVehicle Unit` v
		where v.status = 'Reserved'
			and not exists (
				select 1 from `tabVehicle Sales Order` o
				where o.vehicle_unit = v.name and o.docstatus = 1 and o.delivery_date is not null
			)
		""",
		as_dict=True,
	):
		rows.append(
			{
				"exception_type": _("Reserved unit with no delivery date"),
				"document_type": "Vehicle Unit",
				"document_name": unit.name,
				"detail": unit.customer or "",
				"amount": 0,
			}
		)

	for order in frappe.db.sql(
		"""
		select distinct r.name, r.plate_no, r.customer
		from `tabRepair Order` r
		inner join `tabRepair Order Charges` c
			on c.parent = r.name and c.service_item_type = 'Spareparts'
		where r.docstatus < 2 and r.status not in ('Completed', 'Cancelled')
			and not exists (
				select 1 from `tabSpareparts Request` s
				where s.repair_order = r.name and s.status = 'Issued' and s.docstatus < 2
			)
		""",
		as_dict=True,
	):
		rows.append(
			{
				"exception_type": _("Repair order waiting on parts"),
				"document_type": "Repair Order",
				"document_name": order.name,
				"detail": f"{order.plate_no or ''} · {order.customer or ''}",
				"amount": 0,
			}
		)

	if frappe.db.has_column("Sales Invoice", "custom_repair_bill_type"):
		for invoice in frappe.db.sql(
			"""
			select name, customer, outstanding_amount, due_date
			from `tabSales Invoice`
			where docstatus = 1 and custom_repair_bill_type = 'Insurance'
				and outstanding_amount > 0 and due_date is not null and due_date < %s
			""",
			today,
			as_dict=True,
		):
			rows.append(
				{
					"exception_type": _("Insurance invoice unpaid past terms"),
					"document_type": "Sales Invoice",
					"document_name": invoice.name,
					"detail": f"{invoice.customer or ''} · due {invoice.due_date}",
					"amount": flt(invoice.outstanding_amount),
				}
			)

	for note in frappe.db.sql(
		"""
		select d.name, d.vehicle_unit, o.billing_status, d.grand_total
		from `tabVehicle Delivery Note` d
		left join `tabVehicle Sales Order` o on o.name = d.vehicle_sales_order
		where d.docstatus = 1 and ifnull(o.billing_status, 'Not Billed') != 'Fully Billed'
		""",
		as_dict=True,
	):
		rows.append(
			{
				"exception_type": _("Delivered unit not fully billed"),
				"document_type": "Vehicle Delivery Note",
				"document_name": note.name,
				"detail": f"{note.vehicle_unit or ''} · {note.billing_status or 'Not Billed'}",
				"amount": flt(note.grand_total),
			}
		)

	for unit in frappe.db.sql(
		"""
		select v.name, v.customer
		from `tabVehicle Unit` v
		where v.status = 'Reserved'
			and not exists (
				select 1 from `tabVehicle Sales Order` o
				where o.vehicle_unit = v.name and o.docstatus = 1
			)
		""",
		as_dict=True,
	):
		rows.append(
			{
				"exception_type": _("Reserved unit with no order"),
				"document_type": "Vehicle Unit",
				"document_name": unit.name,
				"detail": unit.customer or "",
				"amount": 0,
			}
		)

	if frappe.db.has_column("Sales Invoice", "repair_order"):
		for order in frappe.db.sql(
			"""
			select distinct r.name, r.status, r.customer
			from `tabRepair Order` r
			inner join `tabSales Invoice` si on si.repair_order = r.name and si.docstatus = 1
			where r.docstatus < 2 and r.status not in ('Completed', 'Cancelled')
			""",
			as_dict=True,
		):
			rows.append(
				{
					"exception_type": _("Invoiced repair order not completed"),
					"document_type": "Repair Order",
					"document_name": order.name,
					"detail": f"{order.status or ''} · {order.customer or ''}",
					"amount": 0,
				}
			)
	return rows
