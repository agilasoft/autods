// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// Read-only charges summary on the Dashboard tab. Add or edit lines only via the Charges table.

frappe.provide("autods.charges_overview");

autods.charges_overview.CONFIG = {
	"Repair Order": {
		charges: "charges",
		charge_child: "Repair Order Charges",
	},
	"Repair Estimate": {
		charges: "charges",
		charge_child: "Repair Estimate Charges",
	},
	"Service Template": {
		charges: "charges",
		charge_child: "Service Template Charges",
	},
};

/** Leading index from `service_row` (e.g. "1", "1: Oil") — matches server `service_row_index`. */
function _service_row_label_index(sr) {
	var s = sr == null ? "" : String(sr).trim();
	if (!s) {
		return 0;
	}
	var m = s.match(/^(\d+)/);
	return m ? parseInt(m[1], 10) : 0;
}

function _flt(v) {
	return parseFloat(v) || 0;
}

function _fmt_cur(frm, v) {
	return frappe.format(_flt(v), {
		fieldtype: "Currency",
		options: frm.doc.currency || "",
	});
}

function _esc(s) {
	return frappe.utils.escape_html(s == null ? "" : String(s));
}

function _cfg(frm) {
	return autods.charges_overview.CONFIG[frm.doctype];
}

function _charge_rows(frm) {
	var cfg = _cfg(frm);
	return (frm.doc[cfg.charges] || []).slice();
}

function _service_rows_ordered(frm) {
	return _charge_rows(frm).filter(function(r) {
		return (r.service_item_type || "").trim() === "Service";
	});
}

/** Service charge rows with 1-based index and "N: item name" label (table order). */
function _service_lines_with_labels(frm) {
	return _service_rows_ordered(frm).map(function(s, si) {
		var num = si + 1;
		var nm = (s.item_name || s.item || "").trim();
		if (!nm) {
			nm = __("Service {0}", [String(num)]);
		}
		return { row: s, num: num, label: num + ": " + nm };
	});
}

/**
 * Service Select options for Spareparts/Overhead.
 * On Repair Order, omit Services locked by a non-Cancelled Job Card.
 * Pass keepLabel to preserve a row's current value so display is not wiped.
 */
function _build_service_row_opt_string(frm, keepLabel) {
	var labels = _service_lines_with_labels(frm)
		.filter(function(line) {
			if (frm.doctype !== "Repair Order") {
				return true;
			}
			if (typeof autods_is_service_charge_locked !== "function") {
				return true;
			}
			return !autods_is_service_charge_locked(frm, line.row && line.row.name);
		})
		.map(function(line) {
			return line.label;
		});
	var keep = (keepLabel || "").trim();
	if (keep && labels.indexOf(keep) === -1) {
		labels.push(keep);
		labels.sort(function(a, b) {
			var ia = _service_row_label_index(a) || 0;
			var ib = _service_row_label_index(b) || 0;
			return ia - ib;
		});
	}
	if (!labels.length) {
		return "";
	}
	return [""].concat(labels).join("\n");
}

function _service_row_label_for_charge(frm, serviceRow) {
	var lines = _service_lines_with_labels(frm);
	for (var i = 0; i < lines.length; i++) {
		if (lines[i].row.name === serviceRow.name) {
			return lines[i].label;
		}
	}
	return "";
}

function _service_name_set(frm) {
	var names = {};
	_service_rows_ordered(frm).forEach(function(s) {
		if (s.name) {
			names[s.name] = true;
		}
	});
	return names;
}

function _charge_linked_to_service(chargeRow, svcRow, ordinal, serviceNames) {
	var parent = (chargeRow.parent_service_charge || "").trim();
	if (parent) {
		if (parent === svcRow.name) {
			return true;
		}
		// Living parent pointing at another Service — do not also match via ordinal.
		if (serviceNames && serviceNames[parent]) {
			return false;
		}
		// Orphaned parent: fall back to ordinal.
	}
	return _service_row_label_index(chargeRow.service_row) === ordinal;
}

