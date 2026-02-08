// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Parts Supersession List"] = {
	"filters": [
		{"fieldname": "original_part", "label": __("Original Part"), "fieldtype": "Link", "options": "Item"},
		{"fieldname": "superseded_part", "label": __("Superseded Part"), "fieldtype": "Link", "options": "Item"},
		{"fieldname": "supersession_type", "label": __("Type"), "fieldtype": "Select", "options": ["", "Direct Replacement", "Upgrade", "Downgrade", "Alternative"]},
		{"fieldname": "status", "label": __("Status"), "fieldtype": "Select", "options": ["", "Active", "Inactive"]}
	]
};
