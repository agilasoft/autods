// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vehicle Sales Quote', {
	refresh: function(frm) {
		if (frm.doc.docstatus !== 1) {
			return;
		}

		if (['Cancelled', 'Lost', 'Expired', 'Ordered'].indexOf(frm.doc.status) >= 0) {
			return;
		}

		frm.add_custom_button(__('Sales Order'), function() {
			frappe.model.open_mapped_doc({
				method: 'autods.vehicle_sales.doctype.vehicle_sales_quote.vehicle_sales_quote.make_sales_order',
				frm: frm,
			});
		}, __('Create'));
	},
});