function _sync_service_row_label_from_parent(frm, row) {
	var cfg = _cfg(frm);
	if (!cfg || !row || !row.name) {
		return;
	}
	var parent = (row.parent_service_charge || "").trim();
	if (!parent) {
		return;
	}
	var svc = null;
	_service_rows_ordered(frm).some(function(s) {
		if (s.name === parent) {
			svc = s;
			return true;
		}
		return false;
	});
	if (!svc) {
		// Orphaned parent: rebind from ordinal when valid, else clear parent.
		var idx = _service_row_label_index(row.service_row);
		var svcLines = _service_lines_with_labels(frm);
		if (idx >= 1 && idx <= svcLines.length) {
			_set_parent_service_from_service_row(frm, row);
			var label = svcLines[idx - 1].label;
			if (label && (row.service_row || "").trim() !== label) {
				frappe.model.set_value(cfg.charge_child, row.name, "service_row", label);
			}
		} else {
			frappe.model.set_value(cfg.charge_child, row.name, "parent_service_charge", "");
		}
		return;
	}
	var label = _service_row_label_for_charge(frm, svc);
	if (label && (row.service_row || "").trim() !== label) {
		frappe.model.set_value(cfg.charge_child, row.name, "service_row", label);
	}
}

function _clear_orphaned_service_links(frm, deletedServiceName) {
	var cfg = _cfg(frm);
	if (!cfg || !deletedServiceName) {
		return;
	}
	(frm.doc[cfg.charges] || []).forEach(function(r) {
		if (!r.name) {
			return;
		}
		if ((r.parent_service_charge || "").trim() !== deletedServiceName) {
			return;
		}
		frappe.model.set_value(cfg.charge_child, r.name, "parent_service_charge", "");
		frappe.model.set_value(cfg.charge_child, r.name, "service_row", "");
	});
}

function _set_parent_service_from_service_row(frm, row) {
	if (!row || !row.name) {
		return;
	}
	var t = (row.service_item_type || "").trim();
	if (t !== "Spareparts" && t !== "Overhead") {
		return;
	}
	var cfg = _cfg(frm);
	if (!cfg) {
		return;
	}
	var idx = _service_row_label_index(row.service_row);
	var svcLines = _service_lines_with_labels(frm);
	var parent = "";
	if (idx >= 1 && idx <= svcLines.length) {
		parent = svcLines[idx - 1].row.name;
	}
	frappe.model.set_value(cfg.charge_child, row.name, "parent_service_charge", parent);
}

function _remap_service_row_labels(frm, optString, lines) {
	var cfg = _cfg(frm);
	if (!cfg || !optString) {
		return;
	}
	var child_doctype = cfg.charge_child;
	var table_field = cfg.charges;
	var svcLines = _service_lines_with_labels(frm);
	(frm.doc[table_field] || []).forEach(function(r) {
		if (!r.name) {
			return;
		}
		var t = (r.service_item_type || "").trim();
		if (t !== "Spareparts" && t !== "Overhead") {
			return;
		}
		var parent = (r.parent_service_charge || "").trim();
		if (parent) {
			_sync_service_row_label_from_parent(frm, r);
			return;
		}
		if (!(r.service_row || "").trim()) {
			return;
		}
		var sr = (r.service_row || "").trim();
		if (lines.indexOf(sr) !== -1) {
			_set_parent_service_from_service_row(frm, r);
			return;
		}
		var ix = _service_row_label_index(sr);
		if (ix >= 1 && ix <= svcLines.length) {
			frappe.model.set_value(child_doctype, r.name, "parent_service_charge", svcLines[ix - 1].row.name);
			frappe.model.set_value(child_doctype, r.name, "service_row", svcLines[ix - 1].label);
		}
	});
}

autods.charges_overview._debouncers = {};
autods.charges_overview._dash_debouncers = {};

function _schedule_dashboard_refresh(frm) {
	if (!frm || !frm.fields_dict || !frm.fields_dict.dashboard_html) {
		return;
	}
	var k = (frm.doctype || "") + ":" + (frm.docname || "new");
	if (!autods.charges_overview._dash_debouncers[k]) {
		autods.charges_overview._dash_debouncers[k] = frappe.utils.debounce(function(f) {
			if (
				window.autods &&
				autods.dashboard &&
				typeof autods.dashboard.refresh_charges_dashboard === "function"
			) {
				autods.dashboard.refresh_charges_dashboard(f);
			}
		}, 450);
	}
	autods.charges_overview._dash_debouncers[k](frm);
}

