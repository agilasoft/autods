// Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Gate Pass', {
	refresh: function(frm) {
		// Add button to record entry
		if (!frm.doc.entry_date || !frm.doc.entry_time) {
			frm.add_custom_button(__('Record Entry'), function() {
				frm.call({
					method: 'record_entry',
					callback: function() {
						frm.reload_doc();
					}
				});
			});
		}
		
		// Add button to record exit
		if (frm.doc.entry_date && frm.doc.entry_time && (!frm.doc.exit_date || !frm.doc.exit_time)) {
			frm.add_custom_button(__('Record Exit'), function() {
				frm.call({
					method: 'record_exit',
					callback: function() {
						frm.reload_doc();
					}
				});
			});
		}
	},
	
	repair_order: function(frm) {
		if (frm.doc.repair_order) {
			frappe.db.get_value('Repair Order', frm.doc.repair_order, 
				['customer', 'vehicle_unit', 'plate_no'], function(r) {
				if (r) {
					frm.set_value('customer', r.customer);
					frm.set_value('vehicle_unit', r.vehicle_unit);
					frm.set_value('plate_no', r.plate_no);
				}
			});
		}
	}
});
