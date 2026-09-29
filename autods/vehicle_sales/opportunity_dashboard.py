# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt


def get_data(data=None):
	"""Replace Quotation with Vehicle Sales Quote on Opportunity Connections."""
	data = data or {}
	data["fieldname"] = data.get("fieldname") or "opportunity"
	data["transactions"] = [
		{"items": ["Vehicle Sales Quote", "Request for Quotation", "Supplier Quotation"]},
	]
	return data
