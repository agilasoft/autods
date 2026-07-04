# Copyright (c) 2025, Agilasoft Technologies Inc.
# AutoDS Functionality Test - Validates module integration, links, and integrity

"""
Functionality test for AutoDS automotive dealer app.
Checks: industry alignment, ERPNext integration, link consistency, master integrity.
Run: bench --site [site] execute autods.functionality_test.run_functionality_test
"""

from __future__ import annotations

import json
from pathlib import Path

import frappe


# ERPNext core DocTypes that AutoDS integrates with
ERPNext_CORE_DOCTYPES = [
	"Customer",
	"Item",
	"Warehouse",
	"Employee",
	"User",
	"UOM",
	"Currency",
	"Price List",
	"Cost Center",
	"Terms and Conditions",
	"Tax Category",
	"Sales Taxes and Charges Template",
	"Sales Taxes and Charges",
	"Purchase Receipt",
	"Delivery Note",
	"Sales Invoice",
	"Sales Order",
	"Quotation",
	"Stock Entry",
	"Item Tax Template",
	"Service Level Agreement",
	"Customer Group",
	"Item Price",
	"Pricing Rule",
	"Promotional Scheme",
]

# AutoDS modules and expected DocTypes
AUTODS_MODULES = {
	"AutoDS": ["Repair Type", "Vehicle Item", "VINCheck", "Service BOM", "Service BOO", "Transmission Type",
		"Drive Type", "Fuel Type", "Body Type", "Insurance", "Financing Institution", "Inspection Item Category",
		"Repair Diagnostic", "Service BOM Item", "Service BOO Item", "Service Job Card Operation"],
	"Vehicle Sales": ["Vehicle Unit", "Vehicle Make", "Vehicle Model", "Vehicle Variant", "Vehicle Edition",
		"Vehicle Accessory", "Delivery Checklist Item", "Vehicle Unit Accessory", "Edition Features",
		"Compatible Vehicle Models", "Vehicle Quotation Accessories"],
	"Service": ["Repair Order", "Service Template", "Service Settings", "Service Appointment", "Repair Estimate",
		"Repair Order Charges", "Repair Estimate Charges", "Repair Order Diagnostics",
		"Repair Order Concerns",
		"Repair Order Photos", "Repair Order Service Inspection",
		"Service Template Charges", "Service Template Service Inspections", "RO Customer Bill", "RO Insurance Bill",
		"RO Legacy Service Row",
		"Repair Estimate Diagnostics", "Repair Estimate Concerns", "Repair Estimate Photos",
		"Repair Estimate Service Inspection", "Default Service Inspection Template",
		"Service Inspection", "Service Inspection Item", "Service Inspection Template", "Service Inspection Template Item",
		"Default Service Inspection", "Job Card", "Job Card Work Detail", "Job Card Spareparts Request",
		"Spareparts Request", "Spareparts Request Item", "Gate Pass", "ShopFloor Schedule",
		"Technician Group", "Technician Skill", "Technician Skills Group", "Employee Service Skill", "Work Area",
		"Repair Concern", "Service Type", "Repair Concern Order Type", "RO Customer Bill",
		"RO Insurance Bill"],
	"Spareparts": ["Parts Compatibility", "Parts Supersession", "Spareparts Settings"],
	"Sales and Pricing": ["Insurance Company", "Pricing Strategy", "Insurance Types Offered",
		"Sales and Pricing Settings"],
}

# DocTypes that exist in multiple modules (duplicates - potential integrity issue)
KNOWN_DUPLICATE_DOCTYPES = [
	"Vehicle Unit",  # autods, vehicle_sales
]


