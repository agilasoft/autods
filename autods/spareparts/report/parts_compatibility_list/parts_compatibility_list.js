// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Parts Compatibility List"] = {
	"filters": [
		{"fieldname": "part", "label": __("Part"), "fieldtype": "Link", "options": "Item"},
		{"fieldname": "vehicle_make", "label": __("Vehicle Make"), "fieldtype": "Link", "options": "Vehicle Make"},
		{"fieldname": "vehicle_model", "label": __("Vehicle Model"), "fieldtype": "Link", "options": "Vehicle Model"}
	]
};
