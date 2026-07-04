// Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

// Inject calendar styles for Service Appointment.
// Frappe already picks readable extra-light/dark text colors automatically,
// so we only add tweaks: a bolder title and a clearly inactive look for
// Cancelled events. Each calendar uses its own style id and class prefix
// to avoid collisions between doctypes.
(function () {
	var STYLE_ID = 'autods-sa-calendar';
	if (document.getElementById(STYLE_ID)) return;
	var style = document.createElement('style');
	style.id = STYLE_ID;
	style.textContent = [
		'body .fc-theme-standard .fc-event .fc-event-title { font-weight: 600; }',
		'body .fc-theme-standard .fc-event.sa-status-cancelled { opacity: 0.55; }',
		'body .fc-theme-standard .fc-event.sa-status-cancelled .fc-event-title { text-decoration: line-through; }',
		'body .fc-theme-standard .fc-event.sa-status-no-show { box-shadow: inset 0 0 0 2px var(--red-500, #e24c4c); }',
		'body .fc-theme-standard .fc-event.sa-status-no-show .fc-event-title { font-weight: 700; }'
	].join('\n');
	document.head.appendChild(style);
})();

frappe.views.calendar['Service Appointment'] = {
	field_map: {
		start: 'start',
		end: 'end',
		id: 'name',
		title: 'title',
		allDay: 'allDay'
	},
	get_events_method: 'autods.service.doctype.service_appointment.service_appointment.get_events',
	filters: [
		{
			fieldtype: 'Link',
			fieldname: 'service_advisor',
			options: 'Employee',
			label: __('Service Advisor')
		},
		{
			fieldtype: 'Select',
			fieldname: 'status',
			options: 'Scheduled\nConfirmed\nIn Progress\nCompleted\nNo-show\nCancelled',
			label: __('Status')
		}
	],
	// Map each status to a Frappe standard palette name. Frappe's calendar
	// applies extra-light shade as background and dark shade as text colour,
	// which keeps contrast readable without any !important overrides.
	get_css_class: function (data) {
		var palette = {
			'Scheduled':   'blue',
			'Confirmed':   'purple',
			'In Progress': 'orange',
			'Completed':   'green',
			'No-show':     'red',
			'Cancelled':   'gray'
		};
		return palette[data && data.status] || 'blue';
	},
	// Frappe's Calendar merges this into FullCalendar's options, so we can
	// tag each event with a status-derived class for the CSS above.
	options: {
		eventClassNames: function (arg) {
			var status = arg && arg.event && arg.event.extendedProps && arg.event.extendedProps.status;
			if (!status) return [];
			return ['sa-status-' + String(status).toLowerCase().replace(/\s+/g, '-')];
		}
	}
};
