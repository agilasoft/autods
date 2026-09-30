frappe.query_reports["Slow Movers"] = {
	filters: [
		{ fieldname: "days", label: __("No Use For (Days)"), fieldtype: "Int", default: 90 },
	],
};
