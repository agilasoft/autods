// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Card', {
	refresh: function(frm) {
		// Create Material Request (Material Issue) – references: Job Card, Repair Order
		if (frm.doc.status !== 'Completed' && frm.doc.status !== 'Cancelled') {
			frm.add_custom_button(__('Create Material Request'), function() {
				frm.call({
					doc: frm.doc,
					method: 'create_material_request',
					callback: function(r) {
						if (r.message && r.message.name) {
							frappe.set_route('Form', 'Material Request', r.message.name);
						}
					}
				});
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
							let d = new frappe.ui.Dialog({
								title: __('Available Technicians'),
								fields: [
									{
										fieldtype: 'HTML',
										options: '<div id="technician-list"></div>'
									}
								],
								primary_action_label: __('Close'),
								primary_action: function() {
									d.hide();
								}
							});

							let html = '<table class="table table-bordered"><thead><tr><th>Technician</th><th>Action</th></tr></thead><tbody>';
							r.message.forEach(function(tech) {
								html += `<tr>
									<td>${tech.employee_name || tech.name}</td>
									<td><button class="btn btn-sm btn-primary" onclick="assignTechnician('${tech.name}')">Assign</button></td>
								</tr>`;
							});
							html += '</tbody></table>';

							d.fields_dict['technician-list'].$wrapper.html(html);

							window.assignTechnician = function(technician) {
								frm.set_value('technician', technician);
								d.hide();
							};

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
	}
});
