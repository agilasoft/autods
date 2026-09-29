// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

/* global frappe */

(function () {
	'use strict';

	var autods_jc_svc_pick_styles_injected = false;
	var autods_jc_plan_styles_injected = false;

	function autods_job_plan_esc(s) {
		if (frappe.utils && frappe.utils.escape_html) {
			return frappe.utils.escape_html(s == null ? '' : String(s));
		}
		return String(s == null ? '' : s);
	}

	function autods_jc_attr_url(u) {
		if (!u) return '';
		return String(u).replace(/"/g, '%22').replace(/</g, '%3C').replace(/`/g, '%60');
	}

	function autods_jc_file_to_img_src(file_url) {
		if (!file_url) return '';
		var u = String(file_url).trim();
		if (frappe.utils.is_url(u)) {
			return encodeURI(u).replace(/#/g, '%23');
		}
		u = frappe.utils.get_file_link(u);
		if (!frappe.utils.is_url(u)) {
			if (u.indexOf('/') !== 0) {
				u = '/' + u;
			}
			if (frappe.urllib && frappe.urllib.get_full_url) {
				u = frappe.urllib.get_full_url(u);
			}
		}
		return encodeURI(u).replace(/#/g, '%23');
	}

	function autods_jc_inject_svc_pick_styles() {
		if (autods_jc_svc_pick_styles_injected) return;
		autods_jc_svc_pick_styles_injected = true;
		var css = [
			'.autods-jc-svc-pick { display: flex; flex-direction: column; gap: 0.75rem; }',
			'.autods-jc-svc-pick__header { margin-bottom: 0.25rem; }',
			'.autods-jc-svc-pick__ro-id { font-size: 0.78rem; color: var(--text-muted, #6c757d); margin: 0 0 0.15rem; }',
			'.autods-jc-svc-pick__vehicle-title { font-size: 1.05rem; font-weight: 600; margin: 0; color: var(--text-color, #212529); }',
			'.autods-jc-svc-pick__meta { font-size: 0.82rem; color: var(--text-muted, #6c757d); margin: 0.2rem 0 0; }',
			'.autods-jc-svc-pick__cards { display: flex; flex-direction: column; gap: 0.65rem; max-height: 360px; overflow-y: auto; }',
			'.autods-jc-svc-pick__card { display: flex; align-items: center; gap: 1rem; border: 1px solid var(--border-color, #dee2e6); border-radius: 12px; padding: 0.75rem 1rem; background: var(--card-bg, #fff); box-shadow: 0 1px 2px rgba(0,0,0,0.04); }',
			'.autods-jc-svc-pick__card--disabled { opacity: 0.65; }',
			'.autods-jc-svc-pick__thumb { flex-shrink: 0; width: 72px; height: 72px; border-radius: 10px; overflow: hidden; background: var(--control-bg, #f8f9fa); border: 1px solid var(--border-color, #e9ecef); display: flex; align-items: center; justify-content: center; }',
			'.autods-jc-svc-pick__thumb img { width: 100%; height: 100%; object-fit: cover; }',
			'.autods-jc-svc-pick__thumb--empty { font-size: 0.62rem; color: var(--text-muted, #868e96); text-align: center; padding: 0.35rem; line-height: 1.25; }',
			'.autods-jc-svc-pick__body { flex: 1; min-width: 0; }',
			'.autods-jc-svc-pick__title { font-weight: 600; font-size: 0.92rem; margin: 0; color: var(--text-color, #212529); }',
			'.autods-jc-svc-pick__subtitle { font-size: 0.8rem; color: var(--text-muted, #6c757d); margin: 0.2rem 0 0; }',
			'.autods-jc-svc-pick__action { flex-shrink: 0; }',
			'.autods-jc-svc-pick__continue.btn { border-radius: 8px; min-width: 5.5rem; }'
		].join('\n');
		$('<style type="text/css" data-autods-jc-svc-pick="1">' + css + '</style>').appendTo('head');
	}

	function autods_jc_render_vehicle_photo(vehicle_image) {
		var imgUrl = vehicle_image ? autods_jc_file_to_img_src(vehicle_image) : '';
		if (imgUrl) {
			return '<div class="autods-jc-plan__photo"><img src="' +
				autods_jc_attr_url(imgUrl) + '" alt="" /></div>';
		}
		return '<div class="autods-jc-plan__photo autods-jc-plan__photo--empty"><span>' +
			autods_job_plan_esc(__('No vehicle photo')) + '</span></div>';
	}

	function autods_jc_render_kv_row(label, valueHtml) {
		return '<div class="autods-jc-plan__kv">' +
			'<span class="autods-jc-plan__kv-label">' + autods_job_plan_esc(label) + '</span>' +
			'<span class="autods-jc-plan__kv-value">' + valueHtml + '</span>' +
			'</div>';
	}

	function autods_jc_render_summary_column(cellsHtml) {
		if (!cellsHtml) return '';
		return '<div class="autods-jc-plan__summary-col">' + cellsHtml + '</div>';
	}

	function autods_jc_render_summary_row(label, value, faIcon) {
		if (!value && value !== 0) return '';
		var labelHtml = faIcon
			? '<span class="autods-jc-plan__summary-label-row">' +
				'<i class="fa ' + faIcon + ' autods-jc-plan__summary-icon" aria-hidden="true"></i>' +
				'<span class="autods-jc-plan__summary-label">' + autods_job_plan_esc(label) + '</span>' +
				'</span>'
			: '<span class="autods-jc-plan__summary-label">' + autods_job_plan_esc(label) + '</span>';
		return '<div class="autods-jc-plan__summary-cell">' +
			labelHtml +
			'<span class="autods-jc-plan__summary-value">' + autods_job_plan_esc(String(value)) + '</span>' +
			'</div>';
	}

	function autods_jc_inject_plan_styles() {
		if (autods_jc_plan_styles_injected) return;
		autods_jc_plan_styles_injected = true;
		var css = [
			'.autods-jc-plan { display: flex; flex-direction: column; gap: 0.85rem; }',
			'.autods-jc-plan__head { display: flex; align-items: center; gap: 1.25rem; flex-wrap: wrap; }',
			'.autods-jc-plan__hero { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.5rem; padding: 0.25rem 0 0.5rem; flex: 0 0 auto; max-width: 45%; min-width: 0; align-self: center; justify-content: flex-start; }',
			'.autods-jc-plan__hero-head { display: flex; flex-direction: column; align-items: center; gap: 0.15rem; width: 100%; flex-shrink: 0; }',
			'.autods-jc-plan__photo { flex-shrink: 0; width: min(220px, 38vw); min-height: 100px; max-height: 140px; display: flex; align-items: center; justify-content: center; background: transparent; border: none; border-radius: 0; overflow: visible; }',
			'.autods-jc-plan__photo img { max-width: 100%; max-height: 132px; width: auto; height: auto; object-fit: contain; object-position: center bottom; display: block; }',
			'.autods-jc-plan__photo--empty { flex-shrink: 0; width: 160px; min-height: 88px; max-height: 140px; color: var(--text-muted, #6c757d); font-size: 0.75rem; text-align: center; padding: 0.75rem 0.5rem; border: 1px dashed var(--border-color, #dee2e6); border-radius: 10px; background: var(--control-bg, #f8f9fa); display: flex; align-items: center; justify-content: center; }',
			'.autods-jc-plan__vehicle-title { font-size: 1.1rem; font-weight: 600; margin: 0; color: var(--text-color, #212529); line-height: 1.3; width: 100%; }',
			'.autods-jc-plan__meta { font-size: 0.8rem; color: var(--text-muted, #6c757d); margin: 0; width: 100%; }',
			'.autods-jc-plan__summary-card { --autods-jc-summary-line: color-mix(in srgb, var(--border-color, #dee2e6) 55%, var(--text-muted, #6c757d) 45%); --autods-jc-summary-stroke: 3px; --autods-jc-summary-cap: 10px; flex: 1; min-width: 0; width: 100%; align-self: center; padding: 0.75rem 1rem; display: flex; align-items: center; background: transparent; }',
			'.autods-jc-plan__summary-grid { display: flex; align-items: stretch; width: 100%; }',
			'.autods-jc-plan__summary-col { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 1.5rem; min-width: 0; padding: 0.35rem 0.5rem; }',
			'.autods-jc-plan__summary-col:not(:last-child) { position: relative; border-right: var(--autods-jc-summary-stroke) solid var(--autods-jc-summary-line); }',
			'.autods-jc-plan__summary-col:first-child:not(:last-child)::before { content: ""; position: absolute; right: calc(var(--autods-jc-summary-stroke) / -2); top: 0; width: var(--autods-jc-summary-cap); height: var(--autods-jc-summary-cap); transform: translate(50%, -50%); border-radius: 50%; background: var(--autods-jc-summary-line); }',
			'.autods-jc-plan__summary-col:nth-child(2):not(:last-child)::after { content: ""; position: absolute; right: calc(var(--autods-jc-summary-stroke) / -2); bottom: 0; width: var(--autods-jc-summary-cap); height: var(--autods-jc-summary-cap); transform: translate(50%, 50%); border-radius: 50%; background: var(--autods-jc-summary-line); }',
			'.autods-jc-plan__summary-cell { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.35rem; min-width: 0; min-height: 2.75rem; }',
			'.autods-jc-plan__summary-label-row { display: inline-flex; align-items: center; justify-content: center; gap: 0.35rem; max-width: 100%; }',
			'.autods-jc-plan__summary-icon { flex-shrink: 0; color: var(--text-muted, #6c757d); font-size: 0.85rem; line-height: 1; }',
			'.autods-jc-plan__summary-label { font-size: 0.92rem; font-weight: 700; line-height: 1.5; color: var(--text-color, #212529); letter-spacing: 0.02em; text-align: center; }',
			'.autods-jc-plan__summary-value { font-size: 0.78rem; font-weight: 400; line-height: 1.5; color: var(--text-muted, #6c757d); text-align: center; width: 100%; word-break: break-word; }',
			'@media (max-width: 560px) { .autods-jc-plan__head { flex-direction: column; align-items: stretch; } .autods-jc-plan__hero { max-width: none; width: 100%; align-self: stretch; } .autods-jc-plan__summary-card { width: 100%; } .autods-jc-plan__photo { width: 100%; max-width: 260px; min-height: 88px; max-height: 140px; margin: 0 auto; } .autods-jc-plan__photo img { max-height: 132px; height: auto; width: auto; } .autods-jc-plan__photo--empty { width: 160px; min-height: 88px; max-height: 140px; margin: 0 auto; } }',
			'.autods-jc-plan__detail-card { --autods-jc-kv-split: 44%; --autods-jc-highlight-bg: var(--highlight-color); --autods-jc-content-bg: var(--autods-jc-highlight-bg); --autods-jc-tab-pill: var(--autods-jc-highlight-bg); background: transparent; border: none; border-radius: 0; box-shadow: none; overflow: visible; }',
			'.autods-jc-plan__tabs { --autods-jc-tab-track: transparent; --autods-jc-tab-active-text: #A0A0A0; --autods-jc-tab-inactive-text: #A0A0A0; position: relative; display: flex; align-items: flex-end; gap: 0.25rem; padding: 0 0.35rem 0; margin: 0; background: transparent; border-radius: 0; }',
			'.autods-jc-plan__tab-slider { position: absolute; top: 0; bottom: 0; left: 0; border-radius: var(--border-radius-md, 8px) var(--border-radius-md, 8px) 0 0; background: var(--autods-jc-tab-pill); border: 1px solid var(--border-color, #dee2e6); border-bottom: none; box-shadow: var(--shadow-xs, 0 1px 2px rgba(0, 0, 0, 0.06)); transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), width 0.25s cubic-bezier(0.4, 0, 0.2, 1); pointer-events: none; z-index: 0; }',
			'.autods-jc-plan__tab { flex: 1; position: relative; z-index: 1; border: none; background: transparent; padding: 0.55rem 0.35rem 0.65rem; font-size: 0.74rem; font-weight: 600; color: var(--autods-jc-tab-inactive-text); cursor: pointer; border-radius: 0; transition: color 0.2s ease; }',
			'.autods-jc-plan__tab--active { color: var(--autods-jc-tab-active-text); }',
			'.autods-jc-plan__panels { position: relative; background: transparent; overflow: visible; }',
			'.autods-jc-plan__panel { opacity: 0; transform: translateY(6px); pointer-events: none; position: absolute; top: 0; left: 0; right: 0; padding: 0 0.35rem 0.35rem; transition: opacity 0.2s ease, transform 0.2s ease; }',
			'.autods-jc-plan__panel--active { opacity: 1; transform: none; pointer-events: auto; position: relative; }',
			'.autods-jc-plan__content-highlight { background: var(--autods-jc-content-bg); border: 1px solid var(--border-color, #dee2e6); border-top: none; border-radius: 0 0 var(--border-radius-md, 8px) var(--border-radius-md, 8px); padding: 0.85rem 1rem; box-shadow: var(--shadow-xs, 0 1px 2px rgba(0, 0, 0, 0.06)); max-height: 380px; overflow-x: hidden; overflow-y: auto; scrollbar-gutter: stable; -webkit-overflow-scrolling: touch; }',
			'.autods-jc-plan__content-highlight::-webkit-scrollbar { width: 6px; }',
			'.autods-jc-plan__content-highlight::-webkit-scrollbar-track { background: transparent; }',
			'.autods-jc-plan__content-highlight::-webkit-scrollbar-thumb { background: color-mix(in srgb, var(--border-color, #dee2e6) 70%, var(--text-muted, #6c757d) 30%); border-radius: 999px; }',
			'.autods-jc-plan__line-card--multi { padding-bottom: 0.5rem; margin-bottom: 0.5rem; border-bottom: 1px solid var(--border-color, #e9ecef); }',
			'.autods-jc-plan__line-card--multi:last-child { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }',
			'.autods-jc-plan__line-title { font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted, #6c757d); margin: 0 0 0.35rem; }',
			'.autods-jc-plan__kv { display: grid; grid-template-columns: var(--autods-jc-kv-split) minmax(0, 1fr); column-gap: 0.75rem; align-items: start; padding: 0.28rem 0; font-size: 0.74rem; line-height: 1.3; }',
			'.autods-jc-plan__kv-label { text-align: left; max-width: none; padding-right: 0.25rem; color: var(--text-muted, #6c757d); font-size: 0.72rem; }',
			'.autods-jc-plan__kv-value { text-align: left; min-width: 0; color: var(--text-color, #212529); font-size: 0.72rem; word-break: break-word; }',
			'.autods-jc-plan__kv-value.text-danger { color: var(--red-500, #dc3545); }',
			'.autods-jc-plan__settings p { font-size: 0.82rem; color: var(--text-muted, #6c757d); margin: 0 0 0.5rem; line-height: 1.45; }',
			'.autods-jc-plan__settings p:last-child { margin-bottom: 0; }',
			'.autods-jc-plan__intro { font-size: 0.82rem; color: var(--text-color, #212529); margin: 0 0 0.35rem; }',
			'[data-theme-mode="light"] .autods-jc-plan__detail-card { --autods-jc-highlight-bg: var(--btn-primary); --autods-jc-content-bg: var(--btn-primary); --autods-jc-tab-pill: var(--btn-primary); --autods-jc-tab-active-text: var(--neutral); }',
			'[data-theme-mode="light"] .autods-jc-plan__tab-slider { border-color: var(--btn-primary); }',
			'[data-theme-mode="light"] .autods-jc-plan__content-highlight { border-color: var(--btn-primary); }',
			'[data-theme-mode="light"] .autods-jc-plan__content-highlight .autods-jc-plan__kv-label, [data-theme-mode="light"] .autods-jc-plan__content-highlight .autods-jc-plan__line-title, [data-theme-mode="light"] .autods-jc-plan__content-highlight .autods-jc-plan__settings p { color: var(--gray-400); }',
			'[data-theme-mode="light"] .autods-jc-plan__content-highlight .autods-jc-plan__kv-value, [data-theme-mode="light"] .autods-jc-plan__content-highlight .autods-jc-plan__intro { color: var(--neutral); }',
			'[data-theme-mode="light"] .autods-jc-plan__content-highlight .autods-jc-plan__kv-value.text-danger { color: var(--red-300); }',
			'[data-theme-mode="light"] .autods-jc-plan__content-highlight .text-muted { color: var(--gray-400); }',
			'[data-theme-mode="light"] .autods-jc-plan__content-highlight .autods-jc-plan__line-card--multi { border-bottom-color: color-mix(in srgb, var(--neutral) 25%, var(--btn-primary) 75%); }',
			'[data-theme-mode="light"] .autods-jc-plan__content-highlight::-webkit-scrollbar-thumb { background: color-mix(in srgb, var(--neutral) 35%, var(--btn-primary) 65%); }'
		].join('\n');
		$('<style type="text/css" data-autods-jc-plan="1">' + css + '</style>').appendTo('head');
	}

	function autods_jc_render_service_thumb(item_image) {
		var imgUrl = item_image ? autods_jc_file_to_img_src(item_image) : '';
		if (imgUrl) {
			return '<div class="autods-jc-svc-pick__thumb"><img src="' +
				autods_jc_attr_url(imgUrl) + '" alt="" /></div>';
		}
		return '<div class="autods-jc-svc-pick__thumb autods-jc-svc-pick__thumb--empty"><span>' +
			autods_job_plan_esc(__('No service image')) + '</span></div>';
	}

	function autods_jc_format_repair_date(repair_date) {
		if (!repair_date) return '';
		try {
			if (frappe.datetime && frappe.datetime.str_to_user) {
				return frappe.datetime.str_to_user(repair_date);
			}
		} catch (e) { /* ignore */ }
		return String(repair_date);
	}

	function autods_jc_format_planned_window(start, end) {
		function compact(dt) {
			if (!dt) return '';
			var s = String(dt).trim();
			if (s.length >= 19 && s.charAt(10) === ' ') {
				return s.slice(0, 16);
			}
			return s;
		}
		var a = compact(start);
		var b = compact(end);
		if (!a && !b) return '';
		if (!a) return autods_job_plan_esc(b);
		if (!b) return autods_job_plan_esc(a);
		return autods_job_plan_esc(a) + ' → ' + autods_job_plan_esc(b);
	}

	function autods_jc_sync_tab_slider($tabs, $activeTab) {
		var $slider = $tabs.find('.autods-jc-plan__tab-slider');
		if (!$slider.length || !$activeTab.length) return;
		$slider.css({
			width: $activeTab.outerWidth() + 'px',
			transform: 'translateX(' + $activeTab.position().left + 'px)'
		});
	}

	function autods_jc_activate_plan_tab($wrapper, tabName) {
		var $tabs = $wrapper.find('.autods-jc-plan__tabs');
		var $activeTab = $tabs.find('.autods-jc-plan__tab[data-tab="' + tabName + '"]');
		if (!$activeTab.length) {
			return;
		}
		if (!$activeTab.hasClass('autods-jc-plan__tab--active')) {
			$tabs.find('.autods-jc-plan__tab').removeClass('autods-jc-plan__tab--active');
			$activeTab.addClass('autods-jc-plan__tab--active');
			$wrapper.find('.autods-jc-plan__panel').removeClass('autods-jc-plan__panel--active');
			$wrapper.find('.autods-jc-plan__panel[data-panel="' + tabName + '"]').addClass('autods-jc-plan__panel--active');
		}
		autods_jc_sync_tab_slider($tabs, $activeTab);
	}

	function autods_fetch_job_card_plan(repair_order_name, selected_charge_rows, callback) {
		frappe.call({
			method: 'autods.service.doctype.repair_order.repair_order.get_job_card_plan_by_repair_order',
			args: {
				repair_order: repair_order_name,
				selected_charge_rows: selected_charge_rows
			},
			freeze: true,
			freeze_message: __('Building job card plan...'),
			callback: function (r) {
				callback(r.message || {});
			}
		});
	}

	function autods_render_job_card_plan_dialog(plan, repair_order_name, selected_charge_rows, on_done) {
		var lines = plan.lines || [];
		if (!lines.length) {
			frappe.msgprint(__('Add at least one Service charge line on the Repair Order to create a Job Card.'));
			return;
		}

		autods_jc_inject_plan_styles();

		var serviceLineCount = plan.service_line_count != null ? plan.service_line_count : lines.length;
		var sets = plan.settings || {};
		var maxDays = sets.planning_max_extra_days != null ? sets.planning_max_extra_days : 0;
		var vehicleTitle = (plan.vehicle_title || '').trim();
		var plateNo = (plan.plate_no || '').trim();
		var repairDate = autods_jc_format_repair_date(plan.repair_date);
		var roId = plan.repair_order || repair_order_name;

		var metaLine = __('Repair Order {0}', [roId]);

		var heroHeadInner = (vehicleTitle
				? '<p class="autods-jc-plan__vehicle-title">' + autods_job_plan_esc(vehicleTitle) + '</p>'
				: '') +
			'<p class="autods-jc-plan__meta">' + autods_job_plan_esc(metaLine) + '</p>';

		var heroHtml = '<div class="autods-jc-plan__hero">' +
			'<div class="autods-jc-plan__hero-head">' + heroHeadInner + '</div>' +
			autods_jc_render_vehicle_photo(plan.vehicle_image) +
			'</div>';

		var firstLine = lines[0] || {};
		var summaryGridHtml =
			autods_jc_render_summary_column(
				autods_jc_render_summary_row(__('Date'), repairDate || firstLine.assignment_date || '', 'fa-calendar') +
				(plateNo ? autods_jc_render_summary_row(__('Plate'), plateNo, 'fa-car') : '')
			) +
			autods_jc_render_summary_column(
				autods_jc_render_summary_row(__('Item'), firstLine.item || '', 'fa-wrench') +
				autods_jc_render_summary_row(__('Job card'), serviceLineCount, 'fa-clipboard')
			) +
			autods_jc_render_summary_column(
				autods_jc_render_summary_row(__('Hour'), firstLine.standard_hours != null ? firstLine.standard_hours : firstLine.hours, 'fa-clock-o')
			);
		var summaryCardHtml = '<div class="autods-jc-plan__summary-card">' +
			'<div class="autods-jc-plan__summary-grid">' + summaryGridHtml + '</div></div>';

		var headHtml = '<div class="autods-jc-plan__head">' + heroHtml + summaryCardHtml + '</div>';

		var scheduleCards = lines.map(function (line) {
			var w = (line.warnings || []).map(function (x) { return autods_job_plan_esc(x); }).join('; ');
			var exists = line.existing_job_card
				? '<span class="indicator-pill yellow">' + autods_job_plan_esc(line.existing_job_card) + '</span>'
				: '<span class="text-muted">—</span>';
			var hoursVal = line.standard_hours != null ? line.standard_hours : line.hours;
			var kvRows = [
				autods_jc_render_kv_row(__('Date'), autods_job_plan_esc(line.assignment_date || '')),
				autods_jc_render_kv_row(__('Item'), autods_job_plan_esc(line.item || '')),
				autods_jc_render_kv_row(__('Description'), autods_job_plan_esc(line.description || '')),
				autods_jc_render_kv_row(__('Standard Hours'), autods_job_plan_esc(String(hoursVal != null ? hoursVal : ''))),
				autods_jc_render_kv_row(__('Work area'), autods_job_plan_esc(line.work_area || '')),
				autods_jc_render_kv_row(__('Skills group'), autods_job_plan_esc(line.technician_skills_group || '')),
				autods_jc_render_kv_row(__('Technician'), autods_job_plan_esc(line.technician || '')),
				autods_jc_render_kv_row(__('Planned window'), autods_jc_format_planned_window(line.planned_start, line.planned_end)),
				autods_jc_render_kv_row(__('Warnings'), '<span class="text-danger">' + (w || '—') + '</span>'),
				autods_jc_render_kv_row(__('Existing'), exists)
			].join('');
			var lineTitle = lines.length > 1
				? '<p class="autods-jc-plan__line-title">' + autods_job_plan_esc(__('Job Card {0}', [String(line.seq)])) + '</p>'
				: '';
			var lineCardClass = lines.length > 1
				? 'autods-jc-plan__line-card autods-jc-plan__line-card--multi'
				: 'autods-jc-plan__line-card';
			return '<div class="' + lineCardClass + '">' + lineTitle + kvRows + '</div>';
		}).join('');

		var planningHtml = '<div class="autods-jc-plan__settings">' +
			'<p class="autods-jc-plan__intro">' +
			autods_job_plan_esc(__('{0} Job Card(s) planned, one per selected service line.', [String(serviceLineCount)])) +
			'</p>' +
			'<p>' +
			autods_job_plan_esc(__('Auto work area: {0} · Auto technician: {1} · Respect bay capacity: {2} · Respect technician load: {3} · Allow overlapping schedules: {4}', [
				sets.auto_assign_work_area ? __('Yes') : __('No'),
				sets.auto_assign_technician ? __('Yes') : __('No'),
				sets.respect_work_area_capacity ? __('Yes') : __('No'),
				sets.respect_technician_load ? __('Yes') : __('No'),
				sets.allow_overlapping_schedules ? __('Yes') : __('No')
			])) + '</p>' +
			'<p>' +
			autods_job_plan_esc(__('Max extra days: {0} · Work area full: {1} · Past shop close: {2} · Technician overlap: {3}', [
				String(maxDays),
				sets.planning_work_area_full || 'warn_only',
				sets.planning_past_shop_close || 'warn_only',
				sets.planning_technician_overlap || 'warn_only'
			])) + '</p>' +
			'</div>';

		var detailCardHtml = '<div class="autods-jc-plan__detail-card">' +
			'<div class="autods-jc-plan__tabs">' +
			'<span class="autods-jc-plan__tab-slider" aria-hidden="true"></span>' +
			'<button type="button" class="autods-jc-plan__tab autods-jc-plan__tab--active" data-tab="schedule">' + autods_job_plan_esc(__('Schedule')) + '</button>' +
			'<button type="button" class="autods-jc-plan__tab" data-tab="planning">' + autods_job_plan_esc(__('Planning')) + '</button>' +
			'</div>' +
			'<div class="autods-jc-plan__panels">' +
			'<div class="autods-jc-plan__panel autods-jc-plan__panel--active" data-panel="schedule"><div class="autods-jc-plan__content-highlight">' + scheduleCards + '</div></div>' +
			'<div class="autods-jc-plan__panel" data-panel="planning"><div class="autods-jc-plan__content-highlight">' + planningHtml + '</div></div>' +
			'</div>' +
			'</div>';

		var planHtml = '<div class="autods-jc-plan">' +
			headHtml +
			detailCardHtml +
			'</div>';

		var createLabel = lines.length === 1 ? __('Create job card') : __('Create job cards');

		var d = new frappe.ui.Dialog({
			title: __('Job card plan'),
			size: 'large',
			fields: [
				{ fieldtype: 'HTML', fieldname: 'plan_html', options: planHtml }
			],
			primary_action_label: createLabel,
			primary_action: function () {
				frappe.call({
					method: 'autods.service.doctype.repair_order.repair_order.create_job_cards_from_plan_by_repair_order',
					args: {
						repair_order: repair_order_name,
						selected_charge_rows: selected_charge_rows
					},
					freeze: true,
					freeze_message: __('Creating job card(s)...'),
					callback: function (res) {
						d.hide();
						var msg = res.message || {};
						var created = msg.created || [];
						var skipped = msg.skipped || [];
						var parts = [];
						if (created.length === 1) {
							parts.push(__('Job Card created'));
						} else if (created.length > 1) {
							parts.push(__('{0} Job Cards created', [created.length]));
						}
						if (skipped.length) {
							parts.push(__('{0} skipped (Job Card already exists)', [skipped.length]));
						}
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

		var $planRoot = d.$wrapper.find('.autods-jc-plan');
		var resizeNs = 'resize.autods-jc-plan-' + String(Math.random()).slice(2);

		function autods_jc_sync_active_tab_slider() {
			var $tabs = $planRoot.find('.autods-jc-plan__tabs');
			var $activeTab = $tabs.find('.autods-jc-plan__tab--active').first();
			if (!$activeTab.length) {
				$activeTab = $tabs.find('.autods-jc-plan__tab[data-tab="schedule"]');
			}
			autods_jc_sync_tab_slider($tabs, $activeTab);
		}

		d.$wrapper.find('.autods-jc-plan__tab').on('click', function () {
			var tab = $(this).attr('data-tab');
			if (!tab) return;
			autods_jc_activate_plan_tab($planRoot, tab);
		});

		d.$wrapper.closest('.modal').on('hidden.bs.modal', function () {
			$(window).off(resizeNs);
		});
		$(window).on(resizeNs, autods_jc_sync_active_tab_slider);

		d.show();
		d.$wrapper.closest('.modal').one('shown.bs.modal', function () {
			autods_jc_activate_plan_tab($planRoot, 'schedule');
		});
		requestAnimationFrame(function () {
			autods_jc_activate_plan_tab($planRoot, 'schedule');
		});
	}

	function autods_open_job_card_plan_dialog(repair_order_name, selected_charge_rows, on_done) {
		autods_fetch_job_card_plan(repair_order_name, selected_charge_rows, function (plan) {
			autods_render_job_card_plan_dialog(plan, repair_order_name, selected_charge_rows, on_done);
		});
	}

	function autods_render_service_selection_dialog(selection, repair_order_name, on_done) {
		var services = selection.services || [];
		if (!services.length) {
			frappe.msgprint(__('Add at least one Service charge line on the Repair Order to create a Job Card.'));
			return;
		}

		autods_jc_inject_svc_pick_styles();

		var roId = selection.repair_order || repair_order_name;
		var vehicleTitle = (selection.vehicle_title || '').trim();
		var plateNo = (selection.plate_no || '').trim();
		var repairDate = autods_jc_format_repair_date(selection.repair_date);

		var metaParts = [];
		if (plateNo) {
			metaParts.push(__('Plate {0}', [plateNo]));
		}
		if (repairDate) {
			metaParts.push(repairDate);
		}
		var metaLine = metaParts.join(' · ');

		var headerHtml = '<div class="autods-jc-svc-pick__header">' +
			'<p class="autods-jc-svc-pick__ro-id">' + autods_job_plan_esc(__('Repair Order {0}', [roId])) + '</p>' +
			(vehicleTitle
				? '<p class="autods-jc-svc-pick__vehicle-title">' + autods_job_plan_esc(vehicleTitle) + '</p>'
				: '') +
			(metaLine ? '<p class="autods-jc-svc-pick__meta">' + autods_job_plan_esc(metaLine) + '</p>' : '') +
			'</div>';

		var cardsHtml = services.map(function (svc) {
			var hasExisting = !!svc.existing_job_card;
			var title = (svc.item || svc.description || __('Service')).trim();
			var hoursStr = (svc.standard_hours != null && svc.standard_hours !== '')
				? __('{0} hrs', [String(svc.standard_hours)])
				: '';
			var desc = (svc.description || '').trim();
			var subtitle = hoursStr && desc
				? hoursStr + ' | ' + desc
				: (hoursStr || desc);
			var cardThumb = autods_jc_render_service_thumb(svc.item_image);

			var actionHtml;
			if (hasExisting) {
				actionHtml = '<span class="indicator-pill yellow">' +
					autods_job_plan_esc(svc.existing_job_card) + '</span>';
			} else {
				actionHtml = '<button type="button" class="btn btn-default btn-sm autods-jc-svc-pick__continue" data-row-name="' +
					autods_job_plan_esc(svc.name) + '">' + autods_job_plan_esc(__('Continue')) + '</button>';
			}

			return '<div class="autods-jc-svc-pick__card' + (hasExisting ? ' autods-jc-svc-pick__card--disabled' : '') + '">' +
				cardThumb +
				'<div class="autods-jc-svc-pick__body">' +
				'<p class="autods-jc-svc-pick__title">' + autods_job_plan_esc(title) + '</p>' +
				(subtitle ? '<p class="autods-jc-svc-pick__subtitle">' + autods_job_plan_esc(subtitle) + '</p>' : '') +
				'</div>' +
				'<div class="autods-jc-svc-pick__action">' + actionHtml + '</div>' +
				'</div>';
		}).join('');

		var body = '<div class="autods-jc-svc-pick">' +
			headerHtml +
			'<div class="autods-jc-svc-pick__cards">' + cardsHtml + '</div>' +
			'</div>';

		var d = new frappe.ui.Dialog({
			title: __('Select service'),
			size: 'large',
			fields: [{ fieldtype: 'HTML', fieldname: 'pick_html', options: body }]
		});

		d.$wrapper.find('.autods-jc-svc-pick__continue').on('click', function () {
			var rowName = $(this).attr('data-row-name');
			if (!rowName) return;
			d.hide();
			autods_open_job_card_plan_dialog(repair_order_name, [rowName], on_done);
		});

		d.get_primary_btn().hide();
		d.show();
	}

	function autods_show_job_card_service_selection(repair_order_name, on_done) {
		frappe.call({
			method: 'autods.service.doctype.repair_order.repair_order.get_job_card_service_selection',
			args: { repair_order: repair_order_name },
			freeze: true,
			freeze_message: __('Loading service lines...'),
			callback: function (r) {
				autods_render_service_selection_dialog(r.message || {}, repair_order_name, on_done);
			}
		});
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
		autods_show_job_card_service_selection(repair_order_name, on_done);
	};
})();
