// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Spareparts Request", {
	refresh: function(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.items && frm.doc.items.length > 0) {
			frm.add_custom_button(__("Create Material Request"), function() {
				frm.call({
					doc: frm.doc,
					method: "make_material_request",
					callback: function(r) {
						if (r.message && r.message.name) {
							frappe.set_route("Form", "Material Request", r.message.name);
						}
					}
				});
			}, __("Actions"));
		}
	}
});
