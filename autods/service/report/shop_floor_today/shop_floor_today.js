// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Shop Floor Today"] = {
	filters: [
		{
			fieldname: "scheduled_date",
			label: __("Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
	],
};
