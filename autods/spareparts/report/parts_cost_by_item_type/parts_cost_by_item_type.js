// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Parts Cost by Item Type"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.month_start()},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.month_end()},
		{"fieldname": "item_type", "label": __("Item Type"), "fieldtype": "Select", "options": ["", "Mechanical Part", "Body Part", "Paint Material", "Other"]}
	]
};
