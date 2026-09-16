// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Dealer Performance"] = {
	filters: [{ fieldname: "dealer", label: __("Dealer"), fieldtype: "Link", options: "Dealer" }],
};
