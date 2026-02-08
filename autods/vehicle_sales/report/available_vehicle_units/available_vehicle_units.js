// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Available Vehicle Units"] = {
	"filters": [
		{"fieldname": "status", "label": __("Status"), "fieldtype": "Select", "options": ["", "Available", "Reserved", "Sold", "In Service"], "default": "Available"},
		{"fieldname": "warehouse", "label": __("Warehouse"), "fieldtype": "Link", "options": "Warehouse"},
		{"fieldname": "make", "label": __("Make"), "fieldtype": "Link", "options": "Vehicle Make"},
		{"fieldname": "model", "label": __("Model"), "fieldtype": "Link", "options": "Vehicle Model"}
	]
};
