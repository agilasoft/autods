// Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

/** Item link search: Service Job items, Spareparts by vehicle specs, else Service Type match (Frappe 16). */
function autods_spareparts_vehicle_filters(doc) {
	return {
		vehicle_unit: doc.vehicle_unit,
		vehicle_make: doc.vehicle_make,
		vehicle_model: doc.vehicle_model,
		vehicle_variant: doc.vehicle_variant,
		vehicle_year_model: doc.vehicle_year_model,
		vehicle_transmission_type: doc.vehicle_transmission_type,
	};
}

function autods_charges_item_query(doc, row) {
	var t = (row && row.service_item_type || '').trim();
	if (t === 'Spareparts') {
		if (!doc.vehicle_unit && !doc.vehicle_model) {
			frappe.msgprint(__('Set a Vehicle Unit with a model before selecting spare parts.'));
			return { filters: { name: ['in', []] } };
		}
		return {
			query: 'autods.service.queries.spareparts_item_link_query',
			filters: autods_spareparts_vehicle_filters(doc),
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
	if (!doc.service_type) {
		return {};
	}
	return {
		query: 'autods.service.queries.charges_item_link_query',
		filters: { service_type: doc.service_type },
	};
}

function autods_open_repair_order_sales_invoice(frm) {
	frappe.call({
		method: 'autods.service.doctype.repair_order.repair_order.get_sales_invoice_payers',
		args: { repair_order: frm.doc.name },
		freeze: true,
		callback: function(r) {
			var payers = r.message || [];
			if (!payers.length) {
				frappe.msgprint(__('This Repair Order has no billable charges.'));
				return;
			}
			function open_payer(payer) {
				if (!payer.bill_to) {
					frappe.msgprint(__('Set the {0} customer before creating the Sales Invoice.', [payer.bill_type]));
					return;
				}
				if (payer.sales_invoice) {
					frappe.set_route('Form', 'Sales Invoice', payer.sales_invoice);
					return;
				}
				frappe.model.open_mapped_doc({
					method: 'autods.service.doctype.repair_order.repair_order.make_sales_invoice',
					frm: frm,
					args: {
						bill_type: payer.bill_type,
						bill_to: payer.bill_to,
					},
				});
			}
			if (payers.length === 1) {
				open_payer(payers[0]);
				return;
			}
			var options = payers.map(function(payer, idx) {
				var who = payer.customer_name || payer.bill_to || __('Missing customer');
				var action = payer.sales_invoice ? __('Open') : __('Create');
				return idx + ': ' + action + ' ' + payer.bill_type + ' — ' + who;
			});
			frappe.prompt([
				{
					fieldname: 'payer',
					fieldtype: 'Select',
					label: __('Bill To'),
					options: options.join('\n'),
					reqd: 1,
				},
			], function(values) {
				var idx = parseInt((values.payer || '').split(':')[0], 10);
				if (!payers[idx]) {
					return;
				}
				open_payer(payers[idx]);
			}, __('Sales Invoice'), __('Continue'));
		},
	});
}

function autods_clear_charge_item_row(row) {
	row.item = '';
	row.item_name = '';
	row.service_type = '';
	row.uom = '';
	row.rate = 0;
	row.amount = 0;
	row.standard_hours = 0;
	row.qty = 0;
	row.service_row = '';
	row.parent_service_charge = '';
}

function autods_refresh_charge_row_amount(frm, cdt, cdn) {
	var grid = frm.fields_dict.charges && frm.fields_dict.charges.grid;
	if (grid) {
		var grid_row = grid.get_row(cdn);
		if (grid_row && grid_row.refresh_field) {
			grid_row.refresh_field('amount');
			return;
		}
	}
	frm.refresh_field('charges');
}

/** Editable charge fields locked when a non-Cancelled Job Card covers the row. */
var AUTODS_JOB_CARD_LOCKED_CHARGE_FIELDS = [
	'service_item_type',
	'item',
	'description',
	'service_row',
	'standard_hours',
	'qty',
	'uom',
	'rate',
	'bill_type',
	'bill_to',
	'item_type',
	'warehouse',
	'color_code',
	'paint_type',
];

function autods_get_locked_charges_map(frm) {
	return (frm && frm._autods_locked_charges) || {};
}

function autods_is_charge_row_locked(frm, row) {
	if (!row || !row.name) {
		return false;
	}
	return !!autods_get_locked_charges_map(frm)[row.name];
}

function autods_is_service_charge_locked(frm, service_charge_row_name) {
	var name = (service_charge_row_name || '').trim();
	if (!name) {
		return false;
	}
	return !!autods_get_locked_charges_map(frm)[name];
}

function autods_set_charge_field_control_locked(fld, is_locked) {
	if (!fld) {
		return;
	}
	if (fld.df) {
		fld.df.read_only = is_locked ? 1 : 0;
	}
	if (fld.$input && fld.$input.length) {
		fld.$input.prop('disabled', !!is_locked);
		if (is_locked && fld.$input.blur) {
			fld.$input.blur();
		}
	}
	if (fld.$input_wrapper && fld.$input_wrapper.length) {
		fld.$input_wrapper.toggleClass('read-only', !!is_locked);
	}
}

function autods_apply_locked_charge_row_editability(frm) {
	var grid = frm.fields_dict.charges && frm.fields_dict.charges.grid;
	if (!grid || !grid.grid_rows) {
		return;
	}
	var locked = autods_get_locked_charges_map(frm);
	grid.grid_rows.forEach(function(gr) {
		if (!gr || !gr.doc || !gr.doc.name) {
			return;
		}
		var is_locked = !!locked[gr.doc.name];
		AUTODS_JOB_CARD_LOCKED_CHARGE_FIELDS.forEach(function(fieldname) {
			if (gr.toggle_editable) {
				gr.toggle_editable(fieldname, !is_locked);
			}
			/* Keep Select/DOM controls non-interactive after option rebuilds. */
			if (gr.on_grid_fields_dict && gr.on_grid_fields_dict[fieldname]) {
				autods_set_charge_field_control_locked(gr.on_grid_fields_dict[fieldname], is_locked);
			}
			if (gr.grid_form && gr.grid_form.fields_dict && gr.grid_form.fields_dict[fieldname]) {
				autods_set_charge_field_control_locked(gr.grid_form.fields_dict[fieldname], is_locked);
			}
		});
		if (gr.wrapper && gr.wrapper.length) {
			gr.wrapper.find('.grid-delete-row').toggle(!is_locked);
		}
	});
}

function autods_snapshot_locked_charge_rows(frm) {
	var locked = autods_get_locked_charges_map(frm);
	var snapshots = {};
	(frm.doc.charges || []).forEach(function(row) {
		if (!row || !row.name || !locked[row.name]) {
			return;
		}
		var snap = {};
		AUTODS_JOB_CARD_LOCKED_CHARGE_FIELDS.forEach(function(fieldname) {
			snap[fieldname] = row[fieldname];
		});
		snap.parent_service_charge = row.parent_service_charge;
		snapshots[row.name] = snap;
	});
	frm._autods_locked_charge_snapshots = snapshots;
}

function autods_load_locked_charge_rows(frm) {
	if (!frm || frm.is_new() || !frm.doc.name) {
		frm._autods_locked_charges = {};
		frm._autods_locked_charge_snapshots = {};
		autods_apply_locked_charge_row_editability(frm);
		return;
	}
	frappe.call({
		method: 'autods.service.doctype.repair_order.repair_order.get_locked_charge_rows',
		args: { repair_order: frm.doc.name },
		callback: function(r) {
			frm._autods_locked_charges = r.message || {};
			autods_snapshot_locked_charge_rows(frm);
			/* Refresh Service Select options first, then re-apply locks so read-only sticks. */
			if (
				window.autods &&
				autods.charges_overview &&
				autods.charges_overview.update_service_row_select_options
			) {
				autods.charges_overview.update_service_row_select_options(frm);
			}
			autods_apply_locked_charge_row_editability(frm);
		},
	});
}

function autods_guard_locked_charge_edit(frm, cdt, cdn, fieldname) {
	var row = locals[cdt] && locals[cdt][cdn];
	if (!autods_is_charge_row_locked(frm, row)) {
		return false;
	}
	var jc = autods_get_locked_charges_map(frm)[row.name];
	var snap = (frm._autods_locked_charge_snapshots || {})[row.name];
	if (fieldname && snap && Object.prototype.hasOwnProperty.call(snap, fieldname)) {
		var prev = snap[fieldname];
		if (row[fieldname] !== prev) {
			/* Assign directly to avoid re-entering this handler via set_value. */
			row[fieldname] = prev == null ? '' : prev;
			var grid = frm.fields_dict.charges && frm.fields_dict.charges.grid;
			var grid_row = grid && grid.get_row(cdn);
			if (grid_row && grid_row.refresh_field) {
				grid_row.refresh_field(fieldname);
			} else {
				frm.refresh_field('charges');
			}
		}
	}
	frappe.msgprint({
		title: __('Charges Locked'),
		indicator: 'orange',
		message: __('This charge line is locked by Job Card {0}. Cancel the Job Card to edit it.', [
			frappe.bold(jc),
		]),
	});
	return true;
}

function autods_set_repair_type_query(frm) {
	frm.set_query('repair_type', function() {
		if (!frm.doc.service_type) {
			return {};
		}
		return {
			query: 'autods.service.queries.repair_type_link_query',
			filters: { service_type: frm.doc.service_type },
		};
	});
}

frappe.ui.form.on('Repair Order', {
	setup: function(frm) {
		autods_set_repair_type_query(frm);
	},
	onload: function(frm) {
		autods.service_datetime.patch_system_datetime_control(frm, 'expected_completion_date');
	},
	service_type: function(frm) {
		autods_set_repair_type_query(frm);
		if (frm.doc.repair_type) {
			frm.set_value('repair_type', '');
		}
		if (frm.fields_dict.charges) {
			frm.refresh_field('charges');
		}
	},
	vehicle_unit: function(frm) {
		if (frm.fields_dict.charges) {
			frm.refresh_field('charges');
		}
	},
	vehicle_model: function(frm) {
		if (frm.fields_dict.charges) {
			frm.refresh_field('charges');
		}
	},
	company: function(frm) {
		if (frm.doc.company && !frm.doc.currency) {
			frappe.db.get_value('Company', frm.doc.company, 'default_currency', function(r) {
				if (r && r.default_currency) {
					frm.set_value('currency', r.default_currency);
				}
			});
		}
	},
	taxes_and_charges: function(frm) {
		if (!frm.doc.taxes_and_charges) {
			return;
		}
		var apply_template = function() {
			frappe.call({
				method: 'autods.service.doctype.repair_order.repair_order.get_tax_rows_from_template',
				args: { template: frm.doc.taxes_and_charges },
				callback: function(r) {
					frm.clear_table('sales_taxes_and_charges');
					(r.message || []).forEach(function(row) {
						var d = frm.add_child('sales_taxes_and_charges');
						Object.keys(row).forEach(function(k) {
							if (['name', 'owner', 'creation', 'modified', 'modified_by', 'docstatus', 'parent', 'parentfield', 'parenttype', 'idx'].indexOf(k) === -1) {
								d[k] = row[k];
							}
						});
					});
					frm.refresh_field('sales_taxes_and_charges');
				}
			});
		};
		if ((frm.doc.sales_taxes_and_charges || []).length) {
			frappe.confirm(__('Replace existing Sales Taxes and Charges with this template?'), apply_template);
		} else {
			apply_template();
		}
	},
	refresh: function(frm) {
		autods_set_repair_type_query(frm);
		if (frm.fields_dict.charges) {
			frm.set_query('item', 'charges', function(doc, cdt, cdn) {
				return autods_charges_item_query(doc, locals[cdt][cdn]);
			});
		}
		autods_load_locked_charge_rows(frm);
		if (!frm.is_new()) {
			frm.set_query('quality_inspection', 'quality_inspections', function(doc, cdt, cdn) {
				var row = locals[cdt][cdn];
				var filters = { repair_order: doc.name };
				if (row.inspection_name) {
					filters.inspection_name = row.inspection_name;
				}
				return { filters: filters };
			});
			var quality_inspection_field = frm.get_docfield('quality_inspections', 'quality_inspection');
			if (quality_inspection_field) {
				quality_inspection_field.get_route_options_for_new_doc = function(link_field) {
					if (frm.is_new()) {
						return {};
					}
					return {
						repair_order: frm.doc.name,
						inspection_name: (link_field.doc.inspection_name || '').trim() || undefined,
					};
				};
			}
			frm.add_custom_button(__('Job cards…'), function() {
				if (window.autods_show_job_card_plan_for_ro) {
					window.autods_show_job_card_plan_for_ro(frm.doc.name, function() {
						frm.reload_doc();
					});
				} else {
					frappe.msgprint(__('Job card planning script is missing. Rebuild assets or refresh.'));
				}
			}, __('Create'));
			frm.add_custom_button(__('Gate Pass Entry'), function() {
				frm.call({
					doc: frm.doc,
					method: 'create_gate_pass',
					args: { gate_pass_type: 'Entry' },
					freeze: true,
					freeze_message: __('Creating Gate Pass...'),
					callback: function(r) {
						if (r.message && r.message.name) {
							frappe.set_route('Form', 'Gate Pass', r.message.name);
						}
					}
				});
			}, __('Create'));
			if (frm.doc.docstatus === 1) {
				frm.add_custom_button(__('Sales Invoice'), function() {
					autods_open_repair_order_sales_invoice(frm);
				}, __('Create'));
			}
		}
		frm.add_custom_button(__('Load Service Template'), function() {
			load_service_template(frm);
		}, __('Actions'));
		if (frm.doc.repair_estimate) {
			frm.add_custom_button(__('Open Repair Estimate'), function() {
				frappe.set_route('Form', 'Repair Estimate', frm.doc.repair_estimate);
			}, __('View'));
		}
	}
});

frappe.ui.form.on('Repair Order Charges', {
	charges_add: function() {},
	form_render: function(frm, cdt, cdn) {
		autods_apply_locked_charge_row_editability(frm);
	},
	charges_remove: function(frm, cdt, cdn) {
		var row = locals[cdt] && locals[cdt][cdn];
		if (!autods_is_charge_row_locked(frm, row)) {
			return;
		}
		var jc = autods_get_locked_charges_map(frm)[row.name];
		frappe.throw(
			__('Cannot remove charge line locked by Job Card {0}.', [frappe.bold(jc)])
		);
	},
	service_item_type: function(frm, cdt, cdn) {
		if (autods_guard_locked_charge_edit(frm, cdt, cdn, 'service_item_type')) {
			return;
		}
		var row = locals[cdt][cdn];
		autods_clear_charge_item_row(row);
		frappe.after_ajax(function() {
			frm.refresh_field('charges');
		});
	},
	item: function(frm, cdt, cdn) {
		if (autods_guard_locked_charge_edit(frm, cdt, cdn, 'item')) {
			return;
		}
	},
	description: function(frm, cdt, cdn) {
		autods_guard_locked_charge_edit(frm, cdt, cdn, 'description');
	},
	service_row: function(frm, cdt, cdn) {
		autods_guard_locked_charge_edit(frm, cdt, cdn, 'service_row');
	},
	standard_hours: function(frm, cdt, cdn) {
		/* Standard Hours is labor/planning only; does not affect Amount (Qty x Rate). */
		autods_guard_locked_charge_edit(frm, cdt, cdn, 'standard_hours');
	},
	uom: function(frm, cdt, cdn) {
		autods_guard_locked_charge_edit(frm, cdt, cdn, 'uom');
	},
	rate: function(frm, cdt, cdn) {
		if (autods_guard_locked_charge_edit(frm, cdt, cdn, 'rate')) {
			return;
		}
		var row = locals[cdt][cdn];
		var t = (row.service_item_type || '').trim();
		if (t === 'Service' || t === 'Spareparts' || t === 'Overhead') {
			row.amount = (parseFloat(row.qty) || 0) * (parseFloat(row.rate) || 0);
		}
		autods_refresh_charge_row_amount(frm, cdt, cdn);
	},
	qty: function(frm, cdt, cdn) {
		if (autods_guard_locked_charge_edit(frm, cdt, cdn, 'qty')) {
			return;
		}
		var row = locals[cdt][cdn];
		var t = (row.service_item_type || '').trim();
		if (t === 'Service' || t === 'Spareparts' || t === 'Overhead') {
			row.amount = (parseFloat(row.qty) || 0) * (parseFloat(row.rate) || 0);
			autods_refresh_charge_row_amount(frm, cdt, cdn);
		}
	},
	bill_type: function(frm, cdt, cdn) {
		if (autods_guard_locked_charge_edit(frm, cdt, cdn, 'bill_type')) {
			return;
		}
		frm.dirty();
	},
	bill_to: function(frm, cdt, cdn) {
		autods_guard_locked_charge_edit(frm, cdt, cdn, 'bill_to');
	},
	item_type: function(frm, cdt, cdn) {
		autods_guard_locked_charge_edit(frm, cdt, cdn, 'item_type');
	},
	warehouse: function(frm, cdt, cdn) {
		autods_guard_locked_charge_edit(frm, cdt, cdn, 'warehouse');
	},
	color_code: function(frm, cdt, cdn) {
		autods_guard_locked_charge_edit(frm, cdt, cdn, 'color_code');
	},
	paint_type: function(frm, cdt, cdn) {
		autods_guard_locked_charge_edit(frm, cdt, cdn, 'paint_type');
	},
});

function autods_default_billing_item_type(cdt, cdn) {
	var row = locals[cdt][cdn];
	if (!row || !row.item) {
		frappe.model.set_value(cdt, cdn, 'item_type', '');
		return;
	}
	frappe.db.get_value('Item', row.item, 'custom_service_item_type', function(r) {
		if (locals[cdt] && locals[cdt][cdn] && locals[cdt][cdn].item === row.item) {
			frappe.model.set_value(cdt, cdn, 'item_type', (r && r.custom_service_item_type) || '');
		}
	});
}

frappe.ui.form.on('RO Customer Bill', {
	item: function(frm, cdt, cdn) {
		autods_default_billing_item_type(cdt, cdn);
	},
	rate: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		row.amount = (parseFloat(row.qty) || 0) * (parseFloat(row.rate) || 0);
		frm.refresh_field('table_wlxj');
	},
	qty: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		row.amount = (parseFloat(row.qty) || 0) * (parseFloat(row.rate) || 0);
		frm.refresh_field('table_wlxj');
	},
});

