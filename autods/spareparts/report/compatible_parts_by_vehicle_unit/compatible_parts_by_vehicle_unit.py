# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from autods.spareparts.compatibility import get_compatible_parts_sql, get_vehicle_specs


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "part", "label": _("Part"), "fieldtype": "Link", "options": "Item", "width": 140},
		{"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 180},
		{
			"fieldname": "compatibility_rule",
			"label": _("Compatibility Rule"),
			"fieldtype": "Link",
			"options": "Parts Compatibility",
			"width": 160,
		},
		{
			"fieldname": "transmission_type",
			"label": _("Rule Transmission"),
			"fieldtype": "Link",
			"options": "Transmission Type",
			"width": 120,
		},
		{"fieldname": "applies_to_all_vehicles", "label": _("Universal"), "fieldtype": "Check", "width": 80},
		{"fieldname": "notes", "label": _("Notes"), "fieldtype": "Data", "width": 200},
	]


def get_data(filters):
	filters = filters or {}
	vehicle_unit = filters.get("vehicle_unit")
	if not vehicle_unit:
		return []

	specs = get_vehicle_specs(vehicle_unit)
	query, bind = get_compatible_parts_sql(specs)
	rows = frappe.db.sql(query, bind, as_dict=True)
	if not rows:
		return []

	rule_names = [row.compatibility_rule for row in rows]
	rule_details = {
		rule.name: rule
		for rule in frappe.get_all(
			"Parts Compatibility",
			filters={"name": ["in", rule_names]},
			fields=["name", "transmission_type", "applies_to_all_vehicles", "notes"],
		)
	}

	part_names = [row.part for row in rows]
	item_names = {
		item.name: item.item_name
		for item in frappe.get_all(
			"Item",
			filters={"name": ["in", part_names]},
			fields=["name", "item_name"],
		)
	}

	results = []
	for row in rows:
		rule = rule_details.get(row.compatibility_rule) or {}
		results.append(
			{
				"part": row.part,
				"item_name": item_names.get(row.part),
				"compatibility_rule": row.compatibility_rule,
				"transmission_type": rule.get("transmission_type"),
				"applies_to_all_vehicles": rule.get("applies_to_all_vehicles"),
				"notes": rule.get("notes"),
			}
		)
	return results
