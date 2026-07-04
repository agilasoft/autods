// Service advisor–style dashboard for Repair Estimate, Repair Order, and Service Appointment.

(function () {
	"use strict";

	const GREEN = "#28a745";
	const AMBER = "#ffc107";
	const RED_D = "#dc3545";
	const GRAY_RING = "#868e96";
	const BLUE_BADGE = "#007bff";
	const BG_MUTED = "#F4F7F9";
	const HEADER_BG = "#ffffff";

	const ESTIMATE_STATUS_PCT = {
		Draft: 10,
		Submitted: 30,
		Approved: 55,
		Rejected: 0,
		"Converted to RO": 80,
	};

	function esc(s) {
		return frappe.utils.escape_html(s == null || s === "" ? "" : String(s));
	}

	function fmt_money(amount, currency) {
		const cur = currency || frappe.boot.sysdefaults.currency || "USD";
		try {
			return format_currency(amount || 0, cur);
		} catch (e) {
			return esc(String(amount || 0));
		}
	}

	function fmt_datetime(val) {
		if (!val) return "—";
		try {
			return frappe.datetime.str_to_user(val, true);
		} catch (e) {
			return esc(String(val));
		}
	}

	function fmt_date(val) {
		if (!val) return "—";
		try {
			return frappe.datetime.str_to_user(val);
		} catch (e) {
			return esc(String(val));
		}
	}

	function vehicle_headline(doc) {
		const parts = [
			doc.vehicle_year_model,
			doc.vehicle_make,
			doc.vehicle_model,
			doc.vehicle_variant,
			doc.vehicle_edition,
		].filter(Boolean);
		return parts.length ? parts.join(" ") : __("Vehicle");
	}

	function diagnostics_rows(doc) {
		if (doc.diagnostics && doc.diagnostics.length) return doc.diagnostics;
		return [];
	}

	function concerns_rows(doc) {
		if (doc.concerns && doc.concerns.length) return doc.concerns;
		return [];
	}

	function fetch_concern_category_map(names) {
		const uniq = [...new Set((names || []).filter(Boolean))];
		const map = {};
		return Promise.all(
			uniq.map(
				(n) =>
					new Promise((resolve) => {
						frappe.db.get_value(
							"Concern Category",
							n,
							["code", "description", "service_type", "icon"],
							(msg) => {
								if (msg) map[n] = msg;
								resolve();
							}
						);
					})
			)
		).then(() => map);
	}

	function fetch_repair_concern_map(names) {
		const uniq = [...new Set((names || []).filter(Boolean))];
		const map = {};
		return Promise.all(
			uniq.map(
				(n) =>
					new Promise((resolve) => {
						frappe.db.get_value(
							"Repair Concern",
							n,
							["code", "description", "icon"],
							(msg) => {
								if (msg) map[n] = msg;
								resolve();
							}
						);
					})
			)
		).then(() => map);
	}

	function fetch_repair_diagnostic_map(names) {
		const uniq = [...new Set((names || []).filter(Boolean))];
		const map = {};
		return Promise.all(
			uniq.map(
				(n) =>
					new Promise((resolve) => {
						frappe.db.get_value(
							"Repair Diagnostic",
							n,
							["code", "description"],
							(msg) => {
								if (msg) map[n] = msg;
								resolve();
							}
						);
					})
			)
		).then(() => map);
	}

	/**
	 * Rows from the parent document's `diagnostics` child table (Repair Estimate Diagnostics).
	 * All table rows with the same Repair Concern link (`concern`) belong to that concern
	 * (multiple diagnostics per concern). Order is the table order (idx / array order).
	 */
	function diagnostics_for_concern_row(row, allDiag) {
		const rC = String(row.concern || "").trim();
		const rCC = String(row.customer_concern || "").trim();
		return (allDiag || []).filter((d) => {
			const dC = String(d.concern || "").trim();
			const dCC = String(d.customer_concern || "").trim();
			if (rC && dC) {
				return rC === dC;
			}
			if (rC && !dC) {
				return !!(rCC && dCC && rCC === dCC);
			}
			if (!rC && dC) {
				return !!(rCC && dCC && rCC === dCC);
			}
			return !!(rCC && dCC && rCC === dCC);
		});
	}

	function render_concern_diagnostics_from_table(diags, diagMap) {
		if (!diags.length) {
			return `<p class="autods-sa-muted">${esc(
				__(
					"No rows in the Diagnostics table share this concern code. Add rows under Diagnostics on the estimate."
				)
			)}</p>`;
		}
		const dmap = diagMap || {};
		const body = diags
			.map((d, i) => {
				const linkName = String(d.diagnostic || "").trim();
				const meta = linkName && dmap[linkName] ? dmap[linkName] : null;
				const code =
					(meta && meta.code) || linkName || "—";
				const desc =
					(meta && meta.description) ||
					"—";
				const idx =
					d.idx != null && d.idx !== "" ?
						String(d.idx)
					:	String(i + 1);
				const notes = d.notes ? String(d.notes) : "—";
				return `<tr>
					<td class="autods-sa-cc-diag-td-idx">${esc(idx)}</td>
					<td>${esc(code)}</td>
					<td>${esc(desc)}</td>
					<td class="autods-sa-cc-diag-td-notes">${esc(notes)}</td>
				</tr>`;
			})
			.join("");
		return `<div class="autods-sa-cc-diag-table-wrap">
			<table class="autods-sa-cc-diag-table">
				<thead><tr>
					<th scope="col">${esc(__("#"))}</th>
					<th scope="col">${esc(__("Diagnostic"))}</th>
					<th scope="col">${esc(__("Description"))}</th>
					<th scope="col">${esc(__("Notes"))}</th>
				</tr></thead>
				<tbody>${body}</tbody>
			</table>
		</div>`;
	}

	function render_estimate_concerns_cards(
		concerns,
		diagnostics,
		catMap,
		concernMap,
		diagMap
	) {
		if (!concerns.length) {
			return `<p class="autods-sa-muted">${esc(
				__(
					"No concerns captured yet. Add rows under Concerns on this estimate."
				)
			)}</p>`;
		}
		const cmap = concernMap || {};
		const cards = concerns
			.map((row, rowIndex) => {
				const cat =
					row.concern_category && catMap[row.concern_category] ?
						catMap[row.concern_category]
					:	null;
				const rc =
					row.concern && cmap[row.concern] ? cmap[row.concern] : null;
				const codePart =
					(rc && rc.code && String(rc.code).trim()) ||
					(row.concern && String(row.concern).trim()) ||
					(cat && cat.code && String(cat.code).trim()) ||
					"";
				const descPart =
					(row.description && String(row.description).trim()) ||
					(rc && rc.description && String(rc.description).trim()) ||
					(cat && cat.description && String(cat.description).trim()) ||
					"";
				let concernCodeAndDesc = "";
				if (codePart && descPart) {
					concernCodeAndDesc = `${codePart} — ${descPart}`;
				} else {
					concernCodeAndDesc = codePart || descPart || __("Concern");
				}
				const customerConcern =
					row.customer_concern && String(row.customer_concern).trim() ?
						String(row.customer_concern).trim()
					:	"";
				const diags = diagnostics_for_concern_row(row, diagnostics);
				const diagInner = render_concern_diagnostics_from_table(
					diags,
					diagMap
				);
				const rowIdx =
					row.idx != null && row.idx !== "" ?
						String(row.idx)
					:	String(rowIndex + 1);
				const diagNames = diags
					.map((d) => String(d.diagnostic || "").trim())
					.filter(Boolean);
				let metaLine = "";
				if (diagNames.length) {
					const maxParts = 3;
					const shown = diagNames.slice(0, maxParts).join(" · ");
					const tail =
						diagNames.length > maxParts ? " …" : "";
					metaLine = `${__("{0} diagnostics", [
						String(diags.length),
					])}: ${shown}${tail}`;
				} else {
					const hintParts = [];
					if (cat && cat.code) hintParts.push(cat.code);
					if (row.concern) hintParts.push(row.concern);
					metaLine =
						hintParts.length ?
							`${__(
								"Link diagnostics to this concern code."
							)} ${hintParts.join(" · ")}`
						:	__(
								"Add diagnostics on the estimate linked to this concern."
							);
				}
				const notesBlock =
					row.notes ?
						`<div class="autods-sa-cc-notes"><span class="autods-sa-cc-notes-label">${esc(
							__("Notes")
						)}</span><p>${esc(row.notes)}</p></div>`
					:	"";
				return `<details class="autods-sa-cc-card">
					<summary class="autods-sa-cc-summary">
						<span class="autods-sa-cc-index" title="${esc(
							__("Concern row {0}", [rowIdx])
						)}" aria-label="${esc(__("Concern row {0}", [rowIdx]))}">${esc(
							rowIdx
						)}</span>
						<span class="autods-sa-cc-summary-text">
							<span class="autods-sa-cc-field">
								<span class="autods-sa-cc-field-label">${esc(
									__("Concern Code and Description")
								)}</span>
								<span class="autods-sa-cc-title">${esc(
									concernCodeAndDesc
								)}</span>
							</span>
							<span class="autods-sa-cc-field autods-sa-cc-field--customer">
								<span class="autods-sa-cc-field-label">${esc(
									__("Customer Concern")
								)}</span>
								<span class="autods-sa-cc-customer">${esc(
									customerConcern || "—"
								)}</span>
							</span>
							<span class="autods-sa-cc-subrow">
								<span class="autods-sa-cc-meta">${esc(metaLine)}</span>
							</span>
						</span>
						<span class="autods-sa-cc-chev" aria-hidden="true"></span>
					</summary>
					<div class="autods-sa-cc-body">
						${notesBlock}
						<div class="autods-sa-cc-diag-section">
							<div class="autods-sa-cc-diag-section-head">
								<span class="autods-sa-cc-diag-section-title">${esc(
									__("Diagnostics (table)")
								)}</span>
								<span class="autods-sa-cc-diag-section-count">${esc(
									String(diags.length)
								)}</span>
							</div>
							<div class="autods-sa-cc-diag-inner">${diagInner}</div>
						</div>
					</div>
				</details>`;
			})
			.join("");
		return `<div class="autods-sa-cc-wrap">
			<div class="autods-sa-cc-stack">${cards}</div>
			<p class="autods-sa-cc-actions">
				<button type="button" class="autods-sa-insp-edit-btn" data-autods-focus-field="concerns">${esc(
					__("Edit concerns & diagnostics")
				)}</button>
			</p>
		</div>`;
	}

	function count_inspection_rows(doc) {
		if (
			doc.doctype === "Repair Order" ||
			doc.doctype === "Repair Estimate"
		) {
			return (doc.quality_inspections || []).length;
		}
		return 0;
	}

	function render_service_inspection_items_table(items) {
		if (!items.length) {
			return `<p class="autods-sa-muted autods-sa-insp-empty">${esc(
				__("No lines on this Service Inspection yet.")
			)}</p>`;
		}
		const body = items
			.map((it) => {
				const line =
					[it.item_code, it.item_name].filter(Boolean).join(" — ") || "—";
				return `<tr>
				<td>${esc(line)}</td>
				<td>${esc(it.specification || "—")}</td>
				<td>${esc(it.expected_value || "—")}</td>
				<td>${esc(it.actual_value || "—")}</td>
				<td>${esc(it.result || "—")}</td>
				<td class="autods-sa-insp-notes">${esc(it.remarks || "—")}</td>
			</tr>`;
			})
			.join("");
		return `<div class="autods-sa-insp-table-wrap">
			<table class="autods-sa-insp-table">
				<thead><tr>
					<th>${esc(__("Item"))}</th>
					<th>${esc(__("Spec"))}</th>
					<th>${esc(__("Expected"))}</th>
					<th>${esc(__("Actual"))}</th>
					<th>${esc(__("Result"))}</th>
					<th>${esc(__("Remarks"))}</th>
				</tr></thead>
				<tbody>${body}</tbody>
			</table>
		</div>`;
	}

	function render_checklist_row_card(row, item_field) {
		const label = row[item_field] || "—";
		const pres = row.present ? __("Yes") : __("No");
		const field_label =
			item_field === "item" ? __("Item") : __("Inspection item");
		return `<div class="autods-sa-insp-row-card">
			<div class="autods-sa-insp-row-card-header">
				<span class="autods-sa-insp-row-title">${esc(label)}</span>
				<span class="autods-sa-insp-row-meta">${esc(pres)} · ${esc(
			row.condition || "—"
		)}</span>
			</div>
			<details class="autods-sa-insp-nested">
				<summary class="autods-sa-insp-nested-summary">${esc(
					__("Line details")
				)}</summary>
				<div class="autods-sa-insp-nested-body">
					<div class="autods-sa-insp-kv-mini">
						<div><span>${esc(field_label)}</span><strong>${esc(
			String(label)
		)}</strong></div>
						<div><span>${esc(__("Present"))}</span><strong>${esc(
			pres
		)}</strong></div>
						<div><span>${esc(__("Condition"))}</span><strong>${esc(
			row.condition || "—"
		)}</strong></div>
						<div class="autods-sa-insp-kv-mini--wide"><span>${esc(
							__("Notes")
						)}</span><strong>${esc(row.notes || "—")}</strong></div>
					</div>
				</div>
			</details>
		</div>`;
	}

	function render_checklist_row_cards(rows, item_field) {
		if (!rows.length) {
			return `<p class="autods-sa-muted autods-sa-insp-empty">${esc(
				__("No checklist lines yet.")
			)}</p>`;
		}
		return `<div class="autods-sa-insp-row-stack">${rows
			.map((row) => render_checklist_row_card(row, item_field))
			.join("")}</div>`;
	}

	function render_quality_row_card(row, si_doc) {
		const si_name = row.quality_inspection;
		const items = (si_doc && si_doc.inspection_items) || [];
		let si_href = "";
		if (si_name) {
			si_href = frappe.utils.get_form_link("Service Inspection", si_name);
		}
		const open_si =
			si_href ?
				`<a class="autods-sa-insp-si-link" href="${attr_url(si_href)}">${esc(
					__("Open Service Inspection")
				)}</a>`
			:	"";

		const si_id_line =
			si_name ?
				`<div class="autods-sa-insp-row-si-id">${esc(
					__("Service Inspection")
				)}: <strong>${esc(si_name)}</strong></div>`
			:	`<div class="autods-sa-insp-row-si-id autods-sa-muted">${esc(
					__("No Service Inspection linked.")
				)}</div>`;

		const meta_line = `${esc(row.status || "—")} · ${esc(
			fmt_date(row.inspection_date)
		)} · ${esc(row.inspected_by || "—")}`;

		let items_block = "";
		if (si_name) {
			if (!si_doc) {
				items_block = `<details class="autods-sa-insp-nested">
					<summary class="autods-sa-insp-nested-summary">${esc(
						__("Inspection items")
					)}</summary>
					<div class="autods-sa-insp-nested-body">
						<p class="autods-sa-muted autods-sa-insp-empty">${esc(
							__(
								"Could not load this Service Inspection. Open it from the link above."
							)
						)}</p>
					</div>
				</details>`;
			} else if (items.length) {
				items_block = `<details class="autods-sa-insp-nested">
					<summary class="autods-sa-insp-nested-summary">${esc(
						__("Inspection items")
					)} (${esc(String(items.length))})</summary>
					<div class="autods-sa-insp-nested-body">
						${render_service_inspection_items_table(items)}
					</div>
				</details>`;
			} else {
				items_block = `<details class="autods-sa-insp-nested">
					<summary class="autods-sa-insp-nested-summary">${esc(
						__("Inspection items")
					)}</summary>
					<div class="autods-sa-insp-nested-body">
						<p class="autods-sa-muted autods-sa-insp-empty">${esc(
							__("No checklist lines on this Service Inspection yet.")
						)}</p>
					</div>
				</details>`;
			}
		}

		return `<div class="autods-sa-insp-row-card">
			<div class="autods-sa-insp-row-card-header autods-sa-insp-row-card-header--quality">
				<div class="autods-sa-insp-row-quality-top">
					<span class="autods-sa-insp-row-title">${esc(
						row.inspection_name || "—"
					)}</span>
					${open_si}
				</div>
				<div class="autods-sa-insp-row-meta">${meta_line}</div>
				${si_id_line}
			</div>
			${
				row.remarks ?
					`<details class="autods-sa-insp-nested">
				<summary class="autods-sa-insp-nested-summary">${esc(
					__("Remarks")
				)}</summary>
				<div class="autods-sa-insp-nested-body"><p class="autods-sa-insp-remarks">${esc(
					row.remarks
				)}</p></div>
			</details>`
				:	""
			}
			${items_block}
		</div>`;
	}

	function render_quality_row_cards(rows, si_map) {
		if (!rows.length) {
			return `<p class="autods-sa-muted autods-sa-insp-empty">${esc(
				__("No service inspections yet.")
			)}</p>`;
		}
		return `<div class="autods-sa-insp-row-stack">${rows
			.map((row) =>
				render_quality_row_card(
					row,
					row.quality_inspection ? si_map.get(row.quality_inspection) : null
				)
			)
			.join("")}</div>`;
	}

	function render_inspection_section_block(section, si_map) {
		const n = section.rows.length;
		const field_attr = esc(section.field);
		const body =
			section.kind === "quality" ?
				render_quality_row_cards(section.rows, si_map)
			:	render_checklist_row_cards(section.rows, section.item_field);
		return `<div class="autods-sa-insp-section">
			<div class="autods-sa-insp-section-head">
				<div class="autods-sa-insp-section-head-text">
					<h4 class="autods-sa-insp-section-title">${esc(section.title)}</h4>
					${
						n > 0 ?
							`<span class="autods-sa-insp-count">${esc(String(n))}</span>`
						:	""
					}
				</div>
				<button type="button" class="autods-sa-insp-edit-btn" data-autods-focus-field="${field_attr}">${esc(
			__("Update checklist")
		)}</button>
			</div>
			${body}
		</div>`;
	}

	async function fetch_service_inspection_map(names) {
		const map = new Map();
		const uniq = [...new Set((names || []).filter(Boolean))];
		await Promise.all(
			uniq.map(async (n) => {
				try {
					const doc = await frappe.db.get_doc("Service Inspection", n);
					map.set(n, doc);
				} catch (e) {
					map.set(n, null);
				}
			})
		);
		return map;
	}

	function inspection_sections(doc) {
		if (
			doc.doctype === "Repair Order" ||
			doc.doctype === "Repair Estimate"
		) {
			return [
				{
					key: "qual",
					title: __("Quality / Service Inspections"),
					field: "quality_inspections",
					rows: doc.quality_inspections || [],
					kind: "quality",
				},
			];
		}
		return [];
	}

	async function render_inspections_panel(doc) {
		const sections = inspection_sections(doc);
		if (!sections.length) {
			return `<p class="autods-sa-muted">${esc(
				__("Inspections are not available on this document type.")
			)}</p>`;
		}
		const si_names = [];
		for (const s of sections) {
			if (s.kind !== "quality") continue;
			for (const r of s.rows || []) {
				if (r.quality_inspection) si_names.push(r.quality_inspection);
			}
		}
		const si_map = await fetch_service_inspection_map(si_names);
		return `<div class="autods-sa-insp-stack">${sections
			.map((s) => render_inspection_section_block(s, si_map))
			.join("")}</div>`;
	}

	/**
	 * Build a browser-ready image URL (Attach Image paths, private files, subpath sites).
	 * Mirrors patterns from frappe/form/sidebar/attachments.js.
	 */
	function file_to_img_src(file_url) {
		if (!file_url) return "";
		let u = String(file_url).trim();
		if (frappe.utils.is_url(u)) {
			return encodeURI(u).replace(/#/g, "%23");
		}
		u = frappe.utils.get_file_link(u);
		if (!frappe.utils.is_url(u)) {
			if (u.indexOf("/") !== 0) {
				u = "/" + u;
			}
			if (frappe.urllib && frappe.urllib.get_full_url) {
				u = frappe.urllib.get_full_url(u);
			}
		}
		return encodeURI(u).replace(/#/g, "%23");
	}

	/** Safe for HTML attribute href/src. */
	function attr_url(u) {
		if (!u) return "";
		return String(u).replace(/"/g, "%22").replace(/</g, "%3C").replace(/`/g, "%60");
	}

	/**
	 * frappe.db.get_value passes the unwrapped message dict to the callback (not r.message).
	 */
	function fetch_vehicle_unit_header_fields(vehicle_unit) {
		return new Promise((resolve) => {
			if (!vehicle_unit) {
				resolve({ image: null, description: "" });
				return;
			}
			frappe.db.get_value(
				"Vehicle Unit",
				vehicle_unit,
				["image", "description"],
				(msg) => {
					resolve({
						image: msg && msg.image ? msg.image : null,
						description:
							msg && msg.description ?
								String(msg.description).trim()
							:	"",
					});
				}
			);
		});
	}

	function db_get_value_fields(doctype, name, fieldnames) {
		return new Promise((resolve) => {
			if (!name) {
				resolve(null);
				return;
			}
			frappe.db.get_value(doctype, name, fieldnames, (msg) => {
				resolve(msg || null);
			});
		});
	}

	function format_linked_type_display(msg, fallbackName) {
		if (!fallbackName) return "";
		if (!msg) return String(fallbackName);
		const desc = msg.description != null ? String(msg.description).trim() : "";
		const code = msg.code != null ? String(msg.code).trim() : "";
		if (desc) return desc;
		if (code) return code;
		return String(fallbackName);
	}

	async function fetch_dashboard_header_link_labels(doc) {
		const customer = doc.customer;
		const st = doc.service_type;
		const rt = doc.repair_type;
		const [custMsg, stMsg, rtMsg] = await Promise.all([
			customer ?
				db_get_value_fields("Customer", customer, "customer_name")
			:	Promise.resolve(null),
			st ?
				db_get_value_fields("Service Type", st, ["code", "description"])
			:	Promise.resolve(null),
			rt ?
				db_get_value_fields("Repair Type", rt, ["code", "description"])
			:	Promise.resolve(null),
		]);
		return {
			customer_display:
				custMsg && custMsg.customer_name ?
					String(custMsg.customer_name).trim()
				:	customer || "",
			service_type_display: format_linked_type_display(stMsg, st),
			repair_type_display: format_linked_type_display(rtMsg, rt),
		};
	}

	function fmt_appointment_time_only(sa) {
		if (!sa) return "";
		const s = sa.appointment_start_time || "";
		const e = sa.appointment_end_time || "";
		return [s, e].filter(Boolean).join(" – ");
	}

	/** faIcon: Font Awesome 4 glyph only, e.g. "fa-user" → class "fa fa-user". */
	function render_dashboard_header_meta(rows) {
		const cells = rows
			.map(([faIcon, title, value]) => {
				const v =
					value != null && String(value).trim() !== "" ?
						String(value)
					:	"—";
				return `<div class="autods-sa-meta-line" title="${esc(title)}">
					<i class="fa ${faIcon} autods-sa-meta-icon" aria-hidden="true"></i>
					<span class="autods-sa-meta-value"><span class="sr-only">${esc(
						title
					)}: </span>${esc(v)}</span>
				</div>`;
			})
			.join("");
		return `<div class="autods-sa-meta-grid">${cells}</div>`;
	}

	function repair_order_name_for_job_cards(doc) {
		if (doc.doctype === "Repair Order") return doc.name || null;
		if (doc.doctype === "Repair Estimate" && doc.repair_order) {
			return doc.repair_order;
		}
		if (doc.doctype === "Service Appointment" && doc.repair_order) {
			const ro = String(doc.repair_order).trim();
			return ro || null;
		}
		return null;
	}

	async function fetch_vehicle_unit_for_dashboard(vehicle_unit) {
		if (!vehicle_unit) return null;
		try {
			return await frappe.db.get_doc("Vehicle Unit", vehicle_unit);
		} catch (e) {
			return null;
		}
	}

	function vehicle_headline_from_vu(vu) {
		if (!vu) return __("Vehicle");
		const pseudo = {
			vehicle_year_model: vu.year_model,
			vehicle_make: vu.make,
			vehicle_model: vu.model,
			vehicle_variant: vu.variant,
			vehicle_edition: "",
		};
		const h = vehicle_headline(pseudo);
		return h && String(h).trim() ? h : __("Vehicle");
	}

	async function fetch_job_cards_full(repair_order) {
		if (!repair_order) return [];
		const list = await frappe.db.get_list("Job Card", {
			filters: { repair_order },
			fields: ["name", "repair_order"],
			order_by: "modified desc",
			limit: 25,
		});
		if (!list.length) return [];
		const docs = await Promise.all(list.map((row) => frappe.db.get_doc("Job Card", row.name)));
		const ro = String(repair_order);
		return docs.filter((jc) => String(jc.repair_order || "") === ro);
	}

	async function fetch_service_appointment_doc(name) {
		if (!name) return null;
		try {
			return await frappe.db.get_doc("Service Appointment", name);
		} catch (e) {
			return null;
		}
	}

	async function fetch_employees_map(technician_ids) {
		const ids = [...new Set((technician_ids || []).filter(Boolean))];
		if (!ids.length) return {};
		const rows = await Promise.all(
			ids.map(
				(id) =>
					new Promise((resolve) => {
						frappe.db.get_value(
							"Employee",
							id,
							["image", "employee_name", "date_of_joining", "designation"],
							(msg) => resolve({ id, msg: msg || {} })
						);
					})
			)
		);
		const out = {};
		rows.forEach(({ id, msg }) => {
			out[id] = {
				image: msg.image || "",
				employee_name: msg.employee_name || id,
				date_of_joining: msg.date_of_joining || "",
				designation: msg.designation || "",
			};
		});
		return out;
	}

	function years_of_service(doj) {
		if (!doj) return null;
		try {
			const days = frappe.datetime.get_diff(frappe.datetime.get_today(), doj);
			if (days <= 0) return null;
			return Math.floor(days / 365.25);
		} catch (e) {
			return null;
		}
	}

	function employee_subline(emp) {
		const y = years_of_service(emp.date_of_joining);
		if (y != null && y > 0) {
			return __("{0} years of experience", [String(y)]);
		}
		if (emp.designation) return emp.designation;
		return "";
	}

	function fmt_datetime_long(val) {
		if (!val) return "—";
		if (window.moment) {
			try {
				return moment(val).format("dddd, MMMM D, YYYY – LT");
			} catch (e) {
				/* fall through */
			}
		}
		return fmt_datetime(val);
	}

	function format_ro_datetime_long(val, fallbackDate) {
		if (!val) return fmt_date(fallbackDate);
		if (
			window.autods &&
			autods.service_datetime &&
			typeof autods.service_datetime.format_system_datetime_long === "function"
		) {
			try {
				return autods.service_datetime.format_system_datetime_long(val);
			} catch (e) {
				console.warn("autods dashboard: format repair order datetime", e);
			}
		}
		return fmt_datetime(val) || fmt_date(fallbackDate);
	}

	function jc_work_completion_pct(jc) {
		const rows = jc.work_details || [];
		if (!rows.length) return jc_progress_pct(jc.status);
		const done = rows.filter((r) => r.status === "Completed").length;
		return Math.round((done / rows.length) * 100);
	}

	function donut_svg_avatar_ring(pct, strokeColor) {
		const r = 38;
		const c = 2 * Math.PI * r;
		const p = Math.min(100, Math.max(0, pct)) / 100;
		const dash = p * c;
		return `<svg class="autods-sa-jc-av-svg" width="80" height="80" viewBox="0 0 100 100" aria-hidden="true">
			<g transform="translate(50,50)">
				<circle r="${r}" fill="none" stroke="#e9ecef" stroke-width="6" />
				<circle r="${r}" fill="none" stroke="${strokeColor}" stroke-width="6"
					stroke-dasharray="${dash} ${c}"
					stroke-linecap="round"
					transform="rotate(-90)" />
			</g>
		</svg>`;
	}

	function render_mechanic_avatar(emp, jc_pct) {
		const ringColor = donut_color(jc_pct);
		const imgSrc =
			emp && emp.image ? file_to_img_src(emp.image) : "";
		const initial = esc(
			(emp && emp.employee_name ? emp.employee_name : "?").charAt(0).toUpperCase()
		);
		const photo = imgSrc
			? `<img src="${attr_url(imgSrc)}" alt="" />`
			: `<span class="autods-sa-jc-av-placeholder">${initial}</span>`;
		return `<div class="autods-sa-jc-avatar-ringbox">
			${donut_svg_avatar_ring(jc_pct, ringColor)}
			<div class="autods-sa-jc-avatar-photo">
				${photo}
				<span class="autods-sa-jc-avatar-pct">${esc(String(jc_pct))}%</span>
			</div>
		</div>`;
	}

	function fmt_appointment_time_window(sa) {
		if (!sa) return "—";
		const d = sa.appointment_date ? fmt_date(sa.appointment_date) : "";
		const s = sa.appointment_start_time || "";
		const e = sa.appointment_end_time || "";
		const t = [s, e].filter(Boolean).join(" – ");
		if (d && t) return `${d} · ${t}`;
		if (d) return d;
		return t || "—";
	}

	function render_appointment_panel(sa, emp_map) {
		if (!sa) {
			return `<p class="autods-sa-muted">${esc(
				__(
					"No Service Appointment is linked to this document. Link one on the form to see schedule details here."
				)
			)}</p>`;
		}
		const adv_raw =
			sa.service_advisor && emp_map[sa.service_advisor]
				? emp_map[sa.service_advisor].employee_name || sa.service_advisor
				: sa.service_advisor || __("—");
		const sa_route = frappe.utils.get_form_link("Service Appointment", sa.name);
		const rows = [
			[__("Appointment"), sa.name],
			[__("Status"), sa.status || "—"],
			[__("Date & time"), fmt_appointment_time_window(sa)],
			[__("Service advisor"), adv_raw],
			[__("Subject"), sa.subject || "—"],
			[__("Customer"), sa.customer || "—"],
			[__("Plate"), sa.plate_no || "—"],
			[__("Vehicle ID"), sa.vehicle_id_no || "—"],
			[__("Service type"), sa.service_type || "—"],
			[__("Repair type"), sa.repair_type || "—"],
		];
		const grid = rows
			.map(
				([k, v]) =>
					`<div class="autods-sa-kv"><span>${esc(k)}</span><strong>${esc(
						String(v)
					)}</strong></div>`
			)
			.join("");
		return `<div class="autods-sa-appt-card">
			<div class="autods-sa-kv-grid">${grid}</div>
			<p><a class="autods-sa-text-link" href="${attr_url(sa_route)}">${esc(
			__("Open Service Appointment")
		)}</a></p>
		</div>`;
	}

	function render_service_appointment_detail_panel(sa, emp_map) {
		if (!sa || sa.__islocal) {
			return `<p class="autods-sa-muted">${esc(
				__("Save this document to see appointment details on the dashboard.")
			)}</p>`;
		}
		const adv_raw =
			sa.service_advisor && emp_map[sa.service_advisor]
				? emp_map[sa.service_advisor].employee_name || sa.service_advisor
				: sa.service_advisor || __("—");
		const rows = [
			[__("Appointment"), sa.name],
			[__("Status"), sa.status || "—"],
			[__("Date & time"), fmt_appointment_time_window(sa)],
			[__("Service advisor"), adv_raw],
			[__("Subject / description"), sa.subject || "—"],
			[__("Customer"), sa.customer || "—"],
			[__("Contact person"), sa.contact_person || "—"],
			[__("Contact mobile"), sa.contact_mobile || "—"],
			[__("Plate"), sa.plate_no || "—"],
			[__("Vehicle ID"), sa.vehicle_id_no || "—"],
			[__("Service type"), sa.service_type || "—"],
			[__("Repair type"), sa.repair_type || "—"],
		];
		if (sa.notes) {
			rows.push([__("Notes"), String(sa.notes)]);
		}
		if (
			String(sa.status || "").trim() === "Cancelled" &&
			sa.cancellation_reason
		) {
			rows.push([__("Cancellation reason"), String(sa.cancellation_reason)]);
		}
		const grid = rows
			.map(
				([k, v]) =>
					`<div class="autods-sa-kv"><span>${esc(k)}</span><strong>${esc(
						String(v)
					)}</strong></div>`
			)
			.join("");
		const linkBits = [];
		if (sa.repair_estimate) {
			const href = frappe.utils.get_form_link(
				"Repair Estimate",
				sa.repair_estimate
			);
			linkBits.push(
				`<a class="autods-sa-insp-edit-btn" href="${attr_url(href)}">${esc(
					__("Open Repair Estimate")
				)}</a>`
			);
		}
		if (sa.repair_order) {
			const href = frappe.utils.get_form_link("Repair Order", sa.repair_order);
			linkBits.push(
				`<a class="autods-sa-insp-edit-btn" href="${attr_url(href)}">${esc(
					__("Open Repair Order")
				)}</a>`
			);
		}
		const linksRow =
			linkBits.length ?
				`<p class="autods-sa-appt-actions">${linkBits.join("")}</p>`
			:	`<p class="autods-sa-muted">${esc(
					__("No repair estimate or repair order linked yet.")
				)}</p>`;
		return `<div class="autods-sa-appt-card autods-sa-appt-card--primary">
			<div class="autods-sa-kv-grid">${grid}</div>
			${linksRow}
		</div>`;
	}

	function render_job_card_panel(jc, emp_map) {
		const emp = jc.technician && emp_map[jc.technician] ? emp_map[jc.technician] : {};
		const tech_name = jc.technician
			? esc(emp.employee_name || jc.technician)
			: esc(__("Unassigned"));
		const sub = employee_subline(emp);
		const jc_pct = jc_work_completion_pct(jc);
		const wd = jc.work_details || [];
		const n = wd.length;
		const primary =
			n && wd[0].work_description
				? wd[0].work_description
				: __("Service work");
		const jc_route = frappe.utils.get_form_link("Job Card", jc.name);
		const menu_href = attr_url(jc_route);
		const exp_comp = jc.expected_completion_date
			? fmt_datetime_long(jc.expected_completion_date)
			: "—";
		const act_comp = jc.actual_completion_date
			? fmt_datetime_long(jc.actual_completion_date)
			: "";
		const completion_line =
			jc.status === "Completed" && act_comp
				? `${esc(exp_comp)} (${esc(__("Actual"))}: ${esc(act_comp)})`
				: esc(exp_comp);

		return `<article class="autods-sa-jc-panel">
			<div class="autods-sa-jc-mechanic">
				<div class="autods-sa-jc-mechanic-label">${esc(__("Technician"))}</div>
				${render_mechanic_avatar(
					jc.technician ? emp : {},
					jc_pct
				)}
				<div class="autods-sa-jc-mechanic-name">${tech_name}</div>
				${
					sub
						? `<div class="autods-sa-jc-mechanic-sub">${esc(sub)}</div>`
						: ""
				}
			</div>
			<div class="autods-sa-jc-main">
				<div class="autods-sa-jc-headrow">
					<div class="autods-sa-jc-headcell">
						<span class="autods-sa-jc-hl">${esc(__("Job card"))}</span>
						<strong>${esc(jc.name)}</strong>
					</div>
					<div class="autods-sa-jc-headcell">
						<span class="autods-sa-jc-hl">${esc(__("Status"))}</span>
						<strong>${esc(jc.status || "—")}</strong>
					</div>
					<div class="autods-sa-jc-headcell">
						<span class="autods-sa-jc-hl">${esc(__("Expected completion"))}</span>
						<strong>${completion_line}</strong>
					</div>
					<div class="autods-sa-jc-headcell">
						<span class="autods-sa-jc-hl">${esc(__("Work area"))}</span>
						<strong>${esc(jc.work_area || "—")}</strong>
					</div>
					<a class="autods-sa-jc-menu" href="${menu_href}" title="${esc(
			__("Open job card")
		)}">⋯</a>
				</div>
				<div class="autods-sa-jc-body">
					<div class="autods-sa-jc-services-label">${esc(__("Your services"))} (${esc(
						String(n)
					)})</div>
					<div class="autods-sa-jc-service-title">${esc(primary)}</div>
					${
						n > 1
							? `<div class="autods-sa-jc-service-more">${wd
									.slice(1, 5)
									.map((w) => esc(w.work_description || "—"))
									.join(" · ")}${
									n > 5
										? " · " +
										  esc(
												String(n - 5) + " " + __("more")
										  )
										: ""
							  }</div>`
							: ""
					}
					<a class="autods-sa-jc-view" href="${menu_href}">${esc(
			__("View details")
		)}</a>
				</div>
			</div>
		</article>`;
	}

	function render_job_cards_deck(job_cards, emp_map, ctx) {
		const estimate_no_ro =
			ctx &&
			ctx.context_doctype === "Repair Estimate" &&
			!ctx.repair_order_name;
		if (estimate_no_ro) {
			return `<p class="autods-sa-muted">${esc(
				__(
					"A Repair Order has not been created from this estimate yet. Job cards are added on the Repair Order and only appear here after you convert the estimate or link an order."
				)
			)}</p>`;
		}
		const sa_no_ro =
			ctx &&
			ctx.context_doctype === "Service Appointment" &&
			!ctx.repair_order_name;
		if (sa_no_ro) {
			return `<p class="autods-sa-muted">${esc(
				__(
					"No Repair Order is linked yet. Create or link a Repair Order to see job cards for this appointment."
				)
			)}</p>`;
		}
		if (!job_cards.length) {
			return `<p class="autods-sa-muted">${esc(
				__(
					"No job cards are linked to this repair order yet. Use Create → Job cards… on the Repair Order, Service Appointment, or Repair Estimate."
				)
			)}</p>`;
		}
		return `<div class="autods-sa-jc-deck">${job_cards
			.map((jc) => render_job_card_panel(jc, emp_map))
			.join("")}</div>`;
	}

	function fetch_repair_orders_for_vehicle(vehicle_unit) {
		if (!vehicle_unit) return Promise.resolve([]);
		return frappe.db.get_list("Repair Order", {
			filters: { vehicle_unit },
			fields: [
				"name",
				"repair_date",
				"expected_completion_date",
				"grand_total",
				"customer",
				"docstatus",
				"service_advisor",
				"service_description",
			],
			order_by: "repair_date desc, modified desc",
			limit: 100,
		});
	}

	async function safe_fetch_repair_orders_for_vehicle(vehicle_unit) {
		try {
			return await fetch_repair_orders_for_vehicle(vehicle_unit);
		} catch (e) {
			console.warn("autods dashboard: repair order history", e);
			return [];
		}
	}

	async function safe_fetch_job_cards_full(repair_order) {
		try {
			return await fetch_job_cards_full(repair_order);
		} catch (e) {
			console.warn("autods dashboard: job cards", e);
			return [];
		}
	}

	function ro_docstatus_label(ds) {
		if (ds === 0) return __("Draft");
		if (ds === 1) return __("Submitted");
		if (ds === 2) return __("Cancelled");
		return __("Unknown");
	}

	function ro_docstatus_completion_pct(docstatus) {
		if (docstatus === 1) return 100;
		if (docstatus === 2) return 0;
		if (docstatus === 0) return 40;
		return 25;
	}

	function render_repair_order_panel(
		ro,
		emp_map,
		vehicle_headline,
		context_doc,
		currency
	) {
		const emp =
			ro.service_advisor && emp_map[ro.service_advisor]
				? emp_map[ro.service_advisor]
				: {};
		const advisor_name = ro.service_advisor
			? esc(emp.employee_name || ro.service_advisor)
			: esc(__("Unassigned"));
		const sub = employee_subline(emp);
		const ro_pct = ro_docstatus_completion_pct(ro.docstatus);
		const desc = (ro.service_description || "").trim();
		const svc_count = desc ? 1 : 0;
		const primary = desc || __("No service description");
		const ro_route = frappe.utils.get_form_link("Repair Order", ro.name);
		const menu_href = attr_url(ro_route);
		const cur = currency || frappe.boot.sysdefaults.currency;
		const time_fmt = format_ro_datetime_long(
			ro.expected_completion_date,
			ro.repair_date
		);

		const is_current_ro =
			context_doc.doctype === "Repair Order" && ro.name === context_doc.name;
		const is_linked_estimate =
			context_doc.doctype === "Repair Estimate" &&
			context_doc.repair_order &&
			ro.name === context_doc.repair_order;
		const hl =
			is_current_ro || is_linked_estimate ? " autods-sa-jc-panel--current" : "";

		const meta_parts = [];
		if (ro.customer) meta_parts.push(esc(ro.customer));
		meta_parts.push(esc(fmt_money(ro.grand_total, cur)));
		meta_parts.push(esc(ro_docstatus_label(ro.docstatus)));
		const extra = `<div class="autods-sa-jc-service-more">${meta_parts.join(
			" · "
		)}</div>`;

		const hint =
			is_current_ro
				? `<div class="autods-sa-ro-hint">${esc(__("This repair order"))}</div>`
				: is_linked_estimate
				  ? `<div class="autods-sa-ro-hint">${esc(
							__("Linked from this estimate")
					  )}</div>`
				  : "";

		return `<article class="autods-sa-jc-panel${hl}">
			<div class="autods-sa-jc-mechanic">
				<div class="autods-sa-jc-mechanic-label">${esc(
					__("Your service advisor")
				)}</div>
				${render_mechanic_avatar(ro.service_advisor ? emp : {}, ro_pct)}
				<div class="autods-sa-jc-mechanic-name">${advisor_name}</div>
				${
					sub
						? `<div class="autods-sa-jc-mechanic-sub">${esc(sub)}</div>`
						: ""
				}
			</div>
			<div class="autods-sa-jc-main">
				<div class="autods-sa-jc-headrow">
					<div class="autods-sa-jc-headcell">
						<span class="autods-sa-jc-hl">${esc(__("Repair order"))}</span>
						<strong>${esc(ro.name)}</strong>
					</div>
					<div class="autods-sa-jc-headcell">
						<span class="autods-sa-jc-hl">${esc(__("Expected completion"))}</span>
						<strong>${esc(time_fmt)}</strong>
					</div>
					<div class="autods-sa-jc-headcell">
						<span class="autods-sa-jc-hl">${esc(__("Vehicle"))}</span>
						<strong>${esc(vehicle_headline)}</strong>
					</div>
					<a class="autods-sa-jc-menu" href="${menu_href}" title="${esc(
			__("Open repair order")
		)}">⋯</a>
				</div>
				<div class="autods-sa-jc-body">
					<div class="autods-sa-jc-services-label">${esc(
						__("Service description")
					)} (${esc(String(svc_count))})</div>
					<div class="autods-sa-jc-service-title">${esc(primary)}</div>
					${extra}
					${hint}
					<a class="autods-sa-jc-view" href="${menu_href}">${esc(
			__("View details")
		)}</a>
				</div>
			</div>
		</article>`;
	}

	function render_repair_order_history_cards(
		orders,
		doc,
		currency,
		vehicle_headline,
		emp_map
	) {
		if (!doc.vehicle_unit) {
			return `<p class="autods-sa-muted">${esc(
				__(
					"Link a Vehicle Unit on this document to see repair orders for that vehicle."
				)
			)}</p>`;
		}
		if (!orders.length) {
			return `<p class="autods-sa-muted">${esc(
				__(
					"No Repair Orders found for this vehicle yet."
				)
			)}</p>`;
		}
		return `<div class="autods-sa-jc-deck">${orders
			.map((ro) =>
				render_repair_order_panel(
					ro,
					emp_map,
					vehicle_headline,
					doc,
					currency
				)
			)
			.join("")}</div>`;
	}

	function jc_progress_pct(status) {
		switch (status) {
			case "Completed":
				return 100;
			case "Work In Progress":
				return 65;
			case "On Hold":
				return 35;
			case "Open":
				return 20;
			case "Cancelled":
				return 0;
			default:
				return 15;
		}
	}

	function completion_from_job_cards(job_cards) {
		if (!job_cards || !job_cards.length) return null;
		const done = job_cards.filter((j) => j.status === "Completed").length;
		return Math.round((done / job_cards.length) * 100);
	}

	function completion_display(job_cards, doc) {
		const from_jc = completion_from_job_cards(job_cards);
		if (from_jc !== null) {
			return { pct: from_jc, sub: `${job_cards.length} ${__("job cards")}` };
		}
		if (doc.doctype === "Repair Estimate" || doc.doctype === "Repair Order") {
			const st = doc.status || "Draft";
			const pct =
				ESTIMATE_STATUS_PCT[st] != null ? ESTIMATE_STATUS_PCT[st] : 15;
			return { pct, sub: st };
		}
		return { pct: 0, sub: __("No job cards") };
	}

	function appointment_datetime_ms(dateStr, timeStr) {
		if (!dateStr) return null;
		const t = (timeStr || "00:00:00").toString().trim();
		const pad = t.split(":").length === 2 ? `${t}:00` : t;
		if (window.moment) {
			const m = moment(`${dateStr} ${pad}`, ["YYYY-MM-DD HH:mm:ss", "YYYY-MM-DD H:mm:ss"], true);
			if (m.isValid()) return m.valueOf();
		}
		const iso = `${dateStr}T${pad.length === 5 ? `${pad}:00` : pad}`;
		const x = Date.parse(iso);
		return Number.isNaN(x) ? null : x;
	}

	function service_appointment_arrived(sa) {
		if (!sa) return false;
		const st = (sa.status || "").trim();
		return st === "In Progress" || st === "Completed";
	}

	function format_countdown_until_appointment(ms) {
		const totalMin = Math.max(0, Math.floor(ms / 60000));
		if (totalMin < 1) return __("Less than 1 min");
		const days = Math.floor(totalMin / 1440);
		const hours = Math.floor((totalMin % 1440) / 60);
		const mins = totalMin % 60;
		if (days > 0) {
			return __("{0}d {1}h", [String(days), String(hours)]);
		}
		if (hours > 0) {
			return __("{0}h {1}m", [String(hours), String(mins)]);
		}
		return __("{0} min", [String(mins)]);
	}

	function fmt_appointment_header_long(sa) {
		if (!sa || !sa.appointment_date) return "";
		const datePart = fmt_date(sa.appointment_date);
		const s = sa.appointment_start_time || "";
		const e = sa.appointment_end_time || "";
		const t = [s, e].filter(Boolean).join(" – ");
		if (window.moment) {
			try {
				const m = moment(sa.appointment_date, "YYYY-MM-DD", true);
				if (m.isValid()) {
					const wd = m.format("dddd, MMM D, YYYY");
					return t ? `${wd} · ${t}` : wd;
				}
			} catch (e) {
				/* fall through */
			}
		}
		return t ? `${datePart} · ${t}` : datePart;
	}

	/**
	 * Repair Estimate only: ring color + center copy from appointment / conversion.
	 * Returns null → use standard completion_display + donut.
	 */
	function estimate_appointment_gauge(doc, sa, job_cards) {
		if (doc.doctype !== "Repair Estimate") return null;

		const ro_link = doc.repair_order && String(doc.repair_order).trim();
		const converted =
			!!ro_link || (doc.status || "").trim() === "Converted to RO";
		if (converted) {
			return {
				ringPct: 100,
				ringColor: GREEN,
				mainIsPercent: false,
				main: __("Converted"),
				sub: ro_link || __("Repair order linked"),
			};
		}

		if (!sa || !sa.appointment_date) return null;
		const st = (sa.status || "").trim();
		if (st === "Cancelled" || st === "No-show") return null;

		if (service_appointment_arrived(sa)) {
			return {
				ringPct: 100,
				ringColor: GRAY_RING,
				mainIsPercent: false,
				main: __("Arrived"),
				sub: "",
			};
		}

		const startMs = appointment_datetime_ms(
			sa.appointment_date,
			sa.appointment_start_time
		);
		const endMs = appointment_datetime_ms(
			sa.appointment_date,
			sa.appointment_end_time || sa.appointment_start_time
		);
		if (startMs == null || endMs == null) return null;

		const now = Date.now();

		if (now > endMs || (now >= startMs && !service_appointment_arrived(sa))) {
			return {
				ringPct: 100,
				ringColor: RED_D,
				mainIsPercent: false,
				main: __("Overdue"),
				sub: __("Not arrived"),
			};
		}

		const msLeft = startMs - now;
		return {
			ringPct: 72,
			ringColor: AMBER,
			mainIsPercent: false,
			main: format_countdown_until_appointment(msLeft),
			sub: __("Until appointment"),
		};
	}

	/** Gauge when the open form is the Service Appointment itself. */
	function service_appointment_doc_gauge(sa) {
		if (!sa || sa.__islocal) {
			return {
				ringPct: 0,
				ringColor: GRAY_RING,
				mainIsPercent: false,
				main: __("—"),
				sub: __("Save to preview"),
			};
		}
		const st = (sa.status || "").trim();
		if (st === "Completed") {
			return {
				ringPct: 100,
				ringColor: GREEN,
				mainIsPercent: false,
				main: __("Completed"),
				sub: "",
			};
		}
		if (st === "Cancelled" || st === "No-show") {
			return {
				ringPct: 100,
				ringColor: RED_D,
				mainIsPercent: false,
				main: st === "Cancelled" ? __("Cancelled") : __("No-show"),
				sub: "",
			};
		}
		if (st === "In Progress") {
			return {
				ringPct: 100,
				ringColor: GRAY_RING,
				mainIsPercent: false,
				main: __("In progress"),
				sub: "",
			};
		}
		if (!sa.appointment_date) {
			return {
				ringPct: 25,
				ringColor: AMBER,
				mainIsPercent: false,
				main: st || __("Scheduled"),
				sub: __("Set appointment date"),
			};
		}
		const startMs = appointment_datetime_ms(
			sa.appointment_date,
			sa.appointment_start_time
		);
		const endMs = appointment_datetime_ms(
			sa.appointment_date,
			sa.appointment_end_time || sa.appointment_start_time
		);
		if (startMs == null || endMs == null) {
			return {
				ringPct: 50,
				ringColor: AMBER,
				mainIsPercent: false,
				main: st || __("Scheduled"),
				sub: fmt_appointment_time_window(sa),
			};
		}
		const now = Date.now();
		if (now > endMs || (now >= startMs && !service_appointment_arrived(sa))) {
			return {
				ringPct: 100,
				ringColor: RED_D,
				mainIsPercent: false,
				main: __("Overdue"),
				sub: __("Not arrived"),
			};
		}
		const msLeft = startMs - now;
		return {
			ringPct: 72,
			ringColor: AMBER,
			mainIsPercent: false,
			main: format_countdown_until_appointment(msLeft),
			sub: __("Until appointment"),
		};
	}

	function donut_color(pct) {
		if (pct >= 85) return GREEN;
		if (pct >= 40) return AMBER;
		return RED_D;
	}

	function donut_svg(pct, strokeColor) {
		const r = 40;
		const c = 2 * Math.PI * r;
		const p = Math.min(100, Math.max(0, pct)) / 100;
		const dash = p * c;
		return `<svg class="autods-sa-donut" width="112" height="112" viewBox="0 0 100 100" aria-hidden="true">
			<g transform="translate(50,50)">
				<circle r="${r}" fill="none" stroke="#e9ecef" stroke-width="10" />
				<circle r="${r}" fill="none" stroke="${strokeColor}" stroke-width="10"
					stroke-dasharray="${dash} ${c}"
					stroke-linecap="round"
					transform="rotate(-90)" />
			</g>
		</svg>`;
	}

	function bind_dashboard_ui(fld, frm) {
		const $root = fld.$wrapper.find(".autods-sa");
		$root
			.off("click.autodsSa")
			.on("click.autodsSa", "[data-autods-tab]", function () {
				const tab = $(this).data("autods-tab");
				$root.find("[data-autods-tab]").removeClass("autods-sa-tab--active");
				$(this).addClass("autods-sa-tab--active");
				$root.find(".autods-sa-panel").removeClass("autods-sa-panel--active");
				$root
					.find(`.autods-sa-panel[data-autods-panel="${tab}"]`)
					.addClass("autods-sa-panel--active");
			})
			.on("click.autodsSa", ".autods-sa-insp-edit-btn", function (e) {
				const fieldname = $(this).attr("data-autods-focus-field");
				if (!fieldname) {
					return;
				}
				e.preventDefault();
				e.stopPropagation();
				if (!frm || !frm.fields_dict[fieldname]) {
					frappe.msgprint(
						__(
							"Open the standard form tabs to edit this checklist."
						)
					);
					return;
				}
				frm.scroll_to_field(fieldname, true);
			});
	}

	async function render_dashboard(frm) {
		const fld = frm.fields_dict.dashboard_html;
		if (!fld || !fld.$wrapper) return;

		try {
			await render_dashboard_body(frm, fld);
		} catch (e) {
			console.error("autods dashboard render failed", e);
			fld.$wrapper
				.empty()
				.html(
					`<p class="autods-sa-muted">${esc(
						__(
							"Could not load dashboard. Save the document and refresh, or check the browser console for details."
						)
					)}</p>`
				);
		}
	}

	async function render_dashboard_body(frm, fld) {
		const dash_gen = frm._autods_dash_gen || 0;
		const d = frm.doc;
		const isServiceAppointment = d.doctype === "Service Appointment";
		const ro_name = repair_order_name_for_job_cards(d);

		let vuData = null;
		let vu_header_description = "";
		let imagePath;
		let job_cards;
		let ro_history;
		let sa_doc;

		if (isServiceAppointment) {
			[vuData, job_cards, ro_history] = await Promise.all([
				fetch_vehicle_unit_for_dashboard(d.vehicle_unit),
				safe_fetch_job_cards_full(ro_name),
				safe_fetch_repair_orders_for_vehicle(d.vehicle_unit),
			]);
			sa_doc = d;
			imagePath = vuData && vuData.image ? vuData.image : null;
		} else {
			let vu_header;
			[vu_header, job_cards, ro_history, sa_doc] = await Promise.all([
				fetch_vehicle_unit_header_fields(d.vehicle_unit),
				safe_fetch_job_cards_full(ro_name),
				safe_fetch_repair_orders_for_vehicle(d.vehicle_unit),
				fetch_service_appointment_doc(d.service_appointment),
			]);
			imagePath = vu_header && vu_header.image ? vu_header.image : null;
			vu_header_description = vu_header && vu_header.description ? vu_header.description : "";
		}

		const [emp_map, linkLabels] = await Promise.all([
			fetch_employees_map([
				...job_cards.map((jc) => jc.technician),
				...ro_history.map((r) => r.service_advisor),
				...(sa_doc && sa_doc.service_advisor ? [sa_doc.service_advisor] : []),
				...(d.service_advisor ? [d.service_advisor] : []),
			]),
			fetch_dashboard_header_link_labels(d),
		]);

		const imgUrl = imagePath ? file_to_img_src(imagePath) : "";

		const appt_gauge = isServiceAppointment
			? service_appointment_doc_gauge(d)
			: estimate_appointment_gauge(d, sa_doc, job_cards);
		let completion_pct;
		let completion_sub;
		let ring_color;
		let gauge_pct_inner_html;
		if (appt_gauge) {
			completion_pct = appt_gauge.ringPct;
			ring_color = appt_gauge.ringColor;
			completion_sub = appt_gauge.sub;
			gauge_pct_inner_html = appt_gauge.mainIsPercent
				? `${esc(String(appt_gauge.main))}%`
				: `<span class="autods-sa-gauge-main-line">${esc(appt_gauge.main)}</span>`;
		} else {
			const cd = completion_display(job_cards, d);
			completion_pct = cd.pct;
			completion_sub = cd.sub;
			ring_color = donut_color(completion_pct);
			gauge_pct_inner_html = `${esc(String(completion_pct))}%`;
		}
		const gauge_pct_class =
			appt_gauge && !appt_gauge.mainIsPercent
				? "autods-sa-gauge-pct autods-sa-gauge-pct--text"
				: "autods-sa-gauge-pct";

		const gauge_sub_html = completion_sub
			? `<div class="autods-sa-gauge-sub">${esc(completion_sub)}</div>`
			: "";

		const plate = d.plate_no || "—";

		const headline = isServiceAppointment
			? vuData
				? vehicle_headline_from_vu(vuData)
				: d.subject && String(d.subject).trim()
				  ? String(d.subject).trim()
				  : __("Service appointment")
			: vehicle_headline(d);

		const vu_desc_sa =
			vuData && vuData.description ? String(vuData.description).trim() : "";
		const vehicle_meta_line =
			isServiceAppointment ?
				vu_desc_sa || headline
			:	vu_header_description || headline;

		let header_date_label;
		let header_date_display;
		if (d.doctype === "Repair Order") {
			header_date_label = __("Repair date");
			header_date_display = fmt_date(d.repair_date);
		} else if (d.doctype === "Repair Estimate") {
			header_date_label = __("Estimate date");
			header_date_display = fmt_date(d.estimate_date);
			if (
				sa_doc &&
				sa_doc.appointment_date &&
				fmt_appointment_time_only(sa_doc)
			) {
				header_date_display = `${header_date_display} · ${fmt_appointment_time_only(sa_doc)}`;
			}
		} else {
			header_date_label = __("Appointment date");
			header_date_display = fmt_appointment_time_window(d);
		}

		const advisor_id = d.service_advisor;
		const advisor_display =
			advisor_id && emp_map[advisor_id] ?
				emp_map[advisor_id].employee_name || advisor_id
			:	advisor_id || "";

		const header_meta_html = render_dashboard_header_meta([
			["fa-user", __("Customer"), linkLabels.customer_display],
			["fa-tag", __("Service type"), linkLabels.service_type_display],
			["fa-wrench", __("Repair type"), linkLabels.repair_type_display],
			["fa-black-tie", __("Service advisor"), advisor_display],
			["fa-calendar", header_date_label, header_date_display],
			["fa-car", __("Vehicle"), vehicle_meta_line],
		]);
		const diagnostics = diagnostics_rows(d);
		const concerns = concerns_rows(d);

		let concerns_cards_html = "";
		if (d.doctype === "Repair Estimate") {
			const catNames = concerns
				.map((c) => c.concern_category)
				.filter(Boolean);
			const concernNames = concerns.map((c) => c.concern).filter(Boolean);
			const diagnosticNames = diagnostics
				.map((x) => x.diagnostic)
				.filter(Boolean);
			const [catMap, concernMap, diagMap] = await Promise.all([
				fetch_concern_category_map(catNames),
				fetch_repair_concern_map(concernNames),
				fetch_repair_diagnostic_map(diagnosticNames),
			]);
			concerns_cards_html = render_estimate_concerns_cards(
				concerns,
				diagnostics,
				catMap,
				concernMap,
				diagMap
			);
		}

		const jc_deck_html = render_job_cards_deck(job_cards, emp_map, {
			context_doctype: d.doctype,
			repair_order_name: ro_name,
		});
		const health_panel_html = isServiceAppointment
			? jc_deck_html
			: d.doctype === "Repair Estimate"
			  ? concerns_cards_html
			  : jc_deck_html;
		const first_tab_label = isServiceAppointment
			? __("Job Cards")
			: d.doctype === "Repair Estimate"
			  ? __("Concerns and Causes")
			  : __("Job Cards");

		const appointment_html = isServiceAppointment
			? render_service_appointment_detail_panel(d, emp_map)
			: render_appointment_panel(sa_doc, emp_map);
		const appointmentTabBadge =
			!isServiceAppointment && d.service_appointment
				? `<span class="autods-sa-badge autods-sa-badge--blue">1</span>`
				: "";
		const currency =
			d.currency || frappe.boot.sysdefaults.currency;

		const inspections_html = await render_inspections_panel(d);
		const inspection_row_count = count_inspection_rows(d);

		let detailsTabCount;
		if (isServiceAppointment) {
			let n = 0;
			const bump = (x) => {
				if (x != null && String(x).trim()) n += 1;
			};
			bump(d.plate_no);
			bump(d.vehicle_id_no);
			if (vuData) {
				bump(vuData.year_model);
				bump(vuData.make);
				bump(vuData.model);
				bump(vuData.variant);
				bump(vuData.transmission_type);
				bump(vuData.drive_type);
				bump(vuData.fuel_type);
				bump(vuData.body_type);
			}
			detailsTabCount = n;
		} else {
			detailsTabCount =
				d.doctype === "Repair Estimate" ?
					0
				:	concerns.length + diagnostics.length;
		}
		const historyTabCount = ro_history.length;

		const history_cards_html = render_repair_order_history_cards(
			ro_history,
			d,
			currency,
			headline,
			emp_map
		);

		let vu_route = "";
		if (d.vehicle_unit) {
			vu_route = frappe.utils.get_form_link("Vehicle Unit", d.vehicle_unit);
		}

		let detail_fields;
		if (isServiceAppointment && vuData) {
			detail_fields = [
				[__("Plate"), d.plate_no || "—"],
				[__("VIN / ID"), d.vehicle_id_no || "—"],
				[__("Year"), vuData.year_model || "—"],
				[__("Make"), vuData.make || "—"],
				[__("Model"), vuData.model || "—"],
				[__("Variant"), vuData.variant || "—"],
				[__("Transmission"), vuData.transmission_type || "—"],
				[__("Drive type"), vuData.drive_type || "—"],
				[__("Fuel"), vuData.fuel_type || "—"],
				[__("Body type"), vuData.body_type || "—"],
			];
		} else if (isServiceAppointment) {
			detail_fields = [
				[__("Plate"), plate],
				[__("VIN / ID"), d.vehicle_id_no || "—"],
				[
					__("Vehicle unit"),
					d.vehicle_unit || __("Not linked"),
				],
			];
		} else {
			detail_fields = [
				[__("Plate"), plate],
				[__("VIN / ID"), d.vehicle_id_no || "—"],
				[__("Odometer"), d.odometer || "—"],
				[__("Color"), d.vehicle_color || "—"],
				[__("Transmission"), d.vehicle_transmission_type || "—"],
				[__("Drive type"), d.vehicle_drive_type || "—"],
				[__("Fuel"), d.vehicle_fuel_type || "—"],
				[__("Body type"), d.vehicle_body_type || "—"],
			];
		}

		const inspections_intro = isServiceAppointment
			? __(
					"Inspection checklists are recorded on the Repair Estimate or Repair Order linked to this appointment. Open those documents to view or edit inspections."
				)
			: __(
					"Each row is its own card. Expand Inspection items to see lines from the linked Service Inspection. Use Update checklist to edit rows on the main form."
				);

		const badge = (n, blue) =>
			n > 0
				? `<span class="autods-sa-badge${blue ? " autods-sa-badge--blue" : ""}">${esc(
						String(Math.min(99, n))
				  )}</span>`
				: "";

		const show_charges_dash =
			!isServiceAppointment &&
			(d.doctype === "Repair Order" || d.doctype === "Repair Estimate");
		const charges_line_count = show_charges_dash ? (d.charges || []).length : 0;

		const tabs_bar = isServiceAppointment
			? `<div class="autods-sa-tabs">
		<button type="button" class="autods-sa-tab autods-sa-tab--active" data-autods-tab="appointment">${esc(
			__("Appointment")
		)}</button>
		<button type="button" class="autods-sa-tab" data-autods-tab="health">${esc(
			first_tab_label
		)}${badge(job_cards.length, true)}</button>
		<button type="button" class="autods-sa-tab" data-autods-tab="details">${esc(
			__("Vehicle Details")
		)}${badge(detailsTabCount, true)}</button>
		<button type="button" class="autods-sa-tab" data-autods-tab="inspections">${esc(
			__("Inspections")
		)}${badge(inspection_row_count, true)}</button>
		<button type="button" class="autods-sa-tab" data-autods-tab="history">${esc(
			__("Service History")
		)}${badge(historyTabCount, false)}</button>
	</div>`
			: show_charges_dash
			? `<div class="autods-sa-tabs">
		<button type="button" class="autods-sa-tab autods-sa-tab--active" data-autods-tab="health">${esc(
			first_tab_label
		)}</button>
		<button type="button" class="autods-sa-tab" data-autods-tab="charges">${esc(
			__("Charges")
		)}${badge(charges_line_count, true)}</button>
		<button type="button" class="autods-sa-tab" data-autods-tab="appointment">${esc(
			__("Appointment")
		)}${appointmentTabBadge}</button>
		<button type="button" class="autods-sa-tab" data-autods-tab="details">${esc(
			__("Vehicle Details")
		)}${badge(detailsTabCount, true)}</button>
		<button type="button" class="autods-sa-tab" data-autods-tab="inspections">${esc(
			__("Inspections")
		)}${badge(inspection_row_count, true)}</button>
		<button type="button" class="autods-sa-tab" data-autods-tab="history">${esc(
			__("Service History")
		)}${badge(historyTabCount, false)}</button>
	</div>`
			: `<div class="autods-sa-tabs">
		<button type="button" class="autods-sa-tab autods-sa-tab--active" data-autods-tab="health">${esc(
			first_tab_label
		)}</button>
		<button type="button" class="autods-sa-tab" data-autods-tab="appointment">${esc(
			__("Appointment")
		)}${appointmentTabBadge}</button>
		<button type="button" class="autods-sa-tab" data-autods-tab="details">${esc(
			__("Vehicle Details")
		)}${badge(detailsTabCount, true)}</button>
		<button type="button" class="autods-sa-tab" data-autods-tab="inspections">${esc(
			__("Inspections")
		)}${badge(inspection_row_count, true)}</button>
		<button type="button" class="autods-sa-tab" data-autods-tab="history">${esc(
			__("Service History")
		)}${badge(historyTabCount, false)}</button>
	</div>`;

		const health_panel_class = isServiceAppointment
			? "autods-sa-panel"
			: "autods-sa-panel autods-sa-panel--active";
		const appointment_panel_class = isServiceAppointment
			? "autods-sa-panel autods-sa-panel--active"
			: "autods-sa-panel";

		const charges_panel_html = show_charges_dash
			? `<div class="autods-sa-panel" data-autods-panel="charges">
			<h3 class="autods-sa-panel-title">${esc(__("Charges"))}</h3>
			<p class="autods-sa-insp-intro">${esc(
				__(
					"Add or edit services, spareparts, and overhead. Save the document to persist changes."
				)
			)}</p>
			<div class="autods-dashboard-charges-root"></div>
		</div>`
			: "";

		const details_grid = detail_fields
			.map(
				([k, v]) => `<div class="autods-sa-kv"><span>${esc(k)}</span><strong>${esc(
					v
				)}</strong></div>`
			)
			.join("");

		const vu_link = vu_route
			? `<p><a class="autods-sa-text-link" href="${attr_url(vu_route)}">${esc(
					__("Open Vehicle Unit")
			  )}</a></p>`
			: "";

		const img_block = imgUrl
			? `<div class="autods-sa-photo"><img src="${attr_url(imgUrl)}" alt="" /></div>`
			: `<div class="autods-sa-photo autods-sa-photo--empty"><span>${esc(
					__("No vehicle photo")
			  )}</span></div>`;

		const html = `
<style>
.autods-sa {
	font-family: "Inter", "Segoe UI", system-ui, sans-serif;
	color: #333333;
	background: ${BG_MUTED};
	border-radius: 12px;
	overflow: hidden;
	max-width: 1100px;
	margin: 0 auto 2.5rem;
	box-sizing: border-box;
}
.autods-sa * { box-sizing: border-box; }
.autods-sa-top {
	background: ${HEADER_BG};
	padding: 1.35rem 1.5rem 0;
}
.autods-sa-head {
	display: flex;
	align-items: flex-end;
	gap: 1.5rem;
	flex-wrap: wrap;
	margin-bottom: 0;
	width: 100%;
	padding-bottom: 0.35rem;
}
.autods-sa-body {
	padding: 1rem 1.5rem 1.5rem;
	background: ${BG_MUTED};
}
.autods-sa-photo {
	flex-shrink: 0;
	width: min(220px, 38vw);
	min-height: 100px;
	max-height: 140px;
	display: flex;
	align-items: center;
	justify-content: center;
	background: transparent;
	border: none;
	border-radius: 0;
	box-shadow: none;
	overflow: visible;
}
.autods-sa-photo img {
	max-width: 100%;
	max-height: 132px;
	width: auto;
	height: auto;
	object-fit: contain;
	object-position: center bottom;
	display: block;
}
.autods-sa-photo--empty {
	width: 160px;
	min-height: 88px;
	color: #6c757d;
	font-size: 0.75rem;
	text-align: center;
	padding: 0.75rem 0.5rem;
	background: transparent;
	border: none;
	border-radius: 0;
}
.autods-sa-title-block {
	flex: 1;
	min-width: 200px;
	align-self: center;
	padding-bottom: 0.5rem;
}
.autods-sa-title-block h1 {
	margin: 0 0 0.35rem;
	font-size: 1.35rem;
	font-weight: 700;
	letter-spacing: -0.02em;
	line-height: 1.25;
	color: #333333;
}
.autods-sa-header-meta {
	font-size: 0.8rem;
	line-height: 1.45;
	color: #868e96;
	max-width: 52rem;
}
.autods-sa-meta-grid {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 0.4rem 1.25rem;
	align-items: start;
}
@media (max-width: 640px) {
	.autods-sa-meta-grid {
		grid-template-columns: 1fr;
	}
}
.autods-sa-meta-line {
	display: flex;
	gap: 0.45rem;
	align-items: flex-start;
	margin: 0;
	min-width: 0;
}
.autods-sa-meta-icon {
	flex-shrink: 0;
	width: 1.1rem;
	text-align: center;
	color: #868e96;
	font-size: 0.85rem;
	line-height: 1.35;
	margin-top: 0.12em;
}
.autods-sa-meta-value {
	font-weight: 500;
	color: #868e96;
	min-width: 0;
	flex: 1 1 auto;
	word-break: break-word;
}
.autods-sa-gauge {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: flex-end;
	align-self: center;
	min-width: 112px;
	margin-bottom: 0.25rem;
}
.autods-sa-gauge-ring {
	position: relative;
	width: 112px;
	height: 112px;
	flex-shrink: 0;
}
.autods-sa-gauge-ring > svg {
	display: block;
	position: absolute;
	top: 0;
	left: 0;
	pointer-events: none;
}
.autods-sa-gauge-inner {
	position: absolute;
	inset: 0;
	z-index: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	text-align: center;
	padding: 0 10px;
	/* Optical center inside donut hole (stroke eats lower visual weight) */
	transform: translateY(-3px);
}
.autods-sa-gauge-score {
	font-size: 1.35rem;
	font-weight: 700;
	color: #212529;
	line-height: 1.1;
}
.autods-sa-gauge-pct {
	font-size: 1.05rem;
	font-weight: 700;
	color: #212529;
	line-height: 1.15;
	margin: 0;
}
.autods-sa-gauge-sub {
	font-size: 0.62rem;
	color: #6c757d;
	margin: 0.1rem 0 0;
	max-width: 92px;
	line-height: 1.25;
}
.autods-sa-tabs {
	display: flex;
	flex-wrap: wrap;
	gap: 0.25rem 1.5rem;
	border-bottom: 1px solid #dee2e6;
	margin: 0 -1.5rem;
	padding: 0.35rem 1.5rem 0;
	background: ${HEADER_BG};
}
.autods-sa-tab {
	background: none;
	border: none;
	padding: 0.65rem 0 0.85rem;
	font-size: 0.72rem;
	font-weight: 600;
	letter-spacing: 0.06em;
	color: #868e96;
	cursor: pointer;
	position: relative;
	display: inline-flex;
	align-items: center;
	gap: 0.35rem;
}
.autods-sa-tab--active { color: #212529; }
.autods-sa-tab--active::after {
	content: "";
	position: absolute;
	left: 0;
	right: 0;
	bottom: -1px;
	height: 3px;
	background: #212529;
	border-radius: 2px 2px 0 0;
}
.autods-sa-badge {
	min-width: 1.15rem;
	height: 1.15rem;
	padding: 0 0.35rem;
	border-radius: 10px;
	background: #dee2e6;
	color: #495057;
	font-size: 0.65rem;
	font-weight: 700;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	line-height: 1;
}
.autods-sa-badge--blue {
	background: ${BLUE_BADGE};
	color: #fff;
}
.autods-sa-shell {
	background: #ffffff;
	border: 1px solid #e9ecef;
	border-radius: 10px;
	padding: 1.25rem;
	box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.autods-sa-panel { display: none; }
.autods-sa-panel--active { display: block; }
.autods-sa-jc-deck {
	display: flex;
	flex-direction: column;
	gap: 0;
}
.autods-sa-jc-panel {
	display: flex;
	flex-direction: row;
	align-items: stretch;
	gap: 1.35rem;
	background: #fff;
	border: 1px solid #e9ecef;
	border-radius: 12px;
	padding: 1.25rem 1.4rem;
	margin-bottom: 1rem;
	box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.autods-sa-jc-panel:last-child { margin-bottom: 0; }
.autods-sa-jc-panel--current {
	border-color: ${GREEN};
	box-shadow: 0 0 0 1px ${GREEN};
}
@media (max-width: 720px) {
	.autods-sa-jc-panel { flex-direction: column; align-items: center; }
	.autods-sa-jc-mechanic { width: 100% !important; max-width: 220px; }
}
.autods-sa-jc-mechanic {
	width: 132px;
	flex-shrink: 0;
	text-align: center;
}
.autods-sa-jc-mechanic-label {
	font-size: 0.62rem;
	font-weight: 600;
	color: #868e96;
	text-transform: uppercase;
	letter-spacing: 0.06em;
	margin-bottom: 0.65rem;
}
.autods-sa-jc-avatar-ringbox {
	width: 80px;
	height: 80px;
	margin: 0 auto 0.6rem;
	position: relative;
}
.autods-sa-jc-av-svg {
	position: absolute;
	top: 0;
	left: 0;
	pointer-events: none;
}
.autods-sa-jc-avatar-photo {
	position: absolute;
	top: 50%;
	left: 50%;
	transform: translate(-50%, -50%);
	width: 56px;
	height: 56px;
	border-radius: 50%;
	overflow: hidden;
	background: #e9ecef;
	z-index: 1;
	display: flex;
	align-items: center;
	justify-content: center;
}
.autods-sa-jc-avatar-photo img {
	width: 100%;
	height: 100%;
	object-fit: cover;
}
.autods-sa-jc-av-placeholder {
	font-size: 1.35rem;
	font-weight: 700;
	color: #adb5bd;
}
.autods-sa-jc-avatar-pct {
	position: absolute;
	bottom: 2px;
	left: 50%;
	transform: translateX(-50%);
	font-size: 9px;
	font-weight: 700;
	line-height: 1.15;
	padding: 2px 5px;
	border-radius: 8px;
	background: rgba(255,255,255,0.96);
	color: #212529;
	box-shadow: 0 1px 2px rgba(0,0,0,0.06);
	white-space: nowrap;
	z-index: 2;
}
.autods-sa-jc-mechanic-name {
	font-size: 0.9rem;
	font-weight: 700;
	color: #333333;
	line-height: 1.25;
	word-break: break-word;
}
.autods-sa-jc-mechanic-sub {
	font-size: 0.72rem;
	color: #868e96;
	margin-top: 0.25rem;
	line-height: 1.3;
}
.autods-sa-jc-main {
	flex: 1;
	min-width: 0;
}
.autods-sa-jc-headrow {
	display: grid;
	grid-template-columns: minmax(0,1fr) minmax(0,1.3fr) minmax(0,1.3fr) auto;
	gap: 0.85rem 1rem;
	padding-bottom: 1rem;
	border-bottom: 1px solid #e9ecef;
	align-items: start;
}
@media (max-width: 900px) {
	.autods-sa-jc-headrow {
		grid-template-columns: 1fr 1fr;
	}
	.autods-sa-jc-headcell:nth-child(3) { grid-column: 1 / -1; }
}
.autods-sa-jc-hl {
	display: block;
	font-size: 0.62rem;
	font-weight: 600;
	color: #868e96;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	margin-bottom: 0.25rem;
}
.autods-sa-jc-headcell strong {
	display: block;
	font-size: 0.82rem;
	font-weight: 600;
	color: #333333;
	line-height: 1.35;
}
.autods-sa-jc-menu {
	flex-shrink: 0;
	align-self: start;
	width: 2rem;
	height: 2rem;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 8px;
	color: #adb5bd;
	font-size: 1.25rem;
	line-height: 1;
	text-decoration: none;
	font-weight: 700;
}
.autods-sa-jc-menu:hover {
	background: #f1f3f5;
	color: #495057;
}
.autods-sa-jc-body {
	padding-top: 1rem;
}
.autods-sa-jc-services-label {
	font-size: 0.68rem;
	font-weight: 600;
	color: #868e96;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	margin-bottom: 0.45rem;
}
.autods-sa-jc-service-title {
	font-size: 1.2rem;
	font-weight: 600;
	color: #3d5a6c;
	line-height: 1.3;
	margin-bottom: 0.35rem;
}
.autods-sa-jc-service-more {
	font-size: 0.8rem;
	color: #6c757d;
	line-height: 1.4;
	margin-bottom: 0.75rem;
}
.autods-sa-jc-view {
	display: inline-block;
	font-size: 0.85rem;
	font-weight: 600;
	color: ${BLUE_BADGE};
	text-decoration: none;
	margin-top: 0.25rem;
}
.autods-sa-jc-view:hover { text-decoration: underline; }
.autods-sa-muted { color: #868e96; font-size: 0.9rem; margin: 0; }
.autods-sa-insp-intro {
	font-size: 0.82rem;
	color: #6c757d;
	margin: 0 0 1rem;
	line-height: 1.45;
}
.autods-sa-insp-stack {
	display: flex;
	flex-direction: column;
	gap: 1.25rem;
}
.autods-sa-insp-section {
	display: flex;
	flex-direction: column;
	gap: 0.65rem;
}
.autods-sa-insp-section-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 0.75rem;
	flex-wrap: wrap;
}
.autods-sa-insp-section-head-text {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	min-width: 0;
	flex-wrap: wrap;
}
.autods-sa-insp-section-title {
	margin: 0;
	font-size: 0.82rem;
	font-weight: 700;
	color: #495057;
	text-transform: uppercase;
	letter-spacing: 0.04em;
}
.autods-sa-insp-count {
	font-size: 0.7rem;
	font-weight: 700;
	color: #495057;
	background: #e9ecef;
	padding: 0.15rem 0.45rem;
	border-radius: 10px;
}
.autods-sa-insp-row-stack {
	display: flex;
	flex-direction: column;
	gap: 0.65rem;
}
.autods-sa-insp-row-card {
	background: #fff;
	border: 1px solid #e9ecef;
	border-radius: 10px;
	padding: 0.75rem 1rem;
	box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.autods-sa-insp-row-card-header {
	display: flex;
	flex-direction: column;
	align-items: flex-start;
	gap: 0.25rem;
}
.autods-sa-insp-row-card-header--quality { gap: 0.35rem; }
.autods-sa-insp-row-quality-top {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 0.75rem;
	width: 100%;
	flex-wrap: wrap;
}
.autods-sa-insp-row-title { font-weight: 600; font-size: 0.9rem; color: #212529; }
.autods-sa-insp-row-meta { font-size: 0.78rem; color: #6c757d; }
.autods-sa-insp-row-si-id {
	font-size: 0.75rem;
	color: #495057;
}
.autods-sa-insp-si-link {
	font-size: 0.78rem;
	font-weight: 600;
	color: ${BLUE_BADGE};
	text-decoration: none;
	white-space: nowrap;
}
.autods-sa-insp-si-link:hover { text-decoration: underline; }
.autods-sa-insp-nested {
	margin-top: 0.5rem;
	border-top: 1px solid #f1f3f5;
	padding-top: 0.35rem;
}
.autods-sa-insp-nested:first-of-type { margin-top: 0.45rem; }
.autods-sa-insp-nested-summary {
	cursor: pointer;
	list-style: none;
	font-size: 0.78rem;
	font-weight: 600;
	color: ${BLUE_BADGE};
	padding: 0.35rem 0;
}
.autods-sa-insp-nested-summary::-webkit-details-marker { display: none; }
.autods-sa-insp-nested-body { padding-bottom: 0.25rem; }
.autods-sa-insp-kv-mini {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
	gap: 0.5rem 1rem;
	font-size: 0.78rem;
}
.autods-sa-insp-kv-mini--wide {
	grid-column: 1 / -1;
}
.autods-sa-insp-kv-mini span {
	display: block;
	font-size: 0.65rem;
	color: #868e96;
	text-transform: uppercase;
	letter-spacing: 0.03em;
	margin-bottom: 0.15rem;
}
.autods-sa-insp-kv-mini strong {
	font-weight: 600;
	color: #212529;
	word-break: break-word;
}
.autods-sa-insp-remarks {
	margin: 0;
	font-size: 0.82rem;
	line-height: 1.45;
	color: #333;
	white-space: pre-wrap;
	word-break: break-word;
}
.autods-sa-insp-edit-btn {
	flex-shrink: 0;
	border: 1px solid ${BLUE_BADGE};
	background: #fff;
	color: ${BLUE_BADGE};
	font-size: 0.72rem;
	font-weight: 600;
	padding: 0.35rem 0.65rem;
	border-radius: 6px;
	cursor: pointer;
	text-transform: uppercase;
	letter-spacing: 0.03em;
	text-decoration: none;
	display: inline-block;
}
.autods-sa-insp-edit-btn:hover {
	background: ${BLUE_BADGE};
	color: #fff;
}
.autods-sa-insp-empty { margin: 0.5rem 0 0; }
.autods-sa-insp-table-wrap {
	overflow-x: auto;
	margin-top: 0.65rem;
}
.autods-sa-insp-table {
	width: 100%;
	border-collapse: collapse;
	font-size: 0.78rem;
}
.autods-sa-insp-table th,
.autods-sa-insp-table td {
	text-align: left;
	padding: 0.45rem 0.5rem;
	border-bottom: 1px solid #f1f3f5;
	vertical-align: top;
}
.autods-sa-insp-table th {
	color: #868e96;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.03em;
	font-size: 0.65rem;
}
.autods-sa-insp-notes {
	max-width: 220px;
	word-break: break-word;
}
.autods-sa-kv-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
	gap: 0.75rem 1.25rem;
}
.autods-sa-kv span { display: block; font-size: 0.72rem; color: #868e96; text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 0.2rem; }
.autods-sa-kv strong { font-size: 0.9rem; font-weight: 600; color: #212529; }
.autods-sa-text-link { color: ${BLUE_BADGE}; text-decoration: none; font-weight: 500; font-size: 0.9rem; }
.autods-sa-text-link:hover { text-decoration: underline; }
.autods-sa-panel-title {
	margin: 0 0 1rem;
	font-size: 0.78rem;
	font-weight: 600;
	color: #868e96;
	text-transform: uppercase;
	letter-spacing: 0.05em;
}
.autods-sa-ro-hint {
	margin-top: 0.5rem;
	font-size: 0.68rem;
	font-weight: 600;
	color: ${GREEN};
	text-transform: uppercase;
	letter-spacing: 0.03em;
}
.autods-sa-appt-card {
	max-width: 720px;
}
.autods-sa-appt-card .autods-sa-kv-grid {
	margin-bottom: 0.75rem;
}
.autods-sa-appt-card--primary .autods-sa-kv-grid {
	margin-bottom: 0.5rem;
}
.autods-sa-appt-links {
	margin-top: 0.5rem;
	font-size: 0.85rem;
	line-height: 1.5;
}
.autods-sa-appt-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 0.5rem;
	margin-top: 1rem;
}
.autods-sa-gauge-pct--text {
	font-size: 0.7rem;
	font-weight: 700;
	line-height: 1.15;
	text-align: center;
	max-width: 5.25rem;
}
.autods-sa-gauge-main-line {
	display: block;
}
.autods-sa-cc-wrap { margin: -0.25rem 0 0; }
.autods-sa-cc-stack {
	display: flex;
	flex-direction: column;
	gap: 0.75rem;
}
.autods-sa-cc-card {
	background: #fff;
	border: 1px solid #e9ecef;
	border-radius: 12px;
	padding: 0;
	box-shadow: 0 1px 2px rgba(0,0,0,0.04);
	overflow: hidden;
}
.autods-sa-cc-summary {
	list-style: none;
	cursor: pointer;
	display: flex;
	align-items: center;
	gap: 1rem;
	padding: 1rem 1.15rem;
	margin: 0;
	background: #ffffff;
	border: none;
	width: 100%;
	text-align: left;
	font: inherit;
}
.autods-sa-cc-summary::-webkit-details-marker { display: none; }
.autods-sa-cc-card[open] > .autods-sa-cc-summary {
	border-bottom: 1px solid #e9ecef;
	background: #fafbfc;
}
.autods-sa-cc-index {
	flex-shrink: 0;
	width: 2.5rem;
	height: 2.5rem;
	min-width: 2.5rem;
	border-radius: 50%;
	background: ${BLUE_BADGE};
	color: #ffffff;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 0.95rem;
	font-weight: 700;
	line-height: 1;
	box-shadow: 0 1px 3px rgba(0, 123, 255, 0.35);
	letter-spacing: -0.02em;
}
.autods-sa-cc-summary-text {
	flex: 1;
	min-width: 0;
	display: flex;
	flex-direction: column;
	gap: 0.4rem;
}
.autods-sa-cc-field {
	display: flex;
	flex-direction: column;
	gap: 0.15rem;
}
.autods-sa-cc-field-label {
	font-size: 0.62rem;
	font-weight: 700;
	color: #868e96;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	line-height: 1.2;
}
.autods-sa-cc-title {
	font-size: 0.95rem;
	font-weight: 700;
	color: #212529;
	line-height: 1.35;
	word-break: break-word;
	letter-spacing: -0.01em;
}
.autods-sa-cc-field--customer .autods-sa-cc-customer {
	font-size: 0.84rem;
	font-weight: 400;
	color: #495057;
	line-height: 1.4;
	word-break: break-word;
}
.autods-sa-cc-subrow {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 0.5rem 0.75rem;
}
.autods-sa-cc-meta {
	font-size: 0.78rem;
	font-weight: 400;
	color: #6c757d;
	line-height: 1.4;
	word-break: break-word;
	flex: 1;
	min-width: 140px;
}
.autods-sa-cc-chev {
	flex-shrink: 0;
	width: 1.25rem;
	height: 1.25rem;
	margin-left: 0.15rem;
	border-right: 2px solid #adb5bd;
	border-bottom: 2px solid #adb5bd;
	transform: rotate(45deg);
	transition: transform 0.15s ease;
	opacity: 0.55;
	align-self: center;
}
.autods-sa-cc-card[open] > .autods-sa-cc-summary .autods-sa-cc-chev {
	transform: rotate(-135deg);
}
.autods-sa-cc-body {
	padding: 0.85rem 1.1rem 1rem;
}
.autods-sa-cc-notes {
	margin: 0 0 0.75rem;
	padding: 0.65rem 0.75rem;
	background: #f8f9fa;
	border-radius: 8px;
	font-size: 0.82rem;
	line-height: 1.45;
	color: #333;
}
.autods-sa-cc-notes-label {
	display: block;
	font-size: 0.62rem;
	font-weight: 700;
	color: #868e96;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	margin-bottom: 0.35rem;
}
.autods-sa-cc-notes p { margin: 0; white-space: pre-wrap; word-break: break-word; }
.autods-sa-cc-diag-section {
	border: 1px solid #e9ecef;
	border-radius: 8px;
	background: #fff;
	overflow: hidden;
	margin-top: 0.25rem;
}
.autods-sa-cc-diag-section-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 0.75rem;
	padding: 0.55rem 0.75rem;
	background: #f8f9fa;
	border-bottom: 1px solid #e9ecef;
}
.autods-sa-cc-diag-section-title {
	font-size: 0.68rem;
	font-weight: 700;
	color: #495057;
	text-transform: uppercase;
	letter-spacing: 0.04em;
}
.autods-sa-cc-diag-section-count {
	font-size: 0.72rem;
	font-weight: 700;
	color: #495057;
	background: #e9ecef;
	padding: 0.15rem 0.5rem;
	border-radius: 10px;
	min-width: 1.5rem;
	text-align: center;
}
.autods-sa-cc-diag-inner {
	padding: 0.65rem 0.75rem 0.85rem;
}
.autods-sa-cc-diag-table-wrap {
	overflow-x: auto;
	-webkit-overflow-scrolling: touch;
}
.autods-sa-cc-diag-table {
	width: 100%;
	border-collapse: collapse;
	font-size: 0.8rem;
	line-height: 1.4;
	color: #333;
}
.autods-sa-cc-diag-table th,
.autods-sa-cc-diag-table td {
	border: 1px solid #e9ecef;
	padding: 0.45rem 0.55rem;
	text-align: left;
	vertical-align: top;
}
.autods-sa-cc-diag-table th {
	background: #f8f9fa;
	font-size: 0.65rem;
	font-weight: 700;
	color: #495057;
	text-transform: uppercase;
	letter-spacing: 0.03em;
}
.autods-sa-cc-diag-td-idx {
	width: 2.25rem;
	text-align: center;
	font-weight: 700;
	color: ${BLUE_BADGE};
	white-space: nowrap;
}
.autods-sa-cc-diag-td-notes {
	white-space: pre-wrap;
	word-break: break-word;
	color: #6c757d;
	font-size: 0.78rem;
}
.autods-sa-cc-actions { margin: 1rem 0 0; }
</style>
<div class="autods-sa">
	<div class="autods-sa-top">
	<div class="autods-sa-head">
		${img_block}
		<div class="autods-sa-title-block">
			<h1>${esc(plate)}</h1>
			<div class="autods-sa-header-meta">${header_meta_html}</div>
		</div>
		<div class="autods-sa-gauge">
			<div class="autods-sa-gauge-ring">
				${donut_svg(completion_pct, ring_color)}
				<div class="autods-sa-gauge-inner">
					<div class="${gauge_pct_class}">${gauge_pct_inner_html}</div>
					${gauge_sub_html}
				</div>
			</div>
		</div>
	</div>
	${tabs_bar}
	</div>
	<div class="autods-sa-body">
	<div class="autods-sa-shell">
		${charges_panel_html}
		<div class="${health_panel_class}" data-autods-panel="health">
			${health_panel_html}
		</div>
		<div class="${appointment_panel_class}" data-autods-panel="appointment">
			${appointment_html}
		</div>
		<div class="autods-sa-panel" data-autods-panel="details">
			<div class="autods-sa-kv-grid">${details_grid}</div>
			${vu_link}
		</div>
		<div class="autods-sa-panel" data-autods-panel="inspections">
			<p class="autods-sa-insp-intro">${esc(inspections_intro)}</p>
			${inspections_html}
		</div>
		<div class="autods-sa-panel" data-autods-panel="history">
			<h3 class="autods-sa-panel-title">${esc(
				__("Repair orders for this vehicle")
			)}</h3>
			${history_cards_html}
		</div>
	</div>
	</div>
</div>`;

		if (dash_gen !== (frm._autods_dash_gen || 0)) {
			return;
		}
		const liveFld = frm.fields_dict.dashboard_html;
		if (!liveFld || !liveFld.$wrapper) {
			return;
		}
		liveFld.$wrapper.empty().html(html);
		bind_dashboard_ui(liveFld, frm);
		if (
			show_charges_dash &&
			window.autods &&
			autods.charges_overview &&
			typeof autods.charges_overview.render_all === "function"
		) {
			autods.charges_overview.render_all(frm);
		}
	}

	frappe.provide("autods.dashboard");
	autods.dashboard._debouncers = {};

	function schedule_dashboard_render(frm) {
		if (!frm || !frm.fields_dict || !frm.fields_dict.dashboard_html) {
			return;
		}
		const key = (frm.doctype || "") + ":" + (frm.docname || "new");
		if (!autods.dashboard._debouncers[key]) {
			autods.dashboard._debouncers[key] = frappe.utils.debounce(function (f) {
				f._autods_dash_gen = (f._autods_dash_gen || 0) + 1;
				render_dashboard(f);
			}, 450);
		}
		autods.dashboard._debouncers[key](frm);
	}

	autods.dashboard.schedule_render = schedule_dashboard_render;
	autods.dashboard.refresh_charges_dashboard = schedule_dashboard_render;

	const _dash = schedule_dashboard_render;

	frappe.ui.form.on("Repair Estimate", {
		refresh(frm) {
			_dash(frm);
		},
		after_save(frm) {
			_dash(frm);
		},
		customer(frm) {
			_dash(frm);
		},
		vehicle_unit(frm) {
			_dash(frm);
		},
		plate_no(frm) {
			_dash(frm);
		},
		service_type(frm) {
			_dash(frm);
		},
		repair_type(frm) {
			_dash(frm);
		},
		service_advisor(frm) {
			_dash(frm);
		},
		estimate_date(frm) {
			_dash(frm);
		},
		status(frm) {
			_dash(frm);
		},
		repair_order(frm) {
			_dash(frm);
		},
		service_appointment(frm) {
			_dash(frm);
		},
		quality_inspections(frm) {
			_dash(frm);
		},
		concerns(frm) {
			_dash(frm);
		},
		diagnostics(frm) {
			_dash(frm);
		},
	});

	frappe.ui.form.on("Repair Order", {
		refresh(frm) {
			_dash(frm);
		},
		after_save(frm) {
			_dash(frm);
		},
		customer(frm) {
			_dash(frm);
		},
		vehicle_unit(frm) {
			_dash(frm);
		},
		plate_no(frm) {
			_dash(frm);
		},
		service_type(frm) {
			_dash(frm);
		},
		repair_type(frm) {
			_dash(frm);
		},
		service_advisor(frm) {
			_dash(frm);
		},
		repair_date(frm) {
			_dash(frm);
		},
		status(frm) {
			_dash(frm);
		},
		company(frm) {
			_dash(frm);
		},
		estimate_date(frm) {
			_dash(frm);
		},
		validity_date(frm) {
			_dash(frm);
		},
		repair_estimate(frm) {
			_dash(frm);
		},
		service_appointment(frm) {
			_dash(frm);
		},
		concerns(frm) {
			_dash(frm);
		},
		diagnostics(frm) {
			_dash(frm);
		},
		quality_inspections(frm) {
			_dash(frm);
		},
	});

	frappe.ui.form.on("Service Appointment", {
		refresh(frm) {
			_dash(frm);
		},
		after_save(frm) {
			_dash(frm);
		},
		on_submit(frm) {
			_dash(frm);
		},
		on_cancel(frm) {
			_dash(frm);
		},
		appointment_date(frm) {
			_dash(frm);
		},
		appointment_start_time(frm) {
			_dash(frm);
		},
		appointment_end_time(frm) {
			_dash(frm);
		},
		status(frm) {
			_dash(frm);
		},
		customer(frm) {
			_dash(frm);
		},
		vehicle_unit(frm) {
			_dash(frm);
		},
		plate_no(frm) {
			_dash(frm);
		},
		expected_completion_date(frm) {
			_dash(frm);
		},
		service_advisor(frm) {
			_dash(frm);
		},
		subject(frm) {
			_dash(frm);
		},
		service_type(frm) {
			_dash(frm);
		},
		repair_type(frm) {
			_dash(frm);
		},
		contact_person(frm) {
			_dash(frm);
		},
		contact_mobile(frm) {
			_dash(frm);
		},
		repair_estimate(frm) {
			_dash(frm);
		},
		repair_order(frm) {
			_dash(frm);
		},
		notes(frm) {
			_dash(frm);
		},
		cancellation_reason(frm) {
			_dash(frm);
		},
	});
})();
