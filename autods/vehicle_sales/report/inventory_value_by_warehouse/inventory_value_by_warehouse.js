// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Inventory Value by Warehouse"] = {
	"filters": [
		{"fieldname": "warehouse", "label": __("Warehouse"), "fieldtype": "Link", "options": "Warehouse"},
		{"fieldname": "status", "label": __("Status"), "fieldtype": "Select", "options": ["", "Available", "Reserved", "Sold", "In Service"]}
	]
};
