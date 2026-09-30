# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Desk notification counts for open dealer work."""


def get_notification_config():
	return {
		"for_doctype": {
			"Repair Order": {
				"status": ("in", ("Open", "Waiting Parts", "In Progress", "Paint", "QC", "Ready")),
			},
			"Job Card": {"status": ("in", ("Open", "Work In Progress", "On Hold"))},
			"Vehicle Sales Quote": {"status": "Open"},
			"Vehicle Sales Order": {"status": ("in", ("To Deliver and Bill", "To Deliver", "To Bill"))},
			"Spareparts Request": {"status": ("in", ("Draft", "Requested", "Approved"))},
		},
	}
