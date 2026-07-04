// Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

// Inject calendar styles for ShopFloor Schedule. See the matching file in
// service_appointment for the rationale; we use a separate style id and
// class prefix here so the two calendars stay independent.
(function () {
	var STYLE_ID = 'autods-sfs-calendar';
	if (document.getElementById(STYLE_ID)) return;
	var style = document.createElement('style');
	style.id = STYLE_ID;
	style.textContent = [
		'body .fc-theme-standard .fc-event .fc-event-title { font-weight: 600; }',
		'body .fc-theme-standard .fc-event.sfs-status-cancelled { opacity: 0.55; }',
		'body .fc-theme-standard .fc-event.sfs-status-cancelled .fc-event-title { text-decoration: line-through; }'
	].join('\n');
	document.head.appendChild(style);
})();

frappe.views.calendar['ShopFloor Schedule'] = {
	field_map: {
		start: 'start',
		end: 'end',
		id: 'name',
		title: 'title',
		allDay: 'allDay'
	},
	get_events_method: 'autods.service.doctype.shopfloor_schedule.shopfloor_schedule.get_events',
	filters: [
		{
			fieldtype: 'Link',
			fieldname: 'technician',
			options: 'Employee',
			label: __('Technician')
		},
		{
			fieldtype: 'Link',
			fieldname: 'work_area',
			options: 'Work Area',
			label: __('Work Area')
		},
		{
			fieldtype: 'Select',
			fieldname: 'status',
			options: 'Scheduled\nIn Progress\nCompleted\nCancelled',
			label: __('Status')
		}
	],
	get_css_class: function (data) {
		var palette = {
			'Scheduled':   'blue',
			'In Progress': 'orange',
			'Completed':   'green',
			'Cancelled':   'gray'
		};
		return palette[data && data.status] || 'blue';
	},
	options: {
		eventClassNames: function (arg) {
			var status = arg && arg.event && arg.event.extendedProps && arg.event.extendedProps.status;
			if (!status) return [];
			return ['sfs-status-' + String(status).toLowerCase().replace(/\s+/g, '-')];
		}
	}
};
