frappe.query_reports["General Repair Repair Type Analysis"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "repair_type",
			"label": __("Repair Type"),
			"fieldtype": "Link",
			"options": "Repair Type"
		}
	]
};
