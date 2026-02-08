// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Parts Consumption Cost Trend"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.month_start(), -11)},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.month_end()},
		{"fieldname": "period", "label": __("Group By"), "fieldtype": "Select", "options": ["Monthly", "Yearly"], "default": "Monthly"}
	]
};
