// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

/* global frappe */

(function () {
	'use strict';

	function autods_job_plan_esc(s) {
		if (frappe.utils && frappe.utils.escape_html) {
			return frappe.utils.escape_html(s == null ? '' : String(s));
		}
		return String(s == null ? '' : s);
	}

	function autods_render_job_card_plan_dialog(plan, repair_order_name, on_done) {
		var lines = plan.lines || [];
		if (!lines.length) {
			frappe.msgprint(__('Add at least one Service charge line on the Repair Order to create job cards.'));
			return;
		}
		var sets = plan.settings || {};
		var maxDays = sets.planning_max_extra_days != null ? sets.planning_max_extra_days : 0;
		var settingsHtml = '<p class="text-muted small">' +
			__('Auto work area: {0} · Auto technician: {1} · Respect bay capacity: {2} · Respect technician load: {3} · Allow overlapping schedules: {4}', [
				sets.auto_assign_work_area ? __('Yes') : __('No'),
				sets.auto_assign_technician ? __('Yes') : __('No'),
				sets.respect_work_area_capacity ? __('Yes') : __('No'),
				sets.respect_technician_load ? __('Yes') : __('No'),
				sets.allow_overlapping_schedules ? __('Yes') : __('No')
			]) + '</p>' +
			'<p class="text-muted small">' +
			__('Max extra days: {0} · Work area full: {1} · Past shop close: {2} · Technician overlap: {3}', [
				String(maxDays),
				autods_job_plan_esc(sets.planning_work_area_full || 'warn_only'),
				autods_job_plan_esc(sets.planning_past_shop_close || 'warn_only'),
				autods_job_plan_esc(sets.planning_technician_overlap || 'warn_only')
			]) + '</p>';

		var rows = lines.map(function (line) {
			var w = (line.warnings || []).map(function (x) { return autods_job_plan_esc(x); }).join('; ');
			var exists = line.existing_job_card
				? '<span class="indicator-pill yellow">' + autods_job_plan_esc(line.existing_job_card) + '</span>'
				: '<span class="text-muted">—</span>';
			return '<tr>' +
				'<td>' + line.seq + '</td>' +
				'<td>' + autods_job_plan_esc(line.assignment_date || '') + '</td>' +
				'<td>' + autods_job_plan_esc(line.item) + '</td>' +
				'<td>' + autods_job_plan_esc(line.description) + '</td>' +
				'<td class="text-end">' + autods_job_plan_esc(String(line.standard_hours != null ? line.standard_hours : line.hours)) + '</td>' +
				'<td>' + autods_job_plan_esc(line.work_area || '') + '</td>' +
				'<td>' + autods_job_plan_esc(line.technician_skills_group || '') + '</td>' +
				'<td>' + autods_job_plan_esc(line.technician || '') + '</td>' +
				'<td class="small">' + autods_job_plan_esc(line.planned_start) + ' → ' + autods_job_plan_esc(line.planned_end) + '</td>' +
				'<td class="small text-danger">' + (w || '—') + '</td>' +
				'<td>' + exists + '</td>' +
				'</tr>';
		}).join('');

		var table = '<div style="max-height:420px;overflow:auto;"><table class="table table-bordered table-sm">' +
			'<thead><tr>' +
			'<th>#</th><th>' + __('Date') + '</th><th>' + __('Item') + '</th><th>' + __('Description') + '</th><th>' + __('Standard Hours') + '</th>' +
			'<th>' + __('Work area') + '</th><th>' + __('Skills group') + '</th><th>' + __('Technician') + '</th>' +
			'<th>' + __('Planned window') + '</th><th>' + __('Warnings') + '</th><th>' + __('Existing') + '</th>' +
			'</tr></thead><tbody>' + rows + '</tbody></table></div>';

		var d = new frappe.ui.Dialog({
			title: __('Job card plan') + ' — ' + autods_job_plan_esc(repair_order_name),
			size: 'large',
			fields: [
				{ fieldtype: 'HTML', fieldname: 'info', options: settingsHtml },
				{ fieldtype: 'HTML', fieldname: 'tbl', options: table }
			],
			primary_action_label: __('Create job cards'),
			primary_action: function () {
				frappe.call({
					method: 'autods.service.doctype.repair_order.repair_order.create_job_cards_from_plan_by_repair_order',
					args: { repair_order: repair_order_name },
					freeze: true,
					freeze_message: __('Creating job cards...'),
					callback: function (res) {
						d.hide();
						var msg = res.message || {};
						var created = msg.created || [];
						var skipped = msg.skipped || [];
						var parts = [];
						if (created.length) parts.push(__('{0} created', [created.length]));
						if (skipped.length) parts.push(__('{0} skipped (already linked)', [skipped.length]));
						frappe.show_alert({ message: parts.join(' · ') || __('Done'), indicator: 'green' });
						if (typeof on_done === 'function') {
							on_done();
						}
						if (created.length === 1) {
							frappe.set_route('Form', 'Job Card', created[0]);
						}
					}
				});
			}
		});
		d.show();
	}

	/**
	 * Open job card planning dialog for a Repair Order (used from Repair Order, Service Appointment, Repair Estimate).
	 * @param {string} repair_order_name
	 * @param {function} [on_done] — called after successful create (e.g. frm.reload_doc)
	 */
	window.autods_show_job_card_plan_for_ro = function (repair_order_name, on_done) {
		if (!repair_order_name) {
			frappe.msgprint(__('No Repair Order is linked.'));
			return;
		}
		frappe.call({
			method: 'autods.service.doctype.repair_order.repair_order.get_job_card_plan_by_repair_order',
			args: { repair_order: repair_order_name },
			freeze: true,
			freeze_message: __('Building job card plan...'),
			callback: function (r) {
				autods_render_job_card_plan_dialog(r.message || {}, repair_order_name, on_done);
			}
		});
	};
})();
