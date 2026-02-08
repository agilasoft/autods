// Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Spareparts Request', {
	refresh: function(frm) {
		// Add approve/reject buttons
		if (frm.doc.status === 'Requested' || frm.doc.status === 'Draft') {
			frm.add_custom_button(__('Approve'), function() {
				frm.call({
					method: 'approve_request',
					callback: function() {
						frm.reload_doc();
					}
				});
			}, __('Actions'));
			
			frm.add_custom_button(__('Reject'), function() {
				frm.call({
					method: 'reject_request',
					callback: function() {
						frm.reload_doc();
					}
				});
			}, __('Actions'));
		}
		
		// Add button to create material request
		if (frm.doc.status === 'Approved' && frm.doc.items && frm.doc.items.length > 0) {
			frm.add_custom_button(__('Create Material Request'), function() {
				frm.call({
					method: 'make_material_request',
					callback: function(r) {
						if (r.message) {
							frappe.set_route('Form', 'Material Request', r.message.name);
						}
					}
				});
			});
		}
	},
	
	job_card: function(frm) {
		if (frm.doc.job_card) {
			frappe.db.get_value('Job Card', frm.doc.job_card, 'repair_order', function(r) {
				if (r && r.repair_order) {
					frm.set_value('repair_order', r.repair_order);
				}
			});
		}
	}
});
