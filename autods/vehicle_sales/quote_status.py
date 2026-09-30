# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Vehicle Sales Quote outcome transitions.

Ordered is set when a Vehicle Sales Order is submitted. Lost is an explicit
advisor action and requires a reason. Cancelling the only submitted order
returns an Ordered quote to Open.
"""

TERMINAL_QUOTE_STATUSES = ("Cancelled", "Lost")


def quote_status_after_order_submit(current_status):
	if current_status in TERMINAL_QUOTE_STATUSES:
		return current_status
	return "Ordered"


def quote_status_after_order_cancel(current_status, other_submitted_orders):
	if current_status != "Ordered":
		return current_status
	if other_submitted_orders:
		return "Ordered"
	return "Open"


def validate_lost_reason(lost_reason):
	return (lost_reason or "").strip()
