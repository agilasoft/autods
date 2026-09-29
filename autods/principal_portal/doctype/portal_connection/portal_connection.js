// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Portal Connection", {
	refresh: function (frm) {
		if (frm.is_new()) {
			return;
		}
		frm.add_custom_button(__("Test Connection"), function () {
			frm.call({
				doc: frm.doc,
				method: "test_connection",
				freeze: true,
				freeze_message: __("Calling counterpart handshake..."),
				callback: function () {
					frm.reload_doc();
				},
			});
		});
	},
});