autods.charges_overview.schedule_render = function(frm) {
	var cfg = _cfg(frm);
	if (!cfg) {
		return;
	}
	var key = frm.doctype + ":" + (frm.docname || "new");
	if (!autods.charges_overview._debouncers[key]) {
		autods.charges_overview._debouncers[key] = frappe.utils.debounce(function(f) {
			autods.charges_overview.render_all(f);
		}, 80);
	}
	autods.charges_overview._debouncers[key](frm);
	_schedule_dashboard_refresh(frm);
};

/** Update embedded dashboard charges panel only (read-only summary). */
autods.charges_overview.render_all = function(frm) {
	var cfg = _cfg(frm);
	if (!cfg) {
		return;
	}
	var html = autods.charges_overview.build_html(frm);
	var $dash = frm.fields_dict.dashboard_html && frm.fields_dict.dashboard_html.$wrapper.find(".autods-dashboard-charges-root");
	if ($dash && $dash.length) {
		$dash.html(html);
	}
};

autods.charges_overview.render = function(frm) {
	autods.charges_overview.render_all(frm);
};

autods.charges_overview.render_into = function(frm, $container) {
	if (!$container || !$container.length) {
		return;
	}
	$container.html(autods.charges_overview.build_html(frm));
};

autods.charges_overview.build_html = function(frm) {
	var cfg = _cfg(frm);
	if (!cfg) {
		return "";
	}
	var ch = frm.doc[cfg.charges] || [];
	var services = _service_rows_ordered(frm);
	var parts = ch.filter(function(r) {
		return (r.service_item_type || "").trim() === "Spareparts";
	});
	var overhead = ch.filter(function(r) {
		return (r.service_item_type || "").trim() === "Overhead";
	});

	var html = ['<div class="autods-charges-overview">'];
	html.push(
		'<p class="text-muted small mb-3">' +
			__("Summary only. Add or edit lines in the Charges tab.") +
			"</p>"
	);

	if (!ch.length) {
		html.push('<div class="text-muted small">' + __("No charge lines yet.") + "</div></div>");
		return html.join("");
	}

	var serviceNames = _service_name_set(frm);
	services.forEach(function(svc, si) {
		var ordinal = si + 1;
		var svc_parts = parts.filter(function(p) {
			return _charge_linked_to_service(p, svc, ordinal, serviceNames);
		});
		var svc_oh = overhead.filter(function(o) {
			return _charge_linked_to_service(o, svc, ordinal, serviceNames);
		});

		var title = svc.item || __("Service line {0}", [ordinal]);
		var sub = [];
		if (svc.description) {
			sub.push(_esc(svc.description));
		}
		if (svc.service_type) {
			sub.push(__("Type: {0}", [_esc(svc.service_type)]));
		}

		html.push('<div class="card mb-3 shadow-sm autods-charge-card">');
		html.push('<div class="card-header py-2 d-flex justify-content-between align-items-start flex-wrap gap-2">');
		html.push("<div><strong>" + _esc(title) + "</strong>");
		if (sub.length) {
			html.push('<div class="text-muted small mt-1">' + sub.join(" · ") + "</div>");
		}
		html.push("</div>");
		html.push('<div class="text-end">');
		html.push(
			'<div class="small mt-1"><span class="text-muted">' +
				_esc(svc.bill_type || __("Customer")) +
				"</span> · <strong>" +
				_fmt_cur(frm, svc.amount) +
				"</strong></div>"
		);
		html.push("</div></div>");

		html.push('<details class="border-top">');
		html.push(
			'<summary class="px-3 py-2 bg-light cursor-pointer small user-select-none">' +
				__("Spareparts ({0}) · Overhead ({1})", [svc_parts.length, svc_oh.length]) +
				"</summary>"
		);
		html.push('<div class="card-body pt-2 pb-3">');

		if (svc_parts.length) {
			html.push('<div class="font-weight-bold small mb-1">' + __("Spareparts") + "</div>");
			html.push('<table class="table table-bordered table-sm mb-3"><thead><tr>');
			["#", __("Item"), __("Qty"), __("Rate"), __("Amount"), __("Bill To")].forEach(function(h) {
				html.push("<th>" + h + "</th>");
			});
			html.push("</tr></thead><tbody>");
			svc_parts.forEach(function(p) {
				html.push("<tr>");
				html.push("<td>" + _esc(p.idx) + "</td>");
				html.push("<td>" + _esc(p.item || p.item_name || "") + "</td>");
				html.push("<td>" + _esc(p.qty) + "</td>");
				html.push("<td>" + _fmt_cur(frm, p.rate) + "</td>");
				html.push("<td>" + _fmt_cur(frm, p.amount) + "</td>");
				html.push("<td>" + _esc(p.bill_type || "") + "</td>");
				html.push("</tr>");
			});
			html.push("</tbody></table>");
		} else {
			html.push('<p class="text-muted small mb-2">' + __("No spareparts for this service.") + "</p>");
		}

		if (svc_oh.length) {
			html.push('<div class="font-weight-bold small mb-1">' + __("Overhead") + "</div>");
			html.push('<table class="table table-bordered table-sm mb-0"><thead><tr>');
			["#", __("Item"), __("Qty"), __("Rate"), __("Amount"), __("Bill To")].forEach(function(h) {
				html.push("<th>" + h + "</th>");
			});
			html.push("</tr></thead><tbody>");
			svc_oh.forEach(function(o) {
				html.push("<tr>");
				html.push("<td>" + _esc(o.idx) + "</td>");
				html.push("<td>" + _esc(o.item || o.item_name || "") + "</td>");
				html.push("<td>" + _esc(o.qty) + "</td>");
				html.push("<td>" + _fmt_cur(frm, o.rate) + "</td>");
				html.push("<td>" + _fmt_cur(frm, o.amount) + "</td>");
				html.push("<td>" + _esc(o.bill_type || "") + "</td>");
				html.push("</tr>");
			});
			html.push("</tbody></table>");
		} else {
			html.push('<p class="text-muted small mb-0">' + __("No overhead lines for this service.") + "</p>");
		}

		html.push("</div></details></div>");
	});

	var nSvc = services.length;
	var un_parts = parts.filter(function(p) {
		var parent = (p.parent_service_charge || "").trim();
		if (parent && serviceNames[parent]) {
			return false;
		}
		var sr = _service_row_label_index(p.service_row);
		return !sr || sr < 1 || sr > nSvc;
	});
	var un_oh = overhead.filter(function(o) {
		var parent = (o.parent_service_charge || "").trim();
		if (parent && serviceNames[parent]) {
			return false;
		}
		var sr = _service_row_label_index(o.service_row);
		return !sr || sr < 1 || sr > nSvc;
	});

	if (un_parts.length || un_oh.length) {
		html.push('<div class="card mb-0 border-warning shadow-sm">');
		html.push('<div class="card-header py-2">');
		html.push("<strong>" + __("Unassigned or invalid Service") + "</strong>");
		html.push(
			'<span class="text-muted small ml-2">' +
				__("Choose Service on each spare part and overhead line in the Charges table.") +
				"</span>"
		);
		html.push("</div>");
		html.push('<details open><summary class="px-3 py-2 bg-light small">' + __("Details") + "</summary>");
		html.push('<div class="card-body pt-2 pb-3">');
		if (un_parts.length) {
			html.push('<div class="font-weight-bold small mb-1">' + __("Spareparts") + "</div>");
			html.push('<table class="table table-bordered table-sm mb-3"><thead><tr>');
			["#", __("Item"), __("Qty"), __("Rate"), __("Amount"), __("Service")].forEach(function(h) {
				html.push("<th>" + h + "</th>");
			});
			html.push("</tr></thead><tbody>");
			un_parts.forEach(function(p) {
				html.push("<tr>");
				html.push("<td>" + _esc(p.idx) + "</td>");
				html.push("<td>" + _esc(p.item || p.item_name || "") + "</td>");
				html.push("<td>" + _esc(p.qty) + "</td>");
				html.push("<td>" + _fmt_cur(frm, p.rate) + "</td>");
				html.push("<td>" + _fmt_cur(frm, p.amount) + "</td>");
				html.push("<td>" + _esc(p.service_row || "") + "</td>");
				html.push("</tr>");
			});
			html.push("</tbody></table>");
		}
		if (un_oh.length) {
			html.push('<div class="font-weight-bold small mb-1">' + __("Overhead") + "</div>");
			html.push('<table class="table table-bordered table-sm mb-0"><thead><tr>');
			["#", __("Item"), __("Qty"), __("Rate"), __("Amount"), __("Service")].forEach(function(h) {
				html.push("<th>" + h + "</th>");
			});
			html.push("</tr></thead><tbody>");
			un_oh.forEach(function(o) {
				html.push("<tr>");
				html.push("<td>" + _esc(o.idx) + "</td>");
				html.push("<td>" + _esc(o.item || o.item_name || "") + "</td>");
				html.push("<td>" + _esc(o.qty) + "</td>");
				html.push("<td>" + _fmt_cur(frm, o.rate) + "</td>");
				html.push("<td>" + _fmt_cur(frm, o.amount) + "</td>");
				html.push("<td>" + _esc(o.service_row || "") + "</td>");
				html.push("</tr>");
			});
			html.push("</tbody></table>");
		}
		html.push("</div></details></div>");
	}

	html.push("</div>");
	return html.join("");
};

