// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

function autods_st_clear_charge_item_row(row) {
	row.item = '';
	row.item_name = '';
	row.service_type = '';
	row.uom = '';
	row.rate = 0;
	row.amount = 0;
	row.standard_hours = 0;
	row.qty = 0;
}

/** Item link search: Service Job items, Spareparts by vehicle model (Frappe 16). */
function autods_st_charges_item_query(doc, row) {
	var t = (row && row.service_item_type || '').trim();
	if (t === 'Spareparts') {
		if (!doc.vehicle_model) {
			frappe.msgprint(__('Set Vehicle Model before selecting spare parts.'));
			return { filters: { name: ['in', []] } };
		}
		return {
			query: 'autods.service.queries.spareparts_item_link_query',
			filters: { vehicle_model: doc.vehicle_model },
		};
	}
	if (t === 'Service') {
		return {
			filters: {
				custom_service_job_item: 1,
				custom_service_item_type: 'Service',
			},
		};
	}
	if (t === 'Overhead') {
		return {
			filters: {
				custom_service_job_item: 1,
				custom_service_item_type: 'Overhead',
			},
		};
	}
	return {};
}

frappe.ui.form.on('Service Template', {
	vehicle_model: function(frm) {
		if (frm.fields_dict.charges) {
			frm.refresh_field('charges');
		}
	},
	refresh: function(frm) {
		if (frm.fields_dict.charges) {
			frm.set_query('item', 'charges', function(doc, cdt, cdn) {
				return autods_st_charges_item_query(doc, locals[cdt][cdn]);
			});
		}
	},
});

frappe.ui.form.on('Service Template Charges', {
	service_item_type: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		autods_st_clear_charge_item_row(row);
		frm.refresh_field('charges');
	},
	standard_hours: function(frm, cdt, cdn) {
		/* Standard Hours is labor/planning only; does not affect Amount (Qty x Rate). */
	},
	rate: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		var t = (row.service_item_type || '').trim();
		if (t === 'Service' || t === 'Spareparts' || t === 'Overhead') {
			row.amount = (parseFloat(row.qty) || 0) * (parseFloat(row.rate) || 0);
		}
		frm.refresh_field('charges');
	},
	qty: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		var t = (row.service_item_type || '').trim();
		if (t === 'Service' || t === 'Spareparts' || t === 'Overhead') {
			row.amount = (parseFloat(row.qty) || 0) * (parseFloat(row.rate) || 0);
			frm.refresh_field('charges');
		}
	},
});
