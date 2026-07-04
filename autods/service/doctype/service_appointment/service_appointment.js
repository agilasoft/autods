// Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Service Appointment', {
	refresh: function(frm) {
		if (frm.doc.__islocal) return;

		var submitted = frm.doc.docstatus === 1;
		var allowed = submitted && ['Confirmed', 'In Progress'].indexOf(frm.doc.status) >= 0;

		if (allowed && !frm.doc.repair_estimate) {
			frm.add_custom_button(__('Create Repair Estimate'), function() {
				frappe.confirm(
					__('Create a new Repair Estimate from this appointment?'),
					function() {
						frm.call({
							doc: frm.doc,
							method: 'create_repair_estimate',
							callback: function(r) {
								if (r.message) {
									frappe.set_route('Form', 'Repair Estimate', r.message);
								}
							}
						});
					}
				);
			}, __('Create'));
		}

		if (allowed && !frm.doc.repair_order) {
			frm.add_custom_button(__('Create Repair Order'), function() {
				frappe.confirm(
					__('Create a new Repair Order from this appointment?'),
					function() {
						frm.call({
							doc: frm.doc,
							method: 'create_repair_order',
							callback: function(r) {
								if (r.message) {
									frappe.set_route('Form', 'Repair Order', r.message);
								}
							}
						});
					}
				);
			}, __('Create'));
		}

		if (frm.doc.repair_estimate) {
			frm.add_custom_button(__('Open Repair Estimate'), function() {
				frappe.set_route('Form', 'Repair Estimate', frm.doc.repair_estimate);
			}, __('View'));
		}
		if (frm.doc.repair_order) {
			frm.add_custom_button(__('Open Repair Order'), function() {
				frappe.set_route('Form', 'Repair Order', frm.doc.repair_order);
			}, __('View'));
		}
	},
	appointment_date: function(frm) {
		// Optional: set default start/end time for new appointments
	}
});
