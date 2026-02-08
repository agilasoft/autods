// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Vehicle Units In Service"] = {
	"filters": [
		{"fieldname": "make", "label": __("Make"), "fieldtype": "Link", "options": "Vehicle Make"}
	]
};
