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
	style_map: {
		Scheduled: 'default',
		'In Progress': 'warning',
		Completed: 'success',
		Cancelled: 'default'
	},
	get_css_class: function(data) {
		return data.status ? 'calendar-' + (data.status.toLowerCase().replace(/\s+/g, '-')) : '';
	}
};