function _mutate_service_row_docfield_options(child_doctype, docname, optString) {
	if (!docname) {
		return;
	}
	var df = frappe.meta.get_docfield(child_doctype, "service_row", docname);
	if (df) {
		df.options = optString || "";
	}
}

function _mutate_df_options_in_list(docfields, optString) {
	if (!docfields || !docfields.length) {
		return;
	}
	docfields.forEach(function(df) {
		if (df && df.fieldname === "service_row") {
			df.options = optString || "";
		}
	});
}

/**
 * Persist options on base meta so make_docfield_copy_for (grid rebuild) inherits
 * the Service list instead of empty JSON options.
 */
function _mutate_base_service_row_options(child_doctype, optString) {
	var opts = optString || "";
	if (
		frappe.meta.docfield_map &&
		frappe.meta.docfield_map[child_doctype] &&
		frappe.meta.docfield_map[child_doctype].service_row
	) {
		frappe.meta.docfield_map[child_doctype].service_row.options = opts;
	}
	_mutate_df_options_in_list(frappe.meta.docfield_list[child_doctype], opts);
}

/** Push service_row Select options onto live grid docfield refs (not detached meta copies). */
function _apply_service_row_options_to_grid(frm, child_doctype, optString) {
	var cfg = _cfg(frm);
	if (!cfg || !frm.fields_dict || !frm.fields_dict[cfg.charges]) {
		return;
	}
	var grid = frm.fields_dict[cfg.charges].grid;
	if (!grid) {
		return;
	}

	/* Base / shared meta: selectable (unlocked) Services only — no keepLabel. */
	var baseOpt = optString || _build_service_row_opt_string(frm);
	_mutate_base_service_row_options(child_doctype, baseOpt);

	if (grid.fields_map && grid.fields_map.service_row) {
		grid.fields_map.service_row.options = baseOpt || "";
	}
	_mutate_df_options_in_list(grid.docfields, baseOpt);

	var meta_dn = (frm.doc && frm.doc.name) || frm.docname;
	if (meta_dn) {
		_mutate_service_row_docfield_options(child_doctype, meta_dn, baseOpt);
	}

	(frm.doc[cfg.charges] || []).forEach(function(r) {
		if (!r.name) {
			return;
		}
		var rowOpt = _build_service_row_opt_string(frm, r.service_row);
		_mutate_service_row_docfield_options(child_doctype, r.name, rowOpt);
	});

	if (!grid.grid_rows || !grid.grid_rows.length) {
		return;
	}
	grid.grid_rows.forEach(function(gr) {
		var row_locked =
			frm.doctype === "Repair Order" &&
			typeof autods_is_charge_row_locked === "function" &&
			autods_is_charge_row_locked(frm, gr.doc);
		var rowOpt = _build_service_row_opt_string(frm, gr.doc && gr.doc.service_row);
		if (gr.doc && gr.doc.name) {
			_mutate_service_row_docfield_options(child_doctype, gr.doc.name, rowOpt);
			var row_df = frappe.meta.get_docfield(child_doctype, "service_row", gr.doc.name);
			if (row_df) {
				row_df.read_only = row_locked ? 1 : 0;
				row_df.options = rowOpt || "";
			}
		}
		_mutate_df_options_in_list(gr.docfields, rowOpt);
		if (gr.docfields && gr.docfields.length) {
			gr.docfields.forEach(function(df) {
				if (df && df.fieldname === "service_row") {
					df.read_only = row_locked ? 1 : 0;
					df.options = rowOpt || "";
				}
			});
		}
		var rowType = gr.doc && (gr.doc.service_item_type || "").trim();
		if (rowType !== "Spareparts" && rowType !== "Overhead") {
			return;
		}
		_refresh_service_row_select_field(
			gr.on_grid_fields_dict && gr.on_grid_fields_dict.service_row,
			rowOpt,
			row_locked
		);
		if (gr.grid_form && gr.grid_form.fields_dict && gr.grid_form.fields_dict.service_row) {
			_refresh_service_row_select_field(
				gr.grid_form.fields_dict.service_row,
				rowOpt,
				row_locked
			);
		}
	});
}

