// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Open Repair Orders"] = {
	"filters": [
		{"fieldname": "customer", "label": __("Customer"), "fieldtype": "Link", "options": "Customer"},
		{"fieldname": "status", "label": __("Status"), "fieldtype": "Select", "options": ["", "Draft", "In Progress", "Paint"]},
		{"fieldname": "service_order_type", "label": __("Service Order Type"), "fieldtype": "Link", "options": "Service Order Type"}
	]
};
