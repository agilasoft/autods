// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Portal Sync Log", {
	refresh: function (frm) {
		if (frm.doc.status === "Failed") {
			frm.add_custom_button(__("Retry"), function () {
				frm.call({
					doc: frm.doc,
					method: "retry",
					freeze: true,
					callback: function () {
						frm.reload_doc();
					},
				});
			});
		}
	},
});
