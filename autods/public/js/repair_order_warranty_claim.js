// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Repair Order", {
	refresh: function (frm) {
		if (frm.is_new()) {
			return;
		}
		frm.add_custom_button(
			__("Warranty Claim"),
			function () {
				frappe.call({
					method: "autods.principal_portal.doctype.warranty_claim.warranty_claim.create_warranty_claim_from_repair_order",
					args: { repair_order: frm.doc.name },
					freeze: true,
					freeze_message: __("Creating Warranty Claim..."),
					callback: function (r) {
						if (r.message && r.message.name) {
							frappe.set_route("Form", "Warranty Claim", r.message.name);
						}
					},
				});
			},
			__("Create")
		);
	},
});