frappe.ui.form.on('RO Insurance Bill', {
	item: function(frm, cdt, cdn) {
		autods_default_billing_item_type(cdt, cdn);
	},
	rate: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		row.amount = (parseFloat(row.qty) || 0) * (parseFloat(row.rate) || 0);
		frm.refresh_field('insurance_bills');
	},
	qty: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		row.amount = (parseFloat(row.qty) || 0) * (parseFloat(row.rate) || 0);
		frm.refresh_field('insurance_bills');
	},
});

frappe.ui.form.on('Repair Order Service Inspection', {
	inspection_name: function(frm, cdt, cdn) {
		autods_fetch_service_inspection_for_row(frm, cdt, cdn);
	},
	quality_inspections_add: function(frm, cdt, cdn) {
		autods_fetch_service_inspection_for_row(frm, cdt, cdn);
	},
});

function autods_fetch_service_inspection_for_row(frm, cdt, cdn) {
	var row = locals[cdt][cdn];
	var inspection_name = (row.inspection_name || '').trim();
	if (!frm.doc.name || !inspection_name) {
		return;
	}
	if (inspection_name !== row.inspection_name) {
		frappe.model.set_value(cdt, cdn, 'inspection_name', inspection_name);
	}
	frappe.call({
		method: 'autods.service.doctype.repair_order.repair_order.get_service_inspection_by_name',
		args: {
			repair_order: frm.doc.name,
			inspection_name: inspection_name
		},
		callback: function(r) {
			if (!r.message) {
				return;
			}
			var si = r.message;
			frappe.model.set_value(cdt, cdn, 'quality_inspection', si.name);
			if (si.status) {
				frappe.model.set_value(cdt, cdn, 'status', si.status);
			}
			if (si.inspection_date) {
				frappe.model.set_value(cdt, cdn, 'inspection_date', si.inspection_date);
			}
			if (si.inspected_by) {
				frappe.model.set_value(cdt, cdn, 'inspected_by', si.inspected_by);
			}
			if (si.remarks) {
				frappe.model.set_value(cdt, cdn, 'remarks', si.remarks);
			}
		}
	});
}

