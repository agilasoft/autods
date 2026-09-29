# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from autods.spareparts.compatibility import get_compatibility_match_condition, get_vehicle_specs


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "name",
			"label": _("Parts Compatibility"),
			"fieldtype": "Link",
			"options": "Parts Compatibility",
			"width": 140,
		},
		{"fieldname": "part", "label": _("Part"), "fieldtype": "Link", "options": "Item", "width": 140},
		{
			"fieldname": "applies_to_all_vehicles",
			"label": _("Applies to All Vehicles"),
			"fieldtype": "Check",
			"width": 80,
		},
		{"fieldname": "vehicle_make", "label": _("Vehicle Make"), "fieldtype": "Link", "options": "Vehicle Make", "width": 120},
		{"fieldname": "vehicle_model", "label": _("Vehicle Model"), "fieldtype": "Link", "options": "Vehicle Model", "width": 120},
		{"fieldname": "vehicle_variant", "label": _("Vehicle Variant"), "fieldtype": "Link", "options": "Vehicle Variant", "width": 120},
		{
			"fieldname": "transmission_type",
			"label": _("Transmission Type"),
			"fieldtype": "Link",
			"options": "Transmission Type",
			"width": 120,
		},
		{"fieldname": "year_from", "label": _("Year From"), "fieldtype": "Int", "width": 80},
		{"fieldname": "year_to", "label": _("Year To"), "fieldtype": "Int", "width": 80},
		{"fieldname": "is_active", "label": _("Is Active"), "fieldtype": "Check", "width": 80},
		{"fieldname": "notes", "label": _("Notes"), "fieldtype": "Data", "width": 200},
	]


def get_data(filters):
	filters = filters or {}
	conditions = []
	values = {}

	if filters.get("part"):
		conditions.append("p.part = %(part)s")
		values["part"] = filters["part"]
	if filters.get("vehicle_make"):
		conditions.append("p.vehicle_make = %(vehicle_make)s")
		values["vehicle_make"] = filters["vehicle_make"]
	if filters.get("vehicle_model"):
		conditions.append("p.vehicle_model = %(vehicle_model)s")
		values["vehicle_model"] = filters["vehicle_model"]
	if filters.get("is_active") in ("0", "1"):
		conditions.append("p.is_active = %(is_active)s")
		values["is_active"] = int(filters["is_active"])

	if filters.get("vehicle_unit"):
		specs = get_vehicle_specs(filters["vehicle_unit"])
		match_condition = get_compatibility_match_condition("p")
		conditions.append(match_condition)
		values.update(
			{
				"make": specs.get("make") or "",
				"model": specs.get("model") or "",
				"variant": specs.get("variant") or "",
				"transmission_type": specs.get("transmission_type") or "",
				"year": specs.get("year") if specs.get("year") not in (None, "") else None,
			}
		)

	where = " and ".join(conditions) if conditions else "1=1"
	query = f"""
		select
			p.name,
			p.part,
			p.applies_to_all_vehicles,
			p.vehicle_make,
			p.vehicle_model,
			p.vehicle_variant,
			p.transmission_type,
			p.year_from,
			p.year_to,
			p.is_active,
			p.notes
		from `tabParts Compatibility` p
		where {where}
		order by p.part, p.vehicle_make, p.vehicle_model
	"""
	return frappe.db.sql(query, values, as_dict=1)
