// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Principal Order", {
	refresh: function (frm) {
		if (frm.doc.docstatus !== 1) {
			return;
		}
		const transitions = {
			Submitted: ["Confirmed"],
			Confirmed: ["Partially Delivered", "Delivered", "Closed"],
			"Partially Delivered": ["Delivered", "Closed"],
			Delivered: ["Closed"],
		};
		(transitions[frm.doc.status] || []).forEach(function (status) {
			frm.add_custom_button(
				__(status),
				function () {
					frm.call({
						doc: frm.doc,
						method: "update_status",
						args: { status: status },
						freeze: true,
						callback: function () {
							frm.reload_doc();
						},
					});
				},
				__("Update Status")
			);
		});
	},
	items_add: function (frm) {
		frm.trigger("compute_amount");
	},
});

frappe.ui.form.on("Principal Order Item", {
	qty: function (frm, cdt, cdn) {
		set_amount(cdt, cdn);
		frm.refresh_field("items");
	},
	rate: function (frm, cdt, cdn) {
		set_amount(cdt, cdn);
		frm.refresh_field("items");
	},
});

function set_amount(cdt, cdn) {
	const row = locals[cdt][cdn];
	row.amount = flt(row.qty) * flt(row.rate);
}
