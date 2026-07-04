# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt
#
# Migration patch: copy any existing legacy Vehicle Unit links (purchase_receipt
# pointing to ERPNext Purchase Receipt; delivery_note pointing to ERPNext
# Delivery Note) into the new Vehicle Sales link slots when those new fields
# are empty. The legacy fields stay populated (hidden) for audit history.

import frappe


def execute():
	if not frappe.db.has_table("Vehicle Unit"):
		return

	meta = frappe.get_meta("Vehicle Unit", cached=False)
	has_new_receiving = meta.has_field("vehicle_receiving")
	has_new_delivery = meta.has_field("vehicle_delivery_note")
	has_legacy_receipt = meta.has_field("purchase_receipt")
	has_legacy_delivery = meta.has_field("delivery_note")

	if not (has_new_receiving and has_new_delivery):
		# DocType not yet migrated to new schema
		return

	if has_legacy_receipt:
		# A legacy purchase_receipt is an ERPNext Purchase Receipt; we cannot
		# auto-create a Vehicle Receiving from it. Instead, leave vehicle_receiving
		# empty and emit an info log so the user can manually backfill.
		legacy_count = frappe.db.count(
			"Vehicle Unit",
			filters={"purchase_receipt": ["is", "set"], "vehicle_receiving": ["is", "not set"]},
		)
		if legacy_count:
			frappe.log_error(
				f"{legacy_count} Vehicle Unit(s) still reference legacy ERPNext Purchase Receipt. "
				"Run Vehicle Receiving manually for these or use the backfill helper to bridge them.",
				"AutoDS: Vehicle Unit migration info",
			)

	if has_legacy_delivery:
		legacy_count = frappe.db.count(
			"Vehicle Unit",
			filters={"delivery_note": ["is", "set"], "vehicle_delivery_note": ["is", "not set"]},
		)
		if legacy_count:
			frappe.log_error(
				f"{legacy_count} Vehicle Unit(s) still reference legacy ERPNext Delivery Note. "
				"Create Vehicle Delivery Notes manually for these.",
				"AutoDS: Vehicle Unit migration info",
			)
