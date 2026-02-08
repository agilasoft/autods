// Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

// Inject dark text for calendar events (override Frappe's light text for readability)
(function () {
	if (document.getElementById('autods-calendar-contrast')) return;
	var style = document.createElement('style');
	style.id = 'autods-calendar-contrast';
	style.textContent = [
		'body .fc-theme-standard .fc-event,',
		'body .fc-theme-standard .fc-event .fc-event-main,',
		'body .fc-theme-standard .fc-event .fc-event-main-frame,',
		'body .fc-theme-standard .fc-event .fc-event-title-container,',
		'body .fc-theme-standard .fc-event a,',
		'body .fc-theme-standard .fc-event .fc-event-main a,',
		'body .fc-theme-standard .fc-time-grid-event .fc-event-main,',
		'body .fc-theme-standard .fc-daygrid-event .fc-event-main,',
		'body .fc-theme-standard .fc-time-grid-event .fc-event-title,',
		'body .fc-theme-standard .fc-daygrid-event .fc-event-title {',
		'  color: rgb(0, 112, 204) !important;',
		'}',
		'body .fc-theme-standard .fc-event .fc-event-title { font-weight: 600; }'
	].join('\n');
	document.head.appendChild(style);
})();

frappe.views.calendar['Service Appointment'] = {
	// start/end point to our returned keys so prepare_events keeps our datetime values
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
	style_map: {
		Scheduled: 'default',
		Confirmed: 'primary',
		'In Progress': 'warning',
		Completed: 'success',
		'No-show': 'danger',
		Cancelled: 'default'
	},
	get_css_class: function(data) {
		return data.status ? 'calendar-' + (data.status.toLowerCase().replace(/\s+/g, '-')) : '';
	}
};
