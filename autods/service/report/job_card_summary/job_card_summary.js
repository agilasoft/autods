// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Job Card Summary"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.month_start()},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.month_end()},
		{"fieldname": "status", "label": __("Status"), "fieldtype": "Select", "options": ["", "Open", "Work In Progress", "On Hold", "Completed", "Cancelled"]},
		{"fieldname": "repair_order", "label": __("Repair Order"), "fieldtype": "Link", "options": "Repair Order"}
	]
};
