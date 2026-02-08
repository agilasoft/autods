frappe.query_reports["General Repair Service Items Analysis"] = {
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
			"fieldname": "service_item",
			"label": __("Service Item"),
			"fieldtype": "Link",
			"options": "Item"
		},
		{
			"fieldname": "service_category",
			"label": __("Service Category"),
			"fieldtype": "Link",
			"options": "Service Category"
		},
		{
			"fieldname": "technician",
			"label": __("Technician"),
			"fieldtype": "Link",
			"options": "Employee"
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer"
		}
	]
};