function load_service_template(frm) {
	var initial_filters = [];
	if (frm.doc.vehicle_make) {
		initial_filters.push(['Service Template', 'vehicle_make', '=', frm.doc.vehicle_make]);
	}
	if (frm.doc.vehicle_model) {
		initial_filters.push(['Service Template', 'vehicle_model', '=', frm.doc.vehicle_model]);
	}

	var d = new frappe.ui.Dialog({
		title: __('Load Service Template'),
		fields: [
			{
				fieldtype: 'Section Break',
				label: __('Filter Templates'),
				description: __('Use default filters (Make, Model) or add more via "Add a Filter". Then click Search.')
			},
			{
				fieldtype: 'HTML',
				fieldname: 'filter_area',
				options: '<div id="service-template-filter-area-ro" class="filter-area-wrapper" style="min-height: 80px;"></div>'
			},
			{ fieldtype: 'Section Break' },
			{
				fieldtype: 'Button',
				fieldname: 'btn_search',
				label: __('Search Templates'),
				click: function() {
					if (d.filter_group) search_templates(d);
				}
			},
			{
				fieldtype: 'Section Break',
				label: __('Select Template')
			},
			{
				fieldtype: 'HTML',
				fieldname: 'template_list',
				options: '<div id="template-list-container-ro" style="min-height: 220px; max-height: 400px; overflow-y: auto; border: 1px solid var(--border-color); padding: 12px; border-radius: 6px; background: var(--fg-color);">' +
					'<div class="text-muted text-center" style="padding: 48px 24px;">' +
					__('Add filters above and click "Search Templates" to list templates') +
					'</div></div>'
			}
		],
		primary_action_label: __('Load Selected Template'),
		primary_action: function() {
			var selected_template = d.selected_template;
			if (!selected_template) {
				frappe.msgprint(__('Please select a Service Template from the list'));
				return;
			}
			if (frm.doc.charges && frm.doc.charges.length > 0) {
				frappe.confirm(
					__('This will replace all existing charge lines. Continue?'),
					function() {
						fetch_template_items_ro(frm, selected_template);
						d.hide();
					}
				);
			} else {
				fetch_template_items_ro(frm, selected_template);
				d.hide();
			}
		}
	});

	function search_templates(dialog) {
		if (!dialog.filter_group) return;
		var filters = dialog.filter_group.get_filters();
		var container = dialog.fields_dict.template_list.$wrapper.find('#template-list-container-ro');

		container.html('<div class="text-center text-muted" style="padding: 48px 24px;">' +
			'<div class="spinner-border spinner-border-sm" role="status"></div><br>' +
			__('Searching...') + '</div>');

		var filter_dict = {};
		filters.forEach(function(filter) {
			if (Array.isArray(filter) && filter.length >= 4) {
				var field = filter[1];
				var condition = filter[2];
				var value = filter[3];
				if (!field || value == null || value === '') return;
				if (condition === '=' || condition === 'like') {
					filter_dict[field] = value;
					if (condition === 'like') filter_dict[field + '_like'] = true;
				}
			}
		});

		frappe.call({
			method: 'autods.service.doctype.repair_order.repair_order.get_service_templates_filtered',
			args: {
				vehicle_make: filter_dict.vehicle_make || null,
				vehicle_model: filter_dict.vehicle_model || null,
				vehicle_variant: filter_dict.vehicle_variant || null,
				vehicle_year_model: filter_dict.vehicle_year_model != null ? filter_dict.vehicle_year_model : null,
				vehicle_transmission_type: filter_dict.vehicle_transmission_type || null,
				vehicle_fuel_type: filter_dict.vehicle_fuel_type || null,
				vehicle_body_type: filter_dict.vehicle_body_type || null,
				vehicle_drive_type: filter_dict.vehicle_drive_type || null,
				template_name: filter_dict.template_name || null,
				template_name_like: filter_dict.template_name_like || null
			},
			callback: function(r) {
				if (r.message && r.message.length > 0) {
					render_template_list(container, r.message, dialog);
				} else {
					container.html('<div class="text-center text-muted" style="padding: 48px 24px;">' +
						__('No templates found. Try changing filters or add more.') + '</div>');
				}
			},
			error: function() {
				container.html('<div class="text-center text-danger" style="padding: 48px 24px;">' +
					__('Error searching templates') + '</div>');
			}
		});
	}

	function render_template_list(container, templates, dialog) {
		dialog.selected_template = null;
		if (!templates.length) {
			container.html('<div class="text-center text-muted" style="padding: 48px 24px;">' +
				__('No templates found') + '</div>');
			return;
		}
		var html = '<div class="list-group">';
		templates.forEach(function(template) {
			var details = [];
			if (template.vehicle_make) details.push(__('Make: {0}', [template.vehicle_make]));
			if (template.vehicle_model) details.push(__('Model: {0}', [template.vehicle_model]));
			if (template.vehicle_variant) details.push(__('Variant: {0}', [template.vehicle_variant]));
			if (template.vehicle_year_model) details.push(__('Year: {0}', [template.vehicle_year_model]));
			var details_str = details.length ? details.join(' • ') : __('Universal Template');
			html += '<div class="template-item list-group-item list-group-item-action" data-template="' + frappe.utils.escape_html(template.name) + '" style="cursor: pointer;">' +
				'<div class="d-flex justify-content-between align-items-center"><strong>' + frappe.utils.escape_html(template.template_name || template.name) + '</strong></div>' +
				'<small class="text-muted">' + frappe.utils.escape_html(template.name) + '</small>' +
				'<div class="text-muted small mt-1">' + details_str + '</div></div>';
		});
		html += '</div>';
		container.html(html);
		container.find('.template-item').on('click', function() {
			container.find('.template-item').removeClass('active');
			$(this).addClass('active');
			dialog.selected_template = $(this).attr('data-template');
		});
	}

	d.show();

	setTimeout(function() {
		try {
			var filter_area = d.fields_dict.filter_area.$wrapper.find('#service-template-filter-area-ro');
			d.filter_group = new frappe.ui.FilterGroup({
				parent: filter_area,
				doctype: 'Service Template',
				on_change: function() {
					if (d.filter_group) search_templates(d);
				}
			});
			if (d.filter_group.wrapper && d.filter_group.wrapper.find('.apply-filters').length) {
				d.filter_group.wrapper.find('.apply-filters').hide();
			}
			frappe.model.with_doctype('Service Template', function() {
				if (initial_filters.length > 0) {
					d.filter_group.add_filters_to_filter_group(initial_filters);
				}
				setTimeout(function() { search_templates(d); }, 300);
			});
		} catch (e) {
			console.error('Load Service Template filter init:', e);
			frappe.msgprint({ message: __('Error initializing filters. Refresh and try again.'), indicator: 'red' });
		}
	}, 150);
}

