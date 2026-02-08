frappe.query_reports["General Repair Bill Type Analysis"] = {
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
			"options": "\nBill Type\nDate",
			"default": "Bill Type",
			"reqd": 1
		},
		{
			"fieldname": "bill_type",
			"label": __("Bill Type"),
			"fieldtype": "Select",
			"options": "\nCustomer\nInsurance\nWarranty"
		},
		{
			"fieldname": "customer",
			"label": __("Customer/Insurance Company"),
			"fieldtype": "Link",
			"options": "Customer"
		}
	]
};