function _refresh_service_row_select_field(fld, optString, row_locked) {
	if (!fld) {
		return;
	}
	try {
		var opts = optString || "";
		if (fld.df) {
			fld.df.options = opts;
			fld.df.read_only = row_locked ? 1 : 0;
		}
		if (fld.$wrapper && fld.$wrapper.length === 0) {
			return;
		}
		/* Rebuild <option> nodes so the open Select always shows N: item_name. */
		var $input = fld.$input;
		if ($input && $input.length && $input.is("select")) {
			var cur = fld.value || ($input.val && $input.val()) || "";
			var parts = opts.split("\n");
			/* Keep current display value even if that Service is JC-locked (filtered out of picks). */
			if (cur && parts.indexOf(cur) === -1) {
				parts.push(cur);
			}
			$input.empty();
			parts.forEach(function(opt) {
				var $o = $("<option></option>").attr("value", opt).text(opt);
				$input.append($o);
			});
			if (cur && parts.indexOf(cur) !== -1) {
				$input.val(cur);
			} else {
				$input.val(parts[0] || "");
			}
			$input.prop("disabled", !!row_locked);
		} else if (fld.set_options) {
			fld.set_options(fld.value);
		} else if (fld.refresh) {
			fld.refresh();
		}
		if (fld.$input && fld.value != null) {
			fld.$input.val(fld.value || "");
		}
		if (fld.$input && fld.$input.length) {
			fld.$input.prop("disabled", !!row_locked);
		}
	} catch (e) {
		/* Grid row may be mid-rebuild; ignore stale control refresh. */
	}
}