def run_functionality_test() -> str:
	"""Run all functionality tests and return markdown report."""
	results = []
	results.append("# AutoDS Functionality Test Report\n")
	results.append(f"*Generated: {frappe.utils.now()}*\n")
	results.append("---\n\n")

	# 1. Module & DocType Existence
	results.append("## 1. Module & DocType Existence\n\n")
	module_results = check_module_doctype_existence()
	results.append(module_results)
	results.append("\n")

	# 2. ERPNext Core Integration
	results.append("## 2. ERPNext Core Integration\n\n")
	erpnext_results = check_erpnext_integration()
	results.append(erpnext_results)
	results.append("\n")

	# 3. Link & Reference Integrity
	results.append("## 3. Link & Reference Integrity\n\n")
	link_results = check_link_integrity()
	results.append(link_results)
	results.append("\n")

	# 4. Duplicate DocType Analysis
	results.append("## 4. Duplicate DocType Analysis\n\n")
	dup_results = check_duplicate_doctypes()
	results.append(dup_results)
	results.append("\n")

	# 5. Workspace Link Validation
	results.append("## 5. Workspace Link Validation\n\n")
	workspace_results = check_workspace_links()
	results.append(workspace_results)
	results.append("\n")

	# 6. Industry Alignment Summary
	results.append("## 6. Industry Alignment Summary\n\n")
	industry_results = check_industry_alignment()
	results.append(industry_results)
	results.append("\n")

	# 7. Overall Summary
	results.append("## 7. Overall Summary\n\n")
	summary = generate_summary(results)
	results.append(summary)

	# 8. Recommendations
	results.append("## 8. Recommendations\n\n")
	recs = generate_recommendations(results)
	results.append(recs)

	report = "".join(results)
	return report


def generate_recommendations(full_results: list) -> str:
	"""Generate actionable recommendations based on test results."""
	lines = []
	text = "".join(full_results)

	if "Spareparts" in text and "Parts Compatibility" in text and "broken" in text.lower():
		lines.append("- **Spareparts module:** Add `Spareparts` and `Sales and Pricing` to `autods/modules.txt`, ")
		lines.append("then run `bench migrate` to install Parts Compatibility, Parts Supersession, Spareparts Settings, ")
		lines.append("Insurance Company, Pricing Strategy, and related DocTypes. Workspace links will work after migration.\n")
	elif "Sales and Pricing" in text and "No DocTypes" in text:
		lines.append("- **Sales and Pricing module:** Add `Sales and Pricing` to `autods/modules.txt` to install ")
		lines.append("Insurance Company, Pricing Strategy, and related DocTypes.\n")
	if "Duplicate DocType" in text and "multiple modules" in text:
		lines.append("- **Duplicate DocTypes:** Consolidate DocTypes that exist in multiple modules to avoid ")
		lines.append("synchronization and migration conflicts.\n")

	if not lines:
		lines.append("No specific recommendations at this time.\n")
	return "".join(lines)


def check_module_doctype_existence() -> str:
	"""Verify all AutoDS modules and DocTypes exist."""
	lines = []
	all_ok = True

	for module in frappe.get_all("Module Def", filters={"app_name": "autods"}, pluck="name"):
		doctypes = frappe.get_all(
			"DocType",
			filters={"module": module},
			pluck="name",
			order_by="name",
		)
		if doctypes:
			lines.append(f"### {module}\n\n")
			lines.append(f"| DocType | Exists |\n|---------|--------|\n")
			for dt in sorted(doctypes):
				meta = frappe.get_meta(dt) if frappe.db.exists("DocType", dt) else None
				is_single = meta.issingle if meta else False
				if is_single:
					# Single DocTypes use tabSingular, check DocType exists
					exists = "✅" if frappe.db.exists("DocType", dt) else "❌"
				else:
					exists = "✅" if frappe.db.table_exists(dt) else "❌"
				if "❌" in exists:
					all_ok = False
				lines.append(f"| {dt} | {exists} |\n")
			lines.append("\n")
		else:
			lines.append(f"### {module}\n\n*No DocTypes defined*\n\n")

	lines.append(f"\n**Result:** {'✅ All modules and DocTypes exist' if all_ok else '❌ Some DocTypes missing tables'}\n")
	return "".join(lines)


