// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Vehicle Inventory by Status"] = {
	"filters": [
		{"fieldname": "status", "label": __("Status"), "fieldtype": "Select", "options": ["", "Available", "Reserved", "Sold", "In Service"]},
		{"fieldname": "make", "label": __("Make"), "fieldtype": "Link", "options": "Vehicle Make"},
		{"fieldname": "warehouse", "label": __("Warehouse"), "fieldtype": "Link", "options": "Warehouse"}
	]
};
