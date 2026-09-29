# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Parts Compatibility match engine: Item spare parts vs Vehicle Unit specs."""

from __future__ import annotations

import frappe
from frappe import _

VEHICLE_SPEC_FIELDS = (
	"make",
	"model",
	"variant",
	"year",
	"transmission_type",
)

FILTER_TO_SPEC = {
	"vehicle_make": "make",
	"vehicle_model": "model",
	"vehicle_variant": "variant",
	"vehicle_year_model": "year",
	"vehicle_transmission_type": "transmission_type",
}


def get_vehicle_specs(vehicle_unit: str) -> dict:
	frappe.clear_document_cache("Vehicle Unit", vehicle_unit)
	values = frappe.db.get_value(
		"Vehicle Unit",
		vehicle_unit,
		["make", "model", "variant", "year_model", "transmission_type"],
		as_dict=True,
	)
	if not values:
		frappe.throw(_("Vehicle Unit {0} not found").format(vehicle_unit))
	return {
		"make": values.make,
		"model": values.model,
		"variant": values.variant,
		"year": values.year_model,
		"transmission_type": values.transmission_type,
	}


def get_vehicle_specs_from_filters(filters: dict | None) -> dict | None:
	filters = dict(filters or {})
	if filters.get("vehicle_unit"):
		return get_vehicle_specs(filters["vehicle_unit"])

	specs = {key: None for key in VEHICLE_SPEC_FIELDS}
	has_spec = False
	for filter_field, spec_field in FILTER_TO_SPEC.items():
		value = filters.get(filter_field)
		if value not in (None, ""):
			specs[spec_field] = value
			has_spec = True

	if not has_spec:
		return None
	return specs


def rule_matches(rule, specs: dict) -> bool:
	if not rule.get("is_active", 1):
		return False

	if rule.get("applies_to_all_vehicles"):
		return True

	if rule.get("vehicle_make") and rule.get("vehicle_make") != specs.get("make"):
		return False
	if rule.get("vehicle_model") and rule.get("vehicle_model") != specs.get("model"):
		return False
	if rule.get("vehicle_variant") and rule.get("vehicle_variant") != specs.get("variant"):
		return False
	if rule.get("transmission_type") and rule.get("transmission_type") != specs.get("transmission_type"):
		return False

	year = specs.get("year")
	if year is not None and year != "":
		year = int(year)
		year_from = int(rule.get("year_from") or 0)
		year_to = int(rule.get("year_to") or 0)
		if year_from and year < year_from:
			return False
		if year_to and year > year_to:
			return False

	return True


def get_compatibility_match_condition(alias: str = "pc") -> str:
	a = alias
	return f"""(
		IFNULL({a}.is_active, 1) = 1
		AND (
			{a}.applies_to_all_vehicles = 1
			OR (
				(IFNULL({a}.vehicle_make, '') = '' OR {a}.vehicle_make = %(make)s)
				AND (IFNULL({a}.vehicle_model, '') = '' OR {a}.vehicle_model = %(model)s)
				AND (IFNULL({a}.vehicle_variant, '') = '' OR {a}.vehicle_variant = %(variant)s)
				AND (IFNULL({a}.transmission_type, '') = '' OR {a}.transmission_type = %(transmission_type)s)
				AND (%(year)s IS NULL OR IFNULL({a}.year_from, 0) = 0 OR %(year)s >= {a}.year_from)
				AND (%(year)s IS NULL OR IFNULL({a}.year_to, 0) = 0 OR %(year)s <= {a}.year_to)
			)
		)
		AND {a}.part IS NOT NULL AND {a}.part != ''
	)"""


def get_compatibility_bind_values(specs: dict) -> dict:
	year = specs.get("year")
	if year not in (None, ""):
		year = int(year)
	else:
		year = None

	return {
		"make": specs.get("make") or "",
		"model": specs.get("model") or "",
		"variant": specs.get("variant") or "",
		"transmission_type": specs.get("transmission_type") or "",
		"year": year,
	}


def get_compatible_parts_subquery(specs: dict, alias: str = "pc") -> tuple[str, dict]:
	condition = get_compatibility_match_condition(alias)
	bind = get_compatibility_bind_values(specs)
	return condition, bind


def get_compatible_parts_sql(specs: dict) -> tuple[str, dict]:
	condition, bind = get_compatible_parts_subquery(specs)
	query = f"""
		SELECT DISTINCT pc.part AS part, pc.name AS compatibility_rule
		FROM `tabParts Compatibility` pc
		WHERE {condition}
		ORDER BY pc.part
	"""
	return query, bind


@frappe.whitelist()
def get_compatible_parts(vehicle_unit=None, **filters):
	specs = None
	if vehicle_unit:
		specs = get_vehicle_specs(vehicle_unit)
	else:
		specs = get_vehicle_specs_from_filters(filters)

	if not specs:
		return []

	query, bind = get_compatible_parts_sql(specs)
	rows = frappe.db.sql(query, bind, as_dict=True)

	part_names = [row.part for row in rows]
	item_names = {}
	if part_names:
		for item in frappe.get_all(
			"Item",
			filters={"name": ["in", part_names]},
			fields=["name", "item_name"],
		):
			item_names[item.name] = item.item_name

	results = []
	for row in rows:
		results.append(
			{
				"part": row.part,
				"item_name": item_names.get(row.part),
				"compatibility_rule": row.compatibility_rule,
			}
		)
	return results


@frappe.whitelist()
def is_part_compatible(part, vehicle_unit=None, **filters):
	specs = None
	if vehicle_unit:
		specs = get_vehicle_specs(vehicle_unit)
	else:
		specs = get_vehicle_specs_from_filters(filters)

	if not specs:
		return False

	rules = frappe.get_all(
		"Parts Compatibility",
		filters={"part": part, "is_active": 1},
		fields=[
			"name",
			"applies_to_all_vehicles",
			"vehicle_make",
			"vehicle_model",
			"vehicle_variant",
			"transmission_type",
			"year_from",
			"year_to",
			"is_active",
		],
	)
	return any(rule_matches(rule, specs) for rule in rules)


def resolve_specs_for_link_query(filters: dict) -> dict | None:
	"""Resolve vehicle specs for spareparts item link query; requires vehicle_unit or vehicle_model."""
	filters = dict(filters or {})
	if filters.get("vehicle_unit"):
		return get_vehicle_specs(filters["vehicle_unit"])

	specs = get_vehicle_specs_from_filters(filters)
	if specs and specs.get("model"):
		return specs
	return None