/** Pre-save validation mirroring server `validate_charges` / prefer-parent bind. */
autods.charges_overview.validate_charges_before_save = function(frm) {
	if (frm.doctype !== "Repair Order" && frm.doctype !== "Repair Estimate") {
		return;
	}
	var cfg = _cfg(frm);
	if (!cfg) {
		return;
	}
	var rows = frm.doc[cfg.charges] || [];
	var n_svc = 0;
	var serviceNames = _service_name_set(frm);

	rows.forEach(function(row) {
		var t = (row.service_item_type || "").trim();
		if (t === "Service") {
			n_svc += 1;
		}
	});

	rows.forEach(function(row) {
		var t = (row.service_item_type || "").trim();
		if (t !== "Spareparts" && t !== "Overhead") {
			return;
		}
		if (n_svc < 1) {
			frappe.throw(__("Add at least one Service line before Spareparts or Overhead."));
		}
		/* Prefer living parent (matches server bind_charge_service_link). */
		var parent = (row.parent_service_charge || "").trim();
		if (parent && serviceNames[parent]) {
			return;
		}
		var sr = (row.service_row || "").trim();
		if (!sr) {
			frappe.throw(__("Service is required for Spareparts and Overhead lines."));
		}
		var idx = _service_row_label_index(sr);
		if (!idx) {
			frappe.throw(__("Service must start with a number between 1 and {0}.", [Math.max(n_svc, 1)]));
		}
		if (idx < 1 || idx > n_svc) {
			frappe.throw(
				__("Service must be between 1 and {0} (Service lines in this document).", [n_svc])
			);
		}
	});
};

/**
 * When exactly one Service line exists, link empty Spareparts/Overhead rows to it.
 * Multiple Services still require a manual pick.
 */
function _autofill_single_service_link(frm, row) {
	var cfg = _cfg(frm);
	if (!cfg || !row || !row.name) {
		return;
	}
	var t = (row.service_item_type || "").trim();
	if (t !== "Spareparts" && t !== "Overhead") {
		return;
	}
	if ((row.service_row || "").trim()) {
		return;
	}
	var lines = _service_lines_with_labels(frm);
	if (lines.length !== 1) {
		return;
	}
	var only = lines[0].row;
	if (
		frm.doctype === "Repair Order" &&
		typeof autods_is_service_charge_locked === "function" &&
		autods_is_service_charge_locked(frm, only && only.name)
	) {
		return;
	}
	frappe.model.set_value(cfg.charge_child, row.name, "service_row", lines[0].label);
	frappe.model.set_value(cfg.charge_child, row.name, "parent_service_charge", lines[0].row.name || "");
}

