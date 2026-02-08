frappe.query_reports["General Repair Job Card Performance"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "technician",
			"label": __("Technician"),
			"fieldtype": "Link",
			"options": "Employee"
		},
		{
			"fieldname": "work_area",
			"label": __("Work Area"),
			"fieldtype": "Link",
			"options": "Work Area"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nOpen\nWork In Progress\nOn Hold\nCompleted\nCancelled"
		},
		{
			"fieldname": "service_category",
			"label": __("Service Category"),
			"fieldtype": "Link",
			"options": "Service Category"
		}
	]
};