function fetch_template_items_ro(frm, template_name) {
	var service_template = template_name || (frm.doc.service_template || null);
	if (!service_template) {
		frappe.msgprint(__('Please select a Service Template'));
		return;
	}
	frm.call({
		method: 'fetch_template_items',
		args: {
			doctype: frm.doctype,
			name: frm.docname,
			service_template: service_template,
			doc: frm.doc
		},
		callback: function(r) {
			if (r.message && r.message.doc) {
				frm._autods_bulk_loading_charges = true;
				// Always replace charges from template response (aligned with Repair Estimate).
				frm.clear_table('charges');
				(r.message.doc.charges || []).forEach(function(item) {
					var row = frm.add_child('charges');
					Object.keys(item).forEach(function(key) {
						// Skip server temp child names and resolved parents — remap from
						// client row names + service_row after add_child.
						if (key !== 'name' && key !== 'idx' && key !== 'parent_service_charge') {
							row[key] = item[key];
						}
					});
				});
				if (r.message.doc.quality_inspections && r.message.doc.quality_inspections.length > 0) {
					var existing_names = (frm.doc.quality_inspections || []).map(function(qi) { return qi.inspection_name; });
					r.message.doc.quality_inspections.forEach(function(item) {
						if (item.inspection_name && existing_names.indexOf(item.inspection_name) === -1) {
							var row = frm.add_child('quality_inspections');
							Object.keys(item).forEach(function(key) {
								if (key !== 'name' && key !== 'idx') {
									row[key] = item[key];
								}
							});
						}
					});
				}
				frm.refresh_field('charges');
				frm.refresh_field('quality_inspections');
				if (autods.charges_overview && autods.charges_overview.update_service_row_select_options) {
					autods.charges_overview.update_service_row_select_options(frm);
					autods.charges_overview.schedule_render(frm);
				}
				frm._autods_bulk_loading_charges = false;
				if (r.message.doc.service_template) {
					frm.set_value('service_template', r.message.doc.service_template);
				}
				['terms_and_conditions', 'tc_notes'].forEach(function(fieldname) {
					if (frm.fields_dict[fieldname] && r.message.doc[fieldname] !== undefined) {
						frm.set_value(fieldname, r.message.doc[fieldname]);
					}
				});
				if (frm.docname && !frm.is_new()) {
					frm.reload_doc();
				}
			}
			if (r.message) {
				var message = __('Items loaded from template');
				if (r.message.service_items_count || r.message.spareparts_count || r.message.sundry_items_count || r.message.service_inspections_count) {
					var counts = [];
					if (r.message.service_items_count) counts.push(__('{0} service items', [r.message.service_items_count]));
					if (r.message.spareparts_count) counts.push(__('{0} spareparts', [r.message.spareparts_count]));
					if (r.message.sundry_items_count) counts.push(__('{0} sundry items', [r.message.sundry_items_count]));
					if (r.message.service_inspections_count) counts.push(__('{0} service inspections', [r.message.service_inspections_count]));
					message += ': ' + counts.join(', ');
				}
				frappe.show_alert({ message: message, indicator: 'green' });
			}
		},
		error: function() {
			frappe.msgprint(__('Error loading items from template'));
		}
	});
}