function _autofill_all_single_service_links(frm) {
	var cfg = _cfg(frm);
	if (!cfg) {
		return;
	}
	if (_service_lines_with_labels(frm).length !== 1) {
		return;
	}
	(frm.doc[cfg.charges] || []).forEach(function(r) {
		_autofill_single_service_link(frm, r);
	});
}

/** Resolve charge child row from a focused service_row control inside the grid. */
function _charge_row_from_service_row_focus_target(frm, target) {
	var cfg = _cfg(frm);
	if (!cfg || !target) {
		return null;
	}
	var $row = $(target).closest(".grid-row");
	var gr = $row.data("grid_row");
	if (gr && gr.doc) {
		return gr.doc;
	}
	var cdn = $row.attr("data-name") || $(target).closest("[data-name]").attr("data-name");
	if (!cdn) {
		return null;
	}
	return (locals[cfg.charge_child] && locals[cfg.charge_child][cdn]) || null;
}

/** Bind once: rebuild Service options when user focuses a Spareparts/Overhead Service cell. */
function _ensure_service_row_focus_handler(frm) {
	var cfg = _cfg(frm);
	if (!cfg || !frm.fields_dict || !frm.fields_dict[cfg.charges]) {
		return;
	}
	var $wrapper = frm.fields_dict[cfg.charges].$wrapper;
	if (!$wrapper || !$wrapper.length || $wrapper.data("autods-svc-row-focus")) {
		return;
	}
	$wrapper.data("autods-svc-row-focus", 1);
	$wrapper.on("focusin.autods_svc_row", '[data-fieldname="service_row"]', function(e) {
		var row = _charge_row_from_service_row_focus_target(frm, e.target);
		if (
			frm.doctype === "Repair Order" &&
			typeof autods_is_charge_row_locked === "function" &&
			autods_is_charge_row_locked(frm, row)
		) {
			if (e.target && e.target.blur) {
				e.target.blur();
			}
			if (typeof autods_apply_locked_charge_row_editability === "function") {
				autods_apply_locked_charge_row_editability(frm);
			}
			return;
		}
		autods.charges_overview.update_service_row_select_options(frm);
	});
}

/** Dynamic Select options for charges `service_row`: "1: Item name", … (Repair Order / Estimate). */
autods.charges_overview.update_service_row_select_options = function(frm) {
	var cfg = _cfg(frm);
	if (!cfg || !frm.fields_dict || !frm.fields_dict[cfg.charges]) {
		return;
	}
	var child_doctype = cfg.charge_child;
	/* Still apply options when parent name is missing (brand-new unsaved forms). */
	var lines = _service_lines_with_labels(frm).map(function(line) {
		return line.label;
	});
	var optString = _build_service_row_opt_string(frm);
	_remap_service_row_labels(frm, optString, lines);
	_autofill_all_single_service_links(frm);
	_apply_service_row_options_to_grid(frm, child_doctype, optString);
	_ensure_service_row_focus_handler(frm);
	if (frm.doctype === "Repair Order" && typeof autods_apply_locked_charge_row_editability === "function") {
		autods_apply_locked_charge_row_editability(frm);
	}
	/* Re-apply after grid render; reload/refresh_field rebuilds rows from stale docfields. */
	setTimeout(function() {
		if (!frm.fields_dict || !frm.fields_dict[cfg.charges]) {
			return;
		}
		_apply_service_row_options_to_grid(frm, child_doctype, _build_service_row_opt_string(frm));
		if (frm.doctype === "Repair Order" && typeof autods_apply_locked_charge_row_editability === "function") {
			autods_apply_locked_charge_row_editability(frm);
		}
	}, 0);
};

function _schedule_service_row_rerender(frm, defer) {
	var run = function() {
		autods.charges_overview.update_service_row_select_options(frm);
		autods.charges_overview.schedule_render(frm);
	};
	if (defer) {
		/* after_ajax runs with repair_order/estimate refresh_field('charges'); delay
		   so options are applied after the grid finishes rebuilding. */
		frappe.after_ajax(function() {
			run();
			setTimeout(run, 100);
		});
	} else {
		run();
	}
}

