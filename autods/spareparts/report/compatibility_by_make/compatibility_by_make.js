// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Compatibility by Make"] = {
	"filters": [
		{"fieldname": "vehicle_make", "label": __("Vehicle Make"), "fieldtype": "Link", "options": "Vehicle Make"}
	]
};
