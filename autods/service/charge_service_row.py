# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt


def _charge_rows(ro):
	return list(getattr(ro, "charges", None) or [])


def iter_service_charge_rows(ro):
	"""Repair Order charge rows with Service item type, in document order."""
	for r in _charge_rows(ro):
		if (r.service_item_type or "").strip() == "Service":
			yield r


def service_line_index_for_charge_row_name(ro, charge_row_name: str | None) -> int | None:
	"""1-based index among Service lines for the charge child row `name`."""
	if not charge_row_name:
		return None
	for i, r in enumerate(iter_service_charge_rows(ro), start=1):
		if r.name == charge_row_name:
			return i
	return None


def sparepart_rows_for_material_request(
	ro,
	service_charge_row_name: str | None = None,
	explicit_charge_row_names: list[str] | None = None,
):
	"""Return Repair Order charge rows (Spareparts) to put on a Material Request.

	- If ``explicit_charge_row_names`` is set, only those rows (must be Spareparts on ``ro``).
	- Else if ``service_charge_row_name`` is set, only spareparts whose ``service_row`` index
	  matches that service line.
	- Else all Spareparts lines on the document (legacy behaviour).
	"""
	spare = [r for r in _charge_rows(ro) if (r.service_item_type or "").strip() == "Spareparts"]
	if explicit_charge_row_names:
		want = {str(x) for x in explicit_charge_row_names if x}
		return [r for r in spare if r.name in want]
	idx = service_line_index_for_charge_row_name(ro, service_charge_row_name)
	if idx is None:
		return spare
	return [r for r in spare if service_row_index(getattr(r, "service_row", None)) == idx]


def service_row_index(value) -> int | None:
	"""Parse the leading service index from a charges `service_row` value.

	Accepts legacy values like ``\"1\"`` and labeled values like ``\"1: Oil change\"``.
	"""
	s = (value or "").strip()
	if not s:
		return None
	i = 0
	while i < len(s) and s[i].isdigit():
		i += 1
	if i == 0:
		return None
	return int(s[:i])