function _wire_form(doctype) {
	var cfg = autods.charges_overview.CONFIG[doctype];
	if (!cfg) {
		return;
	}

	frappe.ui.form.on(doctype, {
		refresh: function(frm) {
			autods.charges_overview.update_service_row_select_options(frm);
			autods.charges_overview.schedule_render(frm);
		},
		validate: function(frm) {
			if (doctype === "Repair Order" || doctype === "Repair Estimate") {
				autods.charges_overview.validate_charges_before_save(frm);
			}
		},
	});

	var rerender = function(frm) {
		_schedule_service_row_rerender(frm, false);
	};

	function _on_charge_row_added(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row) {
			var t = (row.service_item_type || "").trim();
			if (t === "Spareparts" || t === "Overhead") {
				var n_svc = _service_rows_ordered(frm).length;
				var idx = _service_row_label_index(row.service_row);
				if (idx < 1 || idx > n_svc) {
					row.service_row = "";
					row.parent_service_charge = "";
				}
				_autofill_single_service_link(frm, row);
			}
		}
		_schedule_service_row_rerender(frm, false);
	}

	var ch_ev = {};
	ch_ev[cfg.charges + "_add"] = _on_charge_row_added;
	ch_ev[cfg.charges + "_remove"] = function(frm, cdt, cdn) {
		var removed = locals[cdt] && locals[cdt][cdn];
		if (
			doctype === "Repair Order" &&
			typeof autods_is_charge_row_locked === "function" &&
			autods_is_charge_row_locked(frm, removed)
		) {
			var jc = (frm._autods_locked_charges || {})[removed.name];
			frappe.throw(
				__("Cannot remove charge line locked by Job Card {0}.", [frappe.bold(jc)])
			);
		}
		if (
			removed &&
			(removed.service_item_type || "").trim() === "Service" &&
			removed.name &&
			(doctype === "Repair Order" || doctype === "Repair Estimate")
		) {
			_clear_orphaned_service_links(frm, removed.name);
		}
		rerender(frm);
	};
	ch_ev.item = function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		var is_service = row && (row.service_item_type || "").trim() === "Service";
		/* item_name is fetch_from item; defer until fetch completes. */
		_schedule_service_row_rerender(frm, is_service);
	};
	ch_ev.item_name = function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row && (row.service_item_type || "").trim() === "Service") {
			rerender(frm);
		}
	};
	ch_ev.service_item_type = function(frm, cdt, cdn) {
		/* repair_estimate/repair_order.js refresh_field('charges') on type change. */
		var row = locals[cdt] && locals[cdt][cdn];
		_schedule_service_row_rerender(frm, true);
		if (row) {
			frappe.after_ajax(function() {
				_autofill_single_service_link(frm, row);
			});
		}
	};
	ch_ev.form_render = function(frm) {
		autods.charges_overview.update_service_row_select_options(frm);
		_ensure_service_row_focus_handler(frm);
		if (doctype === "Repair Order" && typeof autods_apply_locked_charge_row_editability === "function") {
			autods_apply_locked_charge_row_editability(frm);
		}
	};
	ch_ev.service_row = function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row) {
			_set_parent_service_from_service_row(frm, row);
		}
		if (
			doctype === "Repair Order" &&
			row &&
			typeof autods_is_service_charge_locked === "function"
		) {
			var parent = (row.parent_service_charge || "").trim();
			var row_locked =
				typeof autods_is_charge_row_locked === "function" &&
				autods_is_charge_row_locked(frm, row);
			if (parent && autods_is_service_charge_locked(frm, parent) && !row_locked) {
				var jc = (frm._autods_locked_charges || {})[parent];
				frappe.model.set_value(cdt, cdn, "service_row", "");
				frappe.model.set_value(cdt, cdn, "parent_service_charge", "");
				frappe.msgprint({
					title: __("Charges Locked"),
					indicator: "orange",
					message: __(
						"Cannot link Spareparts or Overhead to a service locked by Job Card {0}.",
						[frappe.bold(jc)]
					),
				});
			}
		}
		_schedule_service_row_rerender(frm, false);
	};
	[
		"standard_hours",
		"qty",
		"uom",
		"rate",
		"bill_type",
		"description",
	].forEach(function(f) {
		ch_ev[f] = rerender;
	});
	frappe.ui.form.on(cfg.charge_child, ch_ev);
}

_wire_form("Repair Order");
_wire_form("Repair Estimate");
_wire_form("Service Template");
