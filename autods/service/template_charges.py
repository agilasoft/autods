# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Map Service Template charge rows onto Repair Order / Repair Estimate charges."""

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
