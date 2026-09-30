// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Comebacks"] = {
	filters: [
		{ fieldname: "window_days", label: __("Window (Days)"), fieldtype: "Int", default: 30 },
	],
};
