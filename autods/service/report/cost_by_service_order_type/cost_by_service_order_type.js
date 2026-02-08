// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Cost by Service Order Type"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.month_start()},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.month_end()},
		{"fieldname": "service_order_type", "label": __("Service Order Type"), "fieldtype": "Link", "options": "Service Order Type"}
	]
};
