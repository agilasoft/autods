// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

function update_work_details_total_hours(frm) {
	let total = 0;
	(frm.doc.work_details || []).forEach(function(row) {
		total += flt(row.hours_spent);
	});
	frm.set_value('work_details_total_hours', total);
}

function open_job_card_material_request_dialog(frm) {
	frm.call({
		doc: frm.doc,
		method: 'get_material_request_candidates',
		callback: function(r) {
			const data = r.message || {};
			if (data.mode === 'none') {
				frappe.msgprint({
					title: __('Material Request'),
					message: data.message || __('Nothing to issue.'),
					indicator: 'orange'
				});
				return;
			}

			function run_create(charge_row_names) {
				frm.call({
					doc: frm.doc,
					method: 'create_material_request',
					args: { charge_row_names: charge_row_names && charge_row_names.length ? charge_row_names : null },
					freeze: true,
					freeze_message: __('Creating Material Request...'),
					callback: function(cr) {
						if (cr.message && cr.message.name) {
							frappe.set_route('Form', 'Material Request', cr.message.name);
						}
					}
				});
			}

			const lines = data.lines || [];
			const fallback = data.fallback_lines || [];

			if (data.mode === 'scoped' && lines.length) {
				frappe.confirm(
					__(
						'Create Material Request for {0} sparepart line(s) linked to this job\'s service line?',
						[lines.length]
					),
					function() {
						run_create(lines.map(function(l) {
							return l.name;
						}));
					}
				);
				return;
			}

			const pick_lines = (data.mode === 'scoped_empty' || data.mode === 'invalid_service_line')
				? fallback
				: lines;
			if (data.message) {
				frappe.msgprint({ message: data.message, indicator: 'orange' });
			}
			if (!(pick_lines && pick_lines.length)) {
				if (!data.message) {
					frappe.msgprint(__('No sparepart lines on this Repair Order.'));
				}
				return;
			}
			show_pick_spareparts_dialog(frm, pick_lines, run_create);
		}
	});
}

function show_pick_spareparts_dialog(frm, lines, run_create) {
	const esc = frappe.utils.escape_html;
	let body = '<p class="text-muted small">' +
		__('Select sparepart charge lines to include on the Material Request.') + '</p>';
	body += '<div class="job-card-mr-pick" style="max-height:260px;overflow:auto">';
	body += '<table class="table table-bordered"><thead><tr><th></th><th>Item</th><th>Qty</th><th>Service</th></tr></thead><tbody>';
	lines.forEach(function(line) {
		const id = 'jc-mr-' + frappe.utils.get_random(8);
		body += '<tr><td><input type="checkbox" class="job-card-mr-line-cb" data-row-name="' +
			esc(line.name) + '" id="' + id + '" checked></td>';
		body += '<td><label for="' + id + '" style="margin:0;font-weight:normal">' +
			esc(line.item_code || '') + ' — ' + esc(line.item_name || '') + '</label></td>';
		body += '<td>' + esc(String(flt(line.qty))) + '</td>';
		body += '<td>' + esc(line.service_row || '') + '</td></tr>';
	});
	body += '</tbody></table></div>';

	const d = new frappe.ui.Dialog({
		title: __('Select spareparts'),
		fields: [{ fieldtype: 'HTML', fieldname: 'pick_html', options: body }],
		primary_action_label: __('Create Material Request'),
		primary_action: function() {
			const names = [];
			d.$wrapper.find('.job-card-mr-line-cb:checked').each(function() {
				names.push($(this).attr('data-row-name'));
			});
			if (!names.length) {
				frappe.msgprint(__('Select at least one line.'));
				return;
			}
			d.hide();
			run_create(names);
		}
	});
	d.show();
}

