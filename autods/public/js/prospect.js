// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Prospect", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		if (!frappe.boot.user.can_create.includes("Vehicle Sales Quote")) {
			return;
		}
		frm.add_custom_button(
			__("Vehicle Sales Quote"),
			() => {
				frappe.model.open_mapped_doc({
					method:
						"autods.vehicle_sales.doctype.vehicle_sales_quote.vehicle_sales_quote.make_from_prospect",
					frm,
				});
			},
			__("Create")
		);
	},
});
