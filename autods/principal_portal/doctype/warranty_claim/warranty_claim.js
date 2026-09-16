// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Warranty Claim", {
	refresh: function (frm) {
		if (frm.doc.docstatus !== 1) {
			return;
		}
		const transitions = {
			Submitted: ["Under Review", "Approved", "Rejected"],
			"Under Review": ["Approved", "Rejected"],
			Approved: ["Settled", "Rejected"],
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
});