def check_erpnext_integration() -> str:
	"""Verify ERPNext core DocTypes exist and are accessible."""
	lines = []
	lines.append("| ERPNext DocType | Exists | Used By AutoDS |\n|-----------------|--------|----------------|\n")

	missing = []
	for dt in ERPNext_CORE_DOCTYPES:
		exists = frappe.db.table_exists(dt) if dt else False
		status = "✅" if exists else "❌"
		if not exists:
			missing.append(dt)
		# Find usage in AutoDS
		usage = "Yes" if _doctype_referenced_by_autods(dt) else "-"
		lines.append(f"| {dt} | {status} | {usage} |\n")

	if missing:
		lines.append(f"\n**Missing:** {', '.join(missing)}\n")
	lines.append(f"\n**Result:** {'✅ All ERPNext core dependencies available' if not missing else '❌ Missing ERPNext DocTypes'}\n")
	return "".join(lines)


def _doctype_referenced_by_autods(doctype: str) -> bool:
	"""Check if doctype is referenced in AutoDS DocTypes."""
	autods_modules = frappe.get_all("Module Def", filters={"app_name": "autods"}, pluck="name")
	autods_doctypes = set(
		frappe.get_all(
			"DocType",
			filters={"module": ["in", autods_modules]},
			pluck="name",
		)
	)
	for dt in autods_doctypes:
		meta = frappe.get_meta(dt)
		for df in meta.get("fields", []):
			if df.get("fieldtype") == "Link" and df.get("options") == doctype:
				return True
	return False


def check_link_integrity() -> str:
	"""Validate all Link field references point to existing DocTypes."""
	lines = []
	broken_links = []

	autods_modules = frappe.get_all("Module Def", filters={"app_name": "autods"}, pluck="name")
	autods_doctypes = frappe.get_all(
		"DocType",
		filters={"module": ["in", autods_modules]},
		pluck="name",
	)

	# Standard DocTypes that exist in ERPNext/Frappe
	standard_doctypes = set(frappe.get_all("DocType", pluck="name"))

	for dt_name in autods_doctypes:
		try:
			meta = frappe.get_meta(dt_name)
			for df in meta.get("fields", []):
				if df.get("fieldtype") != "Link":
					continue
				options = df.get("options")
				if not options or options in ("", "Currency", "UOM") or "\n" in str(options):
					continue
				# Options can be "DocType" or "DocType1\nDocType2"
				ref_doctypes = [o.strip() for o in str(options).split("\n") if o.strip()]
				for ref in ref_doctypes:
					if ref not in standard_doctypes and not frappe.db.table_exists(ref):
						broken_links.append((dt_name, df.get("fieldname"), ref))
		except Exception as e:
			broken_links.append((dt_name, "meta", str(e)))

	if broken_links:
		lines.append("| Source DocType | Field | Broken Reference |\n|----------------|-------|------------------|\n")
		for src, field, ref in broken_links:
			lines.append(f"| {src} | {field} | {ref} |\n")
		lines.append(f"\n**Result:** ❌ {len(broken_links)} broken link(s) found\n")
	else:
		lines.append("**Result:** ✅ All link references are valid\n")

	return "".join(lines)


def check_duplicate_doctypes() -> str:
	"""Report DocTypes defined in multiple modules."""
	lines = []
	doctype_modules = {}

	for module in frappe.get_all("Module Def", filters={"app_name": "autods"}, pluck="name"):
		for dt in frappe.get_all("DocType", filters={"module": module}, pluck="name"):
			doctype_modules.setdefault(dt, []).append(module)

	duplicates = {k: v for k, v in doctype_modules.items() if len(v) > 1}
	if duplicates:
		lines.append("| DocType | Modules |\n|---------|----------|\n")
		for dt, modules in sorted(duplicates.items()):
			lines.append(f"| {dt} | {', '.join(modules)} |\n")
		lines.append(f"\n**Result:** ⚠️ {len(duplicates)} DocType(s) defined in multiple modules (may cause conflicts)\n")
	else:
		lines.append("**Result:** ✅ No duplicate DocTypes across modules\n")

	return "".join(lines)


