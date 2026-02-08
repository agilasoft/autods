frappe.query_reports["General Repair Revenue Analysis"] = {
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
			"fieldname": "group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"options": "\nDate\nCustomer\nRepair Type\nBill Type",
			"default": "Date",
			"reqd": 1
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"fieldname": "repair_type",
			"label": __("Repair Type"),
			"fieldtype": "Link",
			"options": "Repair Type"
		},
		{
			"fieldname": "bill_type",
			"label": __("Bill Type"),
			"fieldtype": "Select",
			"options": "\nCustomer\nInsurance\nWarranty"
		}
	]
};
