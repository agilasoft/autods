// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Reserved Vehicle Units"] = {
	"filters": [
		{"fieldname": "warehouse", "label": __("Warehouse"), "fieldtype": "Link", "options": "Warehouse"},
		{"fieldname": "make", "label": __("Make"), "fieldtype": "Link", "options": "Vehicle Make"}
	]
};
