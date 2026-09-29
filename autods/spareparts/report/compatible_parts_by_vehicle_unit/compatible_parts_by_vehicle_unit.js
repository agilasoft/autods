// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.query_reports["Compatible Parts by Vehicle Unit"] = {
	filters: [
		{
			fieldname: "vehicle_unit",
			label: __("Vehicle Unit"),
			fieldtype: "Link",
			options: "Vehicle Unit",
			reqd: 1,
		},
	],
};
