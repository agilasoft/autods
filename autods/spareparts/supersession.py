# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Active parts-supersession chain.

Settings flags on Spareparts Settings are honored here: the chain is empty
when supersession is off, and an in-stock suggestion is returned only when
auto-suggest is on.
"""

import frappe
from frappe.utils import flt, getdate, nowdate


def supersession_enabled():
	if not frappe.db.exists("DocType", "Spareparts Settings"):
		return False
	return bool(frappe.db.get_single_value("Spareparts Settings", "enable_parts_supersession"))


def auto_suggest_enabled():
	if not supersession_enabled():
		return False
	return bool(frappe.db.get_single_value("Spareparts Settings", "auto_suggest_superseded_parts"))


def approval_required():
	if not frappe.db.exists("DocType", "Spareparts Settings"):
		return False
	return bool(frappe.db.get_single_value("Spareparts Settings", "require_supersession_approval"))


def get_replacement_chain(item_code, max_depth=5):
	"""Walk original → superseded, including two-way links, without looping."""
	if not item_code or not supersession_enabled():
		return []
	if not frappe.db.table_exists("Parts Supersession"):
		return []

	seen = {item_code}
	frontier = [item_code]
	chain = []
	today = getdate(nowdate())
	for _ in range(max_depth):
		if not frontier:
			break
		rows = frappe.db.sql(
			"""
			SELECT original_part, superseded_part, is_two_way, effective_date, end_date
			FROM `tabParts Supersession`
			WHERE status = 'Active'
				AND (original_part IN %(items)s OR (is_two_way = 1 AND superseded_part IN %(items)s))
			""",
			{"items": frontier},
			as_dict=True,
		)
		frontier = []
		for row in rows:
			if row.effective_date and getdate(row.effective_date) > today:
				continue
			if row.end_date and getdate(row.end_date) < today:
				continue
			candidates = []
			if row.original_part in seen or row.original_part == item_code or row.original_part in chain:
				candidates.append(row.superseded_part)
			if row.is_two_way:
				candidates.append(row.original_part)
			for candidate in candidates:
				if not candidate or candidate in seen:
					continue
				seen.add(candidate)
				chain.append(candidate)
				frontier.append(candidate)
	return chain


def stock_qty(item_code, warehouse=None):
	if not item_code or not frappe.db.table_exists("Bin"):
		return 0
	filters = {"item_code": item_code}
	if warehouse:
		filters["warehouse"] = warehouse
	rows = frappe.get_all("Bin", filters=filters, pluck="actual_qty")
	return flt(sum(rows or []))


@frappe.whitelist()
def get_supersession_suggestion(item_code, warehouse=None):
	"""Return the first in-stock replacement when the picked part has none."""
	if not item_code or not auto_suggest_enabled():
		return None
	if stock_qty(item_code, warehouse) > 0:
		return None
	for replacement in get_replacement_chain(item_code):
		qty = stock_qty(replacement, warehouse)
		if qty > 0:
			item_name = frappe.db.get_value("Item", replacement, "item_name")
			return {"item_code": replacement, "item_name": item_name, "actual_qty": qty}
	return None


def replacement_sql_for_parts(part_subquery):
	"""SQL fragment listing active replacements of parts matched by part_subquery."""
	if not supersession_enabled() or not auto_suggest_enabled():
		return ""
	return f"""
		UNION
		SELECT ps.superseded_part
		FROM `tabParts Supersession` ps
		WHERE ps.status = 'Active'
			AND ps.original_part IN ({part_subquery})
			AND (ps.effective_date IS NULL OR ps.effective_date <= %(today)s)
			AND (ps.end_date IS NULL OR ps.end_date >= %(today)s OR ps.end_date = '0000-00-00')
		UNION
		SELECT ps.original_part
		FROM `tabParts Supersession` ps
		WHERE ps.status = 'Active' AND ps.is_two_way = 1
			AND ps.superseded_part IN ({part_subquery})
			AND (ps.effective_date IS NULL OR ps.effective_date <= %(today)s)
			AND (ps.end_date IS NULL OR ps.end_date >= %(today)s OR ps.end_date = '0000-00-00')
	"""
