# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Custom link queries for Service forms (Frappe 16+ compatible)."""

import json

import frappe
from frappe import scrub
from frappe.desk.reportview import get_filters_cond, get_match_cond
from frappe.desk.search import validate_and_sanitize_search_inputs
from frappe.utils import nowdate


@frappe.whitelist()
@validate_and_sanitize_search_inputs
def charges_item_link_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	"""Item link search for repair charge lines: `custom_service_type` = selected Service Type OR unset.

	Replaces client-side ``['or', ...]`` filters, which Frappe 16's query builder no longer accepts
	in ``search_link`` (see ``apply_list_filters`` / ``operator.lower()``).
	"""
	doctype = "Item"
	conditions = []

	if isinstance(filters, str):
		filters = json.loads(filters) if filters else {}
	filters = dict(filters or {})

	service_type = filters.pop("service_type", None)
	if service_type:
		conditions.append(
			"(tabItem.custom_service_type = %(service_type)s OR tabItem.custom_service_type IS NULL)"
		)

	meta = frappe.get_meta(doctype, cached=True)
	searchfields = meta.get_search_fields()

	columns = ""
	extra_searchfields = [field for field in searchfields if field not in ["name", "description"]]

	if extra_searchfields:
		columns += ", " + ", ".join(extra_searchfields)

	if "description" in searchfields:
		columns += """, if(length(tabItem.description) > 40, \
			concat(substr(tabItem.description, 1, 40), "..."), description) as description"""

	searchfields = searchfields + [
		field
		for field in [
			searchfield or "name",
			"item_code",
			"item_group",
			"item_name",
		]
		if field not in searchfields
	]
	searchfields = " or ".join([field + " like %(txt)s" for field in searchfields])

	if filters and isinstance(filters, dict):
		if filters.get("customer") or filters.get("supplier"):
			party = filters.get("customer") or filters.get("supplier")
			item_rules_list = frappe.get_all(
				"Party Specific Item",
				filters={
					"party": ["!=", party],
					"party_type": "Customer" if filters.get("customer") else "Supplier",
				},
				fields=["restrict_based_on", "based_on_value"],
			)

			filters_dict = {}
			for rule in item_rules_list:
				if rule["restrict_based_on"] == "Item":
					rule["restrict_based_on"] = "name"
				filters_dict[rule.restrict_based_on] = []

			for rule in item_rules_list:
				filters_dict[rule.restrict_based_on].append(rule.based_on_value)

			for filter in filters_dict:
				filters[scrub(filter)] = ["not in", filters_dict[filter]]

			if filters.get("customer"):
				del filters["customer"]
			else:
				del filters["supplier"]
		else:
			filters.pop("customer", None)
			filters.pop("supplier", None)

	description_cond = ""
	if frappe.db.estimate_count(doctype) < 50000:
		description_cond = "or tabItem.description LIKE %(txt)s"

	bind = {
		"today": nowdate(),
		"txt": "%%%s%%" % txt,
		"_txt": txt.replace("%", ""),
		"start": start,
		"page_len": page_len,
	}
	if service_type:
		bind["service_type"] = service_type

	return frappe.db.sql(
		"""select
			tabItem.name {columns}
		from tabItem
		where tabItem.docstatus < 2
			and tabItem.disabled=0
			and tabItem.has_variants=0
			and (tabItem.end_of_life > %(today)s or ifnull(tabItem.end_of_life, '0000-00-00')='0000-00-00')
			and ({scond} or tabItem.item_code IN (select parent from `tabItem Barcode` where barcode LIKE %(txt)s)
				{description_cond})
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, item_name), locate(%(_txt)s, item_name), 99999),
			idx desc,
			name, item_name
		limit %(start)s, %(page_len)s """.format(
			columns=columns,
			scond=searchfields,
			fcond=get_filters_cond(doctype, filters, conditions).replace("%", "%%"),
			mcond=get_match_cond(doctype).replace("%", "%%"),
			description_cond=description_cond,
		),
		bind,
		as_dict=as_dict,
	)


@frappe.whitelist()
@validate_and_sanitize_search_inputs
def spareparts_item_link_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	"""Item link search for spareparts charge lines: only Parts Compatibility parts for vehicle_model."""
	doctype = "Item"
	conditions = []

	if isinstance(filters, str):
		filters = json.loads(filters) if filters else {}
	filters = dict(filters or {})

	vehicle_model = filters.pop("vehicle_model", None)
	if vehicle_model:
		parts_cond = """and tabItem.name IN (
				SELECT DISTINCT pc.part
				FROM `tabParts Compatibility` pc
				WHERE pc.vehicle_model = %(vehicle_model)s
					AND pc.part IS NOT NULL AND pc.part != ''
			)"""
	else:
		parts_cond = "and 1=0"

	meta = frappe.get_meta(doctype, cached=True)
	searchfields = meta.get_search_fields()

	columns = ""
	extra_searchfields = [field for field in searchfields if field not in ["name", "description"]]

	if extra_searchfields:
		columns += ", " + ", ".join(extra_searchfields)

	if "description" in searchfields:
		columns += """, if(length(tabItem.description) > 40, \
			concat(substr(tabItem.description, 1, 40), "..."), description) as description"""

	searchfields = searchfields + [
		field
		for field in [
			searchfield or "name",
			"item_code",
			"item_group",
			"item_name",
		]
		if field not in searchfields
	]
	searchfields = " or ".join([field + " like %(txt)s" for field in searchfields])

	if filters and isinstance(filters, dict):
		filters.pop("customer", None)
		filters.pop("supplier", None)

	description_cond = ""
	if frappe.db.estimate_count(doctype) < 50000:
		description_cond = "or tabItem.description LIKE %(txt)s"

	bind = {
		"today": nowdate(),
		"txt": "%%%s%%" % txt,
		"_txt": txt.replace("%", ""),
		"start": start,
		"page_len": page_len,
	}
	if vehicle_model:
		bind["vehicle_model"] = vehicle_model

	return frappe.db.sql(
		"""select
			tabItem.name {columns}
		from tabItem
		where tabItem.docstatus < 2
			and tabItem.disabled=0
			and tabItem.has_variants=0
			and (tabItem.end_of_life > %(today)s or ifnull(tabItem.end_of_life, '0000-00-00')='0000-00-00')
			and ({scond} or tabItem.item_code IN (select parent from `tabItem Barcode` where barcode LIKE %(txt)s)
				{description_cond})
			{parts_cond} {fcond} {mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, item_name), locate(%(_txt)s, item_name), 99999),
			idx desc,
			name, item_name
		limit %(start)s, %(page_len)s """.format(
			columns=columns,
			scond=searchfields,
			parts_cond=parts_cond,
			fcond=get_filters_cond(doctype, filters, conditions).replace("%", "%%"),
			mcond=get_match_cond(doctype).replace("%", "%%"),
			description_cond=description_cond,
		),
		bind,
		as_dict=as_dict,
	)
