// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Opportunity", {
	setup(frm) {
		frm.custom_make_buttons = Object.assign(frm.custom_make_buttons || {}, {
			"Vehicle Sales Quote": "Vehicle Sales Quote",
			"Supplier Quotation": "Supplier Quotation",
		});
		delete frm.custom_make_buttons.Quotation;
	},

	refresh(frm) {
		frm.custom_make_buttons = frm.custom_make_buttons || {};
		delete frm.custom_make_buttons.Quotation;
		frm.custom_make_buttons["Vehicle Sales Quote"] = "Vehicle Sales Quote";
		if (!frm.custom_make_buttons["Supplier Quotation"]) {
			frm.custom_make_buttons["Supplier Quotation"] = "Supplier Quotation";
		}

		if (frm.cscript) {
			frm.cscript.create_quotation = () => open_vehicle_sales_quote(frm);
		}

		if (frm.is_new() || frm.doc.status === "Lost") {
			return;
		}

		frm.remove_custom_button(__("Quotation"), __("Create"));

		frm.add_custom_button(
			__("Vehicle Sales Quote"),
			() => open_vehicle_sales_quote(frm),
			__("Create")
		);
	},
});

function open_vehicle_sales_quote(frm) {
	if (frm.doc.opportunity_from === "Lead") {
		frappe.show_alert({
			message: __(
				"Please set a Customer on the Vehicle Sales Quote (or create a Customer from this Opportunity first)."
			),
			indicator: "orange",
		});
	}

	frappe.model.open_mapped_doc({
		method:
			"autods.vehicle_sales.doctype.vehicle_sales_quote.vehicle_sales_quote.make_from_opportunity",
		frm: frm,
	});
}
