// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Open Orders Parts Demand"] = {
	"filters": [
		{"fieldname": "item", "label": __("Item"), "fieldtype": "Link", "options": "Item"}
	]
};