frappe.ui.form.on('Job Card', {
	onload: function(frm) {
		autods.service_datetime.patch_system_datetime_control(frm, 'expected_completion_date');
	},

	refresh: function(frm) {
		update_work_details_total_hours(frm);
		// Create Material Request (Material Issue) – references: Job Card, Repair Order
		if (frm.doc.status !== 'Completed' && frm.doc.status !== 'Cancelled') {
			frm.add_custom_button(__('Create Material Request'), function() {
				open_job_card_material_request_dialog(frm);
			}, __("Actions"));
		}

		// Add button to assign technician by skills
		if (frm.doc.technician_skills_group && !frm.doc.technician) {
			frm.add_custom_button(__('Find Technicians by Skills'), function() {
				frm.call({
					doc: frm.doc,
					method: 'assign_technician_by_skills',
					callback: function(r) {
						if (r.message && r.message.length > 0) {
							const d = new frappe.ui.Dialog({
								title: __('Ranked technicians'),
								fields: [
									{
										fieldtype: 'HTML',
										fieldname: 'tech_table',
										options: '<div></div>'
									}
								],
								primary_action_label: __('Close'),
								primary_action: function() {
									d.hide();
								}
							});

							const $wrap = d.fields_dict.tech_table.$wrapper;
							const $table = $('<table class="table table-bordered"><thead><tr>' +
								'<th>' + __('Technician') + '</th>' +
								'<th class="text-right">' + __('Skills match') + '</th>' +
								'<th class="text-right">' + __('Open jobs (day)') + '</th>' +
								'<th class="text-right">' + __('Bay jobs') + '</th>' +
								'<th class="text-right">' + __('Score') + '</th>' +
								'<th></th></tr></thead></table>');
							const $tbody = $('<tbody>');
							r.message.forEach(function(tech) {
								const $tr = $('<tr>');
								$tr.append($('<td>').text(tech.employee_name || tech.employee));
								$tr.append($('<td class="text-right">').text(
									tech.skills_match_pct != null ? tech.skills_match_pct + '%' : ''
								));
								$tr.append($('<td class="text-right">').text(tech.open_jobs_today != null ? tech.open_jobs_today : ''));
								$tr.append($('<td class="text-right">').text(
									tech.bay_jobs_same_area != null ? tech.bay_jobs_same_area : ''
								));
								$tr.append($('<td class="text-right">').text(tech.score != null ? tech.score : ''));
								const $btn = $('<button class="btn btn-sm btn-primary">').text(__('Assign'));
								$btn.on('click', function() {
									frm.set_value('technician', tech.employee);
									d.hide();
								});
								$tr.append($('<td>').append($btn));
								$tbody.append($tr);
							});
							$table.append($tbody);
							$wrap.empty().append($table);

							d.show();
						}
					}
				});
			}, __("Actions"));
		}

		// Add button to check technician availability
		if (frm.doc.technician && frm.doc.repair_date && frm.doc.expected_completion_date) {
			frm.add_custom_button(__('Check Technician Availability'), function() {
				frm.call({
					method: 'check_technician_availability',
					args: {
						technician: frm.doc.technician,
						start_date: frm.doc.repair_date,
						end_date: frm.doc.expected_completion_date
					},
					callback: function(r) {
						if (r.message.available) {
							frappe.show_alert({
								message: __('Technician is available'),
								indicator: 'green'
							});
						} else {
							frappe.msgprint({
								title: __('Technician Not Available'),
								message: __('Technician has overlapping jobs. Please select a different time slot or technician.'),
								indicator: 'orange'
							});
						}
					}
				});
			}, __("Actions"));
		}

		// Add button to create shopfloor schedule
		if (frm.doc.work_area && frm.doc.status !== 'Completed' && frm.doc.status !== 'Cancelled') {
			frm.add_custom_button(__('Create ShopFloor Schedule'), function() {
				frm.call({
					doc: frm.doc,
					method: 'create_shopfloor_schedule',
					callback: function(r) {
						if (r.message) {
							frappe.set_route('Form', 'ShopFloor Schedule', r.message.name);
						}
					}
				});
			}, __("Actions"));
		}

		// Add installation cost to vehicle serial (per §3.3.1: after Job Card completion)
		if (frm.doc.vehicle_unit && frm.doc.status === 'Completed') {
			frm.add_custom_button(__('Add installation cost to vehicle'), function() {
				const d = new frappe.ui.Dialog({
					title: __('Add installation cost to vehicle serial'),
					fields: [
						{ fieldname: 'amount_to_add', fieldtype: 'Currency', label: __('Amount to add'), reqd: 1 },
						{ fieldname: 'reason', fieldtype: 'Small Text', label: __('Reason (optional)') }
					],
					primary_action_label: __('Add cost'),
					primary_action: function(values) {
						frappe.call({
							method: 'autods.vehicle_sales.add_cost_to_vehicle_serial.add_cost_to_vehicle_serial',
							args: {
								vehicle_unit: frm.doc.vehicle_unit,
								amount_to_add: values.amount_to_add,
								reason: values.reason || undefined
							},
							callback: function(r) {
								if (r.message && r.message.message) {
									frappe.show_alert({ message: r.message.message, indicator: 'green' });
								}
								if (r.message && r.message.stock_reconciliation) {
									frappe.set_route('Form', 'Stock Reconciliation', r.message.stock_reconciliation);
								}
							}
						});
						d.hide();
					}
				});
				d.show();
			}, __("Actions"));
		}
	},

	technician_skills_group: function(frm) {
		// Clear technician when skills group changes
		if (frm.doc.technician_skills_group) {
			frm.set_value('technician', '');
		}
	},

	start_time: function(frm) {
		if (frm.doc.start_time && frm.doc.end_time) {
			frm.call('calculate_total_hours');
		}
	},

	end_time: function(frm) {
		if (frm.doc.start_time && frm.doc.end_time) {
			frm.call('calculate_total_hours');
		}
	},

	work_details_add: function(frm) {
		update_work_details_total_hours(frm);
	},

	work_details_remove: function(frm) {
		update_work_details_total_hours(frm);
	}
});

frappe.ui.form.on('Job Card Work Detail', {
	hours_spent: function(frm) {
		update_work_details_total_hours(frm);
	}
});
