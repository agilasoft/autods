frappe.query_reports["Repair Order Detailed"] = {
	"filters": [
		{
			"fieldname": "order_number",
			"label": __("Order Number"),
			"fieldtype": "Link",
			"options": "Repair Order"
		},
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
