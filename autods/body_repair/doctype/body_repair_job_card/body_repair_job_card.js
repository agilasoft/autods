// Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Body Repair Job Card', {
	refresh: function(frm) {
		// Add button to create spareparts request
		if (frm.doc.status !== 'Completed' && frm.doc.status !== 'Cancelled') {
			frm.add_custom_button(__('Create Spareparts Request'), function() {
				frm.call({
					method: 'create_spareparts_request',
					callback: function(r) {
						if (r.message) {
							frappe.set_route('Form', 'Body Repair Spareparts Request', r.message.name);
						}
					}
				});
			}, __("Actions"));
			
			// Add button to create outsourcing
			frm.add_custom_button(__('Create Outsourcing'), function() {
				frm.call({
					method: 'create_outsourcing',
					callback: function(r) {
						if (r.message) {
							frappe.set_route('Form', 'Body Repair Outsourcing', r.message.name);
						}
					}
				});
			}, __("Actions"));
		}
		
		// Add button to assign technician by skills
		if (frm.doc.technician_skills_group && !frm.doc.technician) {
			frm.add_custom_button(__('Find Technicians by Skills'), function() {
				frm.call({
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
		if (frm.doc.technician && frm.doc.service_date && frm.doc.expected_completion_date) {
			frm.add_custom_button(__('Check Technician Availability'), function() {
				frm.call({
					method: 'check_technician_availability',
					args: {
						technician: frm.doc.technician,
						start_date: frm.doc.service_date,
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
