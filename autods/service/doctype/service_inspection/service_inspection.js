// Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Service Inspection', {
	refresh: function(frm) {
		autods_set_service_inspection_name_options(frm);
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
	},
	repair_order: function(frm) {
		autods_set_service_inspection_name_options(frm);
	}
});

function autods_set_service_inspection_name_options(frm) {
	if (!frm.doc.repair_order) {
		return;
	}
	frappe.call({
		method: 'autods.service.doctype.repair_order.repair_order.get_repair_order_inspection_names',
		args: { repair_order: frm.doc.repair_order },
		callback: function(r) {
			var names = (r.message || []).filter(Boolean);
			if (!names.length) {
				return;
			}
			frm.set_df_property('inspection_name', 'options', names.join('\n'));
			frm.refresh_field('inspection_name');
		}
	});
}
