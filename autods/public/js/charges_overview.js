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

	services.forEach(function(svc, si) {
		var ordinal = si + 1;
		var svc_parts = parts.filter(function(p) {
			return _service_row_label_index(p.service_row) === ordinal;
		});
		var svc_oh = overhead.filter(function(o) {
			return _service_row_label_index(o.service_row) === ordinal;
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
		var sr = _service_row_label_index(p.service_row);
		return !sr || sr < 1 || sr > nSvc;
	});
	var un_oh = overhead.filter(function(o) {
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

/** Dynamic Select options for charges `service_row`: "1: Item name", … (Repair Order / Estimate). */
autods.charges_overview.update_service_row_select_options = function(frm) {
	var cfg = _cfg(frm);
	if (!cfg || !frm.fields_dict || !frm.fields_dict[cfg.charges]) {
		return;
	}
	var child_doctype = cfg.charge_child;
	var table_field = cfg.charges;
	/* Child table docfield copies are keyed by PARENT doc name (see frappe/form/grid.js setup_fields). */
	var meta_dn = (frm.doc && frm.doc.name) || frm.docname;
	if (!meta_dn) {
		return;
	}
	var rows = frm.doc[table_field] || [];
	var serviceLines = [];
	rows.forEach(function(r) {
		if ((r.service_item_type || "").trim() === "Service") {
			serviceLines.push(r);
		}
	});
	var opts = serviceLines.map(function(s, si) {
		var num = si + 1;
		var nm = (s.item_name || s.item || "").trim();
		if (!nm) {
			nm = __("Service {0}", [String(num)]);
		}
		return num + ": " + nm;
	});
	var optString = opts.join("\n");
	var df = frappe.meta.get_docfield(child_doctype, "service_row", meta_dn);
	if (df) {
		df.options = optString || "";
	}
	rows.forEach(function(r) {
		if (!r.name) {
			return;
		}
		var t = (r.service_item_type || "").trim();
		if (t !== "Spareparts" && t !== "Overhead") {
			return;
		}
		if (optString && (r.service_row || "").trim()) {
			var sr = (r.service_row || "").trim();
			var lines = optString.split("\n");
			if (lines.indexOf(sr) === -1) {
				var ix = _service_row_label_index(sr);
				if (ix >= 1 && ix <= lines.length) {
					frappe.model.set_value(child_doctype, r.name, "service_row", lines[ix - 1]);
				}
			}
		}
	});
	var grid = frm.fields_dict[cfg.charges].grid;
	if (grid && grid.grid_rows && grid.grid_rows.length) {
		grid.grid_rows.forEach(function(gr) {
			var fld = gr.on_grid_fields_dict && gr.on_grid_fields_dict.service_row;
			if (fld && fld.refresh) {
				fld.refresh();
			}
			if (gr.grid_form && gr.grid_form.fields_dict && gr.grid_form.fields_dict.service_row) {
				var gff = gr.grid_form.fields_dict.service_row;
				if (gff.refresh) {
					gff.refresh();
				}
			}
		});
	}
};

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
	});

	var rerender = function(frm) {
		autods.charges_overview.update_service_row_select_options(frm);
		autods.charges_overview.schedule_render(frm);
	};

	var ch_ev = {};
	ch_ev[cfg.charges + "_add"] = rerender;
	ch_ev[cfg.charges + "_remove"] = rerender;
	[
		"service_item_type",
		"item",
		"item_name",
		"standard_hours",
		"qty",
		"uom",
		"rate",
		"bill_type",
		"service_row",
		"description",
	].forEach(function(f) {
		ch_ev[f] = rerender;
	});
	frappe.ui.form.on(cfg.charge_child, ch_ev);
}

_wire_form("Repair Order");
_wire_form("Repair Estimate");
_wire_form("Service Template");
