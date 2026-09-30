// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Deal Gross"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
		},
		{ fieldname: "make", label: __("Make"), fieldtype: "Link", options: "Vehicle Make" },
		{
			fieldname: "salesperson",
			label: __("Sales Person"),
			fieldtype: "Link",
			options: "Sales Person",
		},
	],
};
