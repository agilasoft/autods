# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Shop-floor status for Repair Order.

Estimate statuses stay on Repair Estimate. Repair Order uses this list so
open-order, aging, and workspace charts describe the workshop, not the quote.
"""

SHOP_STATUSES = (
	"Open",
	"Waiting Parts",
	"In Progress",
	"Paint",
	"QC",
	"Ready",
	"Completed",
	"Cancelled",
)

OPEN_SHOP_STATUSES = tuple(status for status in SHOP_STATUSES if status not in ("Completed", "Cancelled"))

LEGACY_STATUS_MAP = {
	"Draft": "Open",
	"Submitted": "Open",
	"Approved": "Open",
	"Rejected": "Cancelled",
	"Converted to RO": "Open",
}


def normalize_shop_status(status):
	"""Map a stored or legacy status onto the shop-floor list."""
	if not status:
		return "Open"
	if status in SHOP_STATUSES:
		return status
	return LEGACY_STATUS_MAP.get(status, "Open")
