// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Vehicle Sales Summary"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.month_start()},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.month_end()},
		{"fieldname": "make", "label": __("Make"), "fieldtype": "Link", "options": "Vehicle Make"},
		{"fieldname": "model", "label": __("Model"), "fieldtype": "Link", "options": "Vehicle Model"},
		{"fieldname": "customer", "label": __("Customer"), "fieldtype": "Link", "options": "Customer"}
	]
};
