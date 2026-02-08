// Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Service Inspection', {
	refresh: function(frm) {
		// Load items from template
		if (frm.doc.service_inspection_template && (!frm.doc.inspection_items || frm.doc.inspection_items.length === 0)) {
			frm.add_custom_button(__('Load from Template'), function() {
				if (frm.doc.service_inspection_template) {
					frm.call({
						method: 'load_from_template',
						args: {
							template_name: frm.doc.service_inspection_template
						},
						callback: function(r) {
							frm.reload_doc();
						}
					});
				} else {
					frappe.msgprint(__('Please select a Service Inspection Template first'));
				}
			});
		}
	}
});