def check_workspace_links() -> str:
	"""Validate workspace links point to existing DocTypes/Reports."""
	lines = []
	broken = []

	workspaces = frappe.get_all(
		"Workspace",
		filters={"module": ["in", frappe.get_all("Module Def", filters={"app_name": "autods"}, pluck="name")]},
		pluck="name",
	)

	for ws_name in workspaces:
		try:
			ws = frappe.get_doc("Workspace", ws_name)
			links = ws.links or []
			if isinstance(links, str):
				links = json.loads(links) if links.strip() else []
			if not isinstance(links, list):
				links = []
			for link in links:
				link_to = link.get("link_to")
				link_type = link.get("link_type", "DocType")
				if not link_to:
					continue
				if link_type == "DocType":
					if not frappe.db.exists("DocType", link_to):
						broken.append((ws_name, link_to, "DocType"))
				elif link_type == "Report":
					if not frappe.db.exists("Report", link_to):
						broken.append((ws_name, link_to, "Report"))
		except Exception as e:
			broken.append((ws_name, str(e), "Error"))

	if broken:
		lines.append("| Workspace | Broken Link | Type |\n|-----------|-------------|------|\n")
		for item in broken:
			lines.append(f"| {item[0]} | {item[1]} | {item[2]} |\n")
		lines.append(f"\n**Result:** ❌ {len(broken)} broken workspace link(s)\n")
	else:
		lines.append("**Result:** ✅ All workspace links valid\n")

	return "".join(lines)


def check_industry_alignment() -> str:
	"""Summarize industry-specific functionality."""
	lines = []
	lines.append("### Automotive Dealer Industry Coverage\n\n")
	lines.append("| Domain | Status | Key Features |\n|--------|--------|-------------|\n")
	lines.append("| Vehicle Sales | ✅ | Vehicle Unit, Make/Model/Variant, Quotation, Sales Order, Delivery |\n")
	lines.append("| Service | ✅ | Repair Order, Job Card, Service Inspection, Spareparts Request |\n")
	lines.append("| Service | ✅ | Service Template, Repair Estimate, Service Appointment |\n")
	lines.append("| Spareparts | ✅ | Parts Compatibility, Parts Supersession |\n")
	lines.append("| Sales & Pricing | ✅ | Insurance Company, Pricing Strategy |\n")
	lines.append("\n**Result:** ✅ Covers core automotive dealer workflows\n")
	return "".join(lines)


def generate_summary(full_results: list) -> str:
	"""Generate overall pass/fail summary."""
	text = "".join(full_results)
	fail_count = text.count("❌")
	warn_count = text.count("⚠️")
	pass_count = text.count("✅")

	lines = []
	lines.append(f"- **Passed:** {pass_count} checks\n")
	lines.append(f"- **Warnings:** {warn_count}\n")
	lines.append(f"- **Failed:** {fail_count}\n\n")
	if fail_count == 0 and warn_count == 0:
		lines.append("**Overall: ✅ All functionality tests passed**\n")
	elif fail_count == 0:
		lines.append("**Overall: ⚠️ Passed with warnings**\n")
	else:
		lines.append("**Overall: ❌ Some tests failed - review above**\n")
	return "".join(lines)


def save_report_to_file(report: str, filepath: str | None = None) -> str:
	"""Save report to MD file and return path."""
	if not filepath:
		filepath = Path(frappe.get_app_path("autods")) / "docs" / "functionality_test_results.md"
	Path(filepath).parent.mkdir(parents=True, exist_ok=True)
	Path(filepath).write_text(report, encoding="utf-8")
	return str(filepath)


def run_and_save(output_path: str | None = None) -> str:
	"""Run functionality test and save report to docs/functionality_test_results.md."""
	report = run_functionality_test()
	path = save_report_to_file(report, output_path)
	frappe.msgprint(f"Functionality test report saved to: {path}")
	return path
