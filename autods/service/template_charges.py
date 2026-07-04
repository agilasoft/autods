# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Map Service Template charge rows onto Repair Order / Repair Estimate charges."""

import frappe

TEMPLATE_CHARGE_FIELDS = (
	"service_item_type",
	"item",
	"item_name",
	"service_type",
	"description",
	"service_row",
	"standard_hours",
	"qty",
	"uom",
	"rate",
	"amount",
	"bill_type",
	"bill_to",
	"item_type",
	"warehouse",
	"color_code",
	"paint_type",
)


def charge_row_from_template(row, template_name, extra=None):
	"""Build a charges child row dict from a Service Template Charges row."""
	data = {"service_template": template_name}
	for field in TEMPLATE_CHARGE_FIELDS:
		val = row.get(field) if isinstance(row, dict) else getattr(row, field, None)
		if val is not None and val != "":
			data[field] = val
	if extra:
		data.update(extra)
	return data


def apply_template_terms(doc, template):
	"""Copy Terms and Conditions link and details from a Service Template."""
	terms = getattr(template, "terms_and_conditions", None)
	doc.terms_and_conditions = terms
	if terms:
		doc.tc_notes = (
			frappe.db.get_value("Terms and Conditions", terms, "terms")
			or getattr(template, "tc_notes", None)
		)
	else:
		doc.tc_notes = getattr(template, "tc_notes", None)
