// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Repair Order Aging"] = {
	"filters": [
		{"fieldname": "customer", "label": __("Customer"), "fieldtype": "Link", "options": "Customer"},
		{"fieldname": "min_days", "label": __("Open At Least (Days)"), "fieldtype": "Int", "default": 0}
	]
};
