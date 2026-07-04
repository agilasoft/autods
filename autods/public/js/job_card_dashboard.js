// Job Card shopfloor dashboard: same visual language as Repair Order dashboard (repair_service_dashboard.js).

(function () {
	"use strict";

	const GREEN = "#28a745";
	const AMBER = "#ffc107";
	const RED_D = "#dc3545";
	const GRAY_RING = "#868e96";
	const BLUE_BADGE = "#007bff";
	const BG_MUTED = "#F4F7F9";
	const HEADER_BG = "#ffffff";

	function esc(s) {
		return frappe.utils.escape_html(s == null || s === "" ? "" : String(s));
	}

	function attr_url(u) {
		if (!u) return "";
		return String(u).replace(/"/g, "%22").replace(/</g, "%3C").replace(/`/g, "%60");
	}

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

	function fmt_date(val) {
		if (!val) return "—";
		try {
			return frappe.datetime.str_to_user(val);
		} catch (e) {
			return esc(String(val));
		}
	}

	function fmt_datetime(val) {
		if (!val) return "—";
		if (autods.service_datetime && autods.service_datetime.format_system_datetime) {
			return esc(autods.service_datetime.format_system_datetime(val));
		}
		try {
			return frappe.datetime.str_to_user(val, true);
		} catch (e) {
			return esc(String(val));
		}
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
							msg && msg.description ? String(msg.description).trim() : "",
					});
				}
			);
		});
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
							["employee_name", "image"],
							(msg) => resolve({ id, msg: msg || {} })
						);
					})
			)
		);
		const out = {};
		rows.forEach(({ id, msg }) => {
			out[id] = {
				employee_name: msg.employee_name || id,
				image: msg.image || "",
			};
		});
		return out;
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

	function jc_work_completion_pct(jc) {
		const rows = jc.work_details || [];
		if (!rows.length) return jc_progress_pct(jc.status);
		const done = rows.filter((r) => r.status === "Completed").length;
		return Math.round((done / rows.length) * 100);
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

	function render_tech_avatar_with_overlays(emp, technicianId, start_disabled, end_disabled) {
		const name =
			(emp && emp.employee_name && String(emp.employee_name).trim()) ||
			(technicianId && String(technicianId).trim()) ||
			"";
		const initial = name ? name.charAt(0).toUpperCase() : "?";
		const imgSrc = emp && emp.image ? file_to_img_src(emp.image) : "";
		const inner = imgSrc
			? `<img class="autods-jc-tech-img" src="${attr_url(imgSrc)}" alt="" />`
			: name || technicianId
				? `<span class="autods-jc-tech-ph">${esc(initial)}</span>`
				: `<i class="fa fa-user-circle autods-jc-tech-icon" aria-hidden="true"></i>`;
		const title = name || technicianId || __("Technician");
		const startTitle = esc(__("Start job timer"));
		const endTitle = esc(__("End job timer"));
		return `<div class="autods-jc-tech-photo-wrap" title="${esc(title)}">
			<div class="autods-jc-tech-photo">${inner}</div>
			<div class="autods-jc-tech-photo-overlay">
				<button type="button" class="autods-jc-overlay-btn autods-jc-overlay-start" data-autods-jc-start ${start_disabled ? "disabled" : ""} title="${startTitle}">
					<i class="fa fa-play" aria-hidden="true"></i>
					<span class="sr-only">${esc(__("Start"))}</span>
				</button>
				<button type="button" class="autods-jc-overlay-btn autods-jc-overlay-end" data-autods-jc-end ${end_disabled ? "disabled" : ""} title="${endTitle}">
					<i class="fa fa-stop" aria-hidden="true"></i>
					<span class="sr-only">${esc(__("End"))}</span>
				</button>
			</div>
		</div>`;
	}

	function parse_doc_datetime_ms(val) {
		if (!val) return null;
		if (window.moment && autods.service_datetime && autods.service_datetime.get_system_timezone) {
			try {
				const system_tz = autods.service_datetime.get_system_timezone();
				let m = moment.tz(val, frappe.defaultDatetimeFormat, system_tz);
				if (!m.isValid()) {
					m = moment.tz(val, system_tz);
				}
				if (m.isValid()) return m.valueOf();
			} catch (e) {
				/* fall through */
			}
		}
		if (window.moment) {
			try {
				const m = moment(
					val,
					[frappe.defaultDatetimeFormat, "YYYY-MM-DD HH:mm:ss", moment.ISO_8601].filter(
						Boolean
					),
					true
				);
				if (m.isValid()) return m.valueOf();
				const m2 = moment(val);
				if (m2.isValid()) return m2.valueOf();
			} catch (e) {
				/* fall through */
			}
		}
		const x = Date.parse(String(val).replace(" ", "T"));
		return Number.isNaN(x) ? null : x;
	}

	function format_elapsed_hms(ms) {
		const sec = Math.max(0, Math.floor(ms / 1000));
		const h = Math.floor(sec / 3600);
		const m = Math.floor((sec % 3600) / 60);
		const s = sec % 60;
		if (h > 0) {
			return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
		}
		return `${m}:${String(s).padStart(2, "0")}`;
	}

	function spareparts_status_class(st) {
		const t = (st || "").trim();
		if (t === "Issued") return "autods-jc-sp-status--ok";
		if (t === "Approved") return "autods-jc-sp-status--info";
		if (t === "Rejected" || t === "Cancelled") return "autods-jc-sp-status--bad";
		return "autods-jc-sp-status--pending";
	}

	function render_work_detail_cards(rows) {
		if (!rows.length) {
			return `<p class="autods-sa-muted">${esc(__("No work detail lines yet."))}</p>`;
		}
		const body = rows
			.map((r, i) => {
				const idx = r.idx != null && r.idx !== "" ? String(r.idx) : String(i + 1);
				const title = r.work_description || __("Work line");
				return `<div class="autods-sa-insp-row-card">
					<div class="autods-sa-insp-row-card-header">
						<span class="autods-sa-insp-row-title">${esc(idx)}. ${esc(title)}</span>
						<span class="autods-sa-insp-row-meta">${esc(r.status || "—")} · ${esc(
					String(r.hours_spent != null ? r.hours_spent : "—")
				)} ${esc(__("h"))}</span>
					</div>
					${r.notes ? `<p class="autods-sa-insp-remarks">${esc(r.notes)}</p>` : ""}
				</div>`;
			})
			.join("");
		return `<div class="autods-sa-insp-row-stack">${body}</div>
			<p class="autods-sa-cc-actions">
				<button type="button" class="autods-sa-insp-edit-btn" data-autods-jc-focus="work_details">${esc(
					__("Edit work details")
				)}</button>
			</p>`;
	}

	function render_spareparts_cards(rows) {
		if (!rows.length) {
			return `<p class="autods-sa-muted">${esc(__("No spareparts request lines yet."))}</p>`;
		}
		const body = rows
			.map((r) => {
				const line =
					[r.item_code, r.item_name].filter(Boolean).join(" — ") || "—";
				const se = r.stock_entry
					? `<a class="autods-sa-text-link" href="${attr_url(
							frappe.utils.get_form_link("Stock Entry", r.stock_entry)
					  )}">${esc(r.stock_entry)}</a>`
					: "—";
				const spr = r.spareparts_request
					? `<a class="autods-sa-text-link" href="${attr_url(
							frappe.utils.get_form_link("Spareparts Request", r.spareparts_request)
					  )}">${esc(r.spareparts_request)}</a>`
					: "—";
				return `<div class="autods-sa-insp-row-card autods-jc-sp-card">
					<div class="autods-sa-insp-row-quality-top">
						<span class="autods-sa-insp-row-title">${esc(line)}</span>
						<span class="autods-jc-sp-status ${spareparts_status_class(
							r.status
						)}">${esc(r.status || __("Requested"))}</span>
					</div>
					<div class="autods-sa-insp-kv-mini" style="margin-top:0.5rem">
						<div><span>${esc(__("Qty"))}</span><strong>${esc(
					String(r.qty != null ? r.qty : "—")
				)} ${esc(r.uom || "")}</strong></div>
						<div><span>${esc(__("Requested"))}</span><strong>${esc(
					fmt_datetime(r.requested_date)
				)}</strong></div>
						<div><span>${esc(__("Stock entry"))}</span><strong>${se}</strong></div>
						<div><span>${esc(__("Spareparts request"))}</span><strong>${spr}</strong></div>
					</div>
					${r.notes ? `<p class="autods-sa-insp-remarks" style="margin-top:0.5rem">${esc(r.notes)}</p>` : ""}
				</div>`;
			})
			.join("");
		return `<div class="autods-sa-insp-row-stack">${body}</div>`;
	}

	function clear_jc_dash_timer(frm) {
		if (frm && frm.__autods_jc_dash_timer) {
			clearInterval(frm.__autods_jc_dash_timer);
			frm.__autods_jc_dash_timer = null;
		}
	}

	function update_timer_ui(frm) {
		const $w = frm.fields_dict.dashboard_html && frm.fields_dict.dashboard_html.$wrapper;
		if (!$w || !$w.length) return;
		const $box = $w.find("#autods-jc-timer-box");
		if (!$box.length) return;
		const d = frm.doc;
		const $main = $w.find("#autods-jc-timer-main");
		const $sub = $w.find("#autods-jc-timer-sub");
		const expectedMs = parse_doc_datetime_ms(d.expected_completion_date);
		const now = Date.now();
		const terminal = d.status === "Completed" || d.status === "Cancelled";
		const delayed =
			!terminal &&
			expectedMs != null &&
			now > expectedMs &&
			d.status !== "Completed";

		let ringColor = donut_color(jc_work_completion_pct(d));
		if (delayed) ringColor = RED_D;
		if (terminal && d.status === "Completed") ringColor = GREEN;
		if (terminal && d.status === "Cancelled") ringColor = GRAY_RING;

		const $rings = $w.find(".autods-sa-donut > g > circle");
		const $ring = $rings.eq(1);
		if ($ring.length) {
			$ring.attr("stroke", ringColor);
		}

		$box.toggleClass("autods-jc-timer--delayed", !!delayed);

		if (terminal) {
			const startMs = parse_doc_datetime_ms(d.start_time);
			const endMs = parse_doc_datetime_ms(d.end_time);
			if (startMs != null && endMs != null) {
				$main.text(format_elapsed_hms(endMs - startMs));
				$sub.text(__("Total time"));
			} else {
				$main.text(d.status || "—");
				$sub.text("");
			}
			return;
		}

		const startMs = parse_doc_datetime_ms(d.start_time);
		if (startMs == null) {
			$main.text(__("—"));
			$sub.text(__("Press Start to begin timer"));
			return;
		}

		const endMs = parse_doc_datetime_ms(d.end_time);
		const refEnd = endMs != null ? endMs : now;
		$main.text(format_elapsed_hms(refEnd - startMs));
		if (delayed) {
			$sub.text(__("Delayed — past expected completion"));
		} else if (expectedMs != null) {
			$sub.text(`${__("Due")} ${fmt_datetime(d.expected_completion_date)}`);
		} else {
			$sub.text(__("Elapsed"));
		}
	}

	function bind_job_card_dashboard_ui(fld, frm) {
		const $root = fld.$wrapper.find(".autods-jc-dash");
		clear_jc_dash_timer(frm);

		$root
			.off("click.autodsJcDash")
			.on("click.autodsJcDash", "[data-autods-tab]", function () {
				const tab = $(this).data("autods-tab");
				$root.find("[data-autods-tab]").removeClass("autods-sa-tab--active");
				$(this).addClass("autods-sa-tab--active");
				$root.find(".autods-sa-panel").removeClass("autods-sa-panel--active");
				$root.find(`.autods-sa-panel[data-autods-panel="${tab}"]`).addClass("autods-sa-panel--active");
			})
			.on("click.autodsJcDash", "[data-autods-jc-focus]", function (e) {
				e.preventDefault();
				const fieldname = $(this).attr("data-autods-jc-focus");
				if (frm && fieldname && frm.fields_dict[fieldname]) {
					frm.scroll_to_field(fieldname, true);
				}
			})
			.on("click.autodsJcDash", "[data-autods-jc-start]", function (e) {
				e.preventDefault();
				jc_action_start(frm);
			})
			.on("click.autodsJcDash", "[data-autods-jc-end]", function (e) {
				e.preventDefault();
				jc_action_end(frm);
			});

		const d = frm.doc;
		const need_tick =
			d.start_time &&
			!d.end_time &&
			d.status !== "Completed" &&
			d.status !== "Cancelled";
		if (need_tick) {
			update_timer_ui(frm);
			frm.__autods_jc_dash_timer = setInterval(function () {
				update_timer_ui(frm);
			}, 1000);
		} else {
			update_timer_ui(frm);
		}
	}

	function jc_action_start(frm) {
		const st = frm.doc.status;
		if (st === "Completed" || st === "Cancelled") {
			frappe.msgprint(__("This job cannot be started."));
			return;
		}
		if (frm.doc.start_time && !frm.doc.end_time) {
			frappe.msgprint(__("Timer is already running."));
			return;
		}
		if (frm.doc.start_time && frm.doc.end_time) {
			frappe.msgprint(
				__(
					"Start and end times are already set. Clear them on the Time Tracking tab if you need to restart."
				)
			);
			return;
		}
		frm.set_value("start_time", frappe.datetime.now_datetime());
		if (frm.doc.status === "Open") {
			frm.set_value("status", "Work In Progress");
		}
		frm.save(null, () => render_job_card_dashboard(frm));
	}

	function jc_action_end(frm) {
		if (!frm.doc.start_time) {
			frappe.msgprint(__("Start the job first."));
			return;
		}
		if (frm.doc.end_time) {
			frappe.msgprint(__("End time is already set."));
			return;
		}
		frm.set_value("end_time", frappe.datetime.now_datetime());
		frm.save(null, () => render_job_card_dashboard(frm));
	}

	async function render_job_card_dashboard(frm) {
		const fld = frm.fields_dict.dashboard_html;
		if (!fld || !fld.$wrapper) return;
		clear_jc_dash_timer(frm);

		if (frm.is_new()) {
			fld.$wrapper.html(
				`<p class="text-muted" style="padding:1rem 0">${esc(
					__("Save the Job Card to open the dashboard.")
				)}</p>`
			);
			return;
		}

		const d = frm.doc;
		const plate = d.plate_no || __("Plate");

		const [vu, emp_map, custMsg] = await Promise.all([
			fetch_vehicle_unit_header_fields(d.vehicle_unit),
			fetch_employees_map([d.technician]),
			d.customer ? db_get_value_fields("Customer", d.customer, "customer_name") : Promise.resolve(null),
		]);

		const imgUrl = vu.image ? file_to_img_src(vu.image) : "";
		const img_block = imgUrl
			? `<div class="autods-sa-photo"><img src="${attr_url(imgUrl)}" alt="" /></div>`
			: `<div class="autods-sa-photo autods-sa-photo--empty"><span>${esc(
					__("No vehicle photo")
			  )}</span></div>`;

		const customer_display =
			custMsg && custMsg.customer_name ? String(custMsg.customer_name).trim() : d.customer || "";
		const tech_id = d.technician;
		const tech_display =
			tech_id && emp_map[tech_id] ? emp_map[tech_id].employee_name || tech_id : tech_id || "";

		const workRows = d.work_details || [];
		const spRows = d.spareparts_requests || [];
		const badge = (n, blue) =>
			n > 0
				? `<span class="autods-sa-badge${blue ? " autods-sa-badge--blue" : ""}">${esc(
						String(Math.min(99, n))
				  )}</span>`
				: "";

		const jc_pct = jc_work_completion_pct(d);
		const expectedMs = parse_doc_datetime_ms(d.expected_completion_date);
		const now = Date.now();
		const delayed_preview =
			d.status !== "Completed" &&
			d.status !== "Cancelled" &&
			expectedMs != null &&
			now > expectedMs;
		let ringColor = donut_color(jc_pct);
		if (delayed_preview) ringColor = RED_D;
		if (d.status === "Completed") ringColor = GREEN;
		if (d.status === "Cancelled") ringColor = GRAY_RING;

		const timer_main_initial = "—";
		const timer_sub_initial =
			d.start_time && !d.end_time ? __("Elapsed") : __("Press Start to begin timer");

		function meta_line(faIcon, title, valueHtml) {
			const t = esc(title);
			return `<div class="autods-sa-meta-line" title="${t}">
					<i class="fa ${faIcon} autods-sa-meta-icon" aria-hidden="true"></i>
					<span class="autods-sa-meta-value"><span class="sr-only">${t}: </span>${valueHtml}</span>
				</div>`;
		}
		const ro_header_val = esc(d.repair_order || "—");
		const tech_header_val = esc(tech_display || tech_id || "—");
		const header_meta_inner = [
			meta_line("fa-user", __("Customer"), esc(customer_display || d.customer || "—")),
			meta_line("fa-file-text-o", __("Repair order"), ro_header_val),
			meta_line("fa-tachometer", __("Status"), esc(d.status || "—")),
			meta_line("fa-map-marker", __("Work area"), esc(d.work_area || "—")),
			meta_line("fa-calendar", __("Repair date"), esc(fmt_date(d.repair_date))),
			meta_line("fa-black-tie", __("Technician"), tech_header_val),
		].join("");
		const header_meta_html = `<div class="autods-sa-header-meta"><div class="autods-sa-meta-grid">${header_meta_inner}</div></div>`;

		const start_disabled =
			d.status === "Completed" || d.status === "Cancelled" || (d.start_time && !d.end_time);
		const end_disabled =
			d.status === "Completed" ||
			d.status === "Cancelled" ||
			!d.start_time ||
			!!d.end_time;

		const html = `
<style>
.autods-jc-dash.autods-sa {
	font-family: "Inter", "Segoe UI", system-ui, sans-serif;
	color: #333333;
	background: ${BG_MUTED};
	border-radius: 12px;
	overflow: hidden;
	max-width: 1100px;
	width: 100%;
	margin: 0 auto 2.5rem;
	box-sizing: border-box;
	-webkit-tap-highlight-color: transparent;
}
.autods-jc-dash.autods-sa * { box-sizing: border-box; }
.autods-jc-dash .autods-sa-top {
	background: ${HEADER_BG};
	padding: 1.35rem 1.5rem 0;
}
.autods-jc-dash .autods-sa-head {
	display: flex;
	align-items: flex-end;
	gap: 1.5rem;
	flex-wrap: wrap;
	margin-bottom: 0;
	width: 100%;
	padding-bottom: 0.35rem;
}
.autods-jc-dash .autods-sa-body { padding: 1rem 1.5rem 1.5rem; background: ${BG_MUTED}; }
.autods-jc-dash .autods-sa-photo {
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
	overflow: visible;
}
.autods-jc-dash .autods-sa-photo img {
	max-width: 100%;
	max-height: 132px;
	width: auto;
	height: auto;
	object-fit: contain;
	object-position: center bottom;
	display: block;
}
.autods-jc-dash .autods-sa-photo--empty {
	width: 160px;
	min-height: 88px;
	color: #6c757d;
	font-size: 0.75rem;
	text-align: center;
	padding: 0.75rem 0.5rem;
	background: transparent;
	border: none;
}
.autods-jc-dash .autods-sa-title-block {
	flex: 1;
	min-width: 200px;
	align-self: center;
	padding-bottom: 0.5rem;
}
.autods-jc-dash .autods-sa-title-block h1 {
	margin: 0 0 0.35rem;
	font-size: 1.35rem;
	font-weight: 700;
	letter-spacing: -0.02em;
	line-height: 1.25;
	color: #333333;
}
.autods-jc-dash .autods-jc-dash-subtitle {
	margin: 0 0 0.35rem;
	font-size: 0.8rem;
	line-height: 1.45;
	color: #868e96;
	font-weight: 500;
	max-width: 52rem;
}
.autods-jc-dash .autods-jc-dash-subtitle strong {
	font-weight: 600;
	color: #868e96;
}
.autods-jc-dash .autods-sa-header-meta {
	font-size: 0.8rem;
	line-height: 1.45;
	color: #868e96;
	max-width: 52rem;
}
.autods-jc-dash .autods-sa-meta-grid {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 0.4rem 1.25rem;
	align-items: start;
}
.autods-jc-dash .autods-sa-meta-line {
	display: flex;
	gap: 0.45rem;
	align-items: flex-start;
	margin: 0;
	min-width: 0;
}
.autods-jc-dash .autods-sa-meta-icon {
	flex-shrink: 0;
	width: 1.1rem;
	text-align: center;
	color: #868e96;
	font-size: 0.85rem;
	line-height: 1.35;
	margin-top: 0.12em;
}
.autods-jc-dash .autods-sa-meta-value {
	font-weight: 500;
	color: #868e96;
	min-width: 0;
	flex: 1 1 auto;
	word-break: break-word;
}
.autods-jc-dash .autods-sa-gauge {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: flex-end;
	align-self: center;
	min-width: 118px;
	max-width: 9.5rem;
	margin-bottom: 0.25rem;
}
.autods-jc-dash .autods-jc-gauge-visual { flex-shrink: 0; }
.autods-jc-dash .autods-sa-gauge-ring { position: relative; width: 112px; height: 112px; flex-shrink: 0; }
.autods-jc-dash .autods-sa-gauge-ring .autods-sa-donut {
	width: 112px;
	height: 112px;
	display: block;
}
.autods-jc-dash .autods-sa-gauge-ring > svg {
	display: block;
	position: absolute;
	top: 0;
	left: 0;
	pointer-events: none;
}
.autods-jc-dash .autods-sa-gauge-inner.autods-jc-gauge-avatar-only {
	position: absolute;
	inset: 0;
	z-index: 1;
	display: flex;
	align-items: center;
	justify-content: center;
	text-align: center;
	padding: 0;
	pointer-events: auto;
}
.autods-jc-dash .autods-jc-tech-photo-wrap {
	position: relative;
	width: 62px;
	height: 62px;
	border-radius: 50%;
	overflow: hidden;
	flex-shrink: 0;
	box-shadow: 0 0 0 2px #fff;
}
.autods-jc-dash .autods-jc-tech-photo {
	position: absolute;
	inset: 0;
	width: 100%;
	height: 100%;
	border-radius: 50%;
	overflow: hidden;
	background: #e9ecef;
	display: flex;
	align-items: center;
	justify-content: center;
}
.autods-jc-dash .autods-jc-tech-photo-overlay {
	position: absolute;
	left: 0;
	right: 0;
	bottom: 0;
	top: 0;
	display: flex;
	align-items: flex-end;
	justify-content: center;
	gap: 3px;
	padding: 0 5px 5px;
	pointer-events: none;
	z-index: 2;
}
.autods-jc-dash .autods-jc-overlay-btn {
	pointer-events: auto;
	width: 22px;
	height: 22px;
	min-width: 22px;
	min-height: 22px;
	padding: 0;
	border: none;
	border-radius: 50%;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	touch-action: manipulation;
	font-size: 9px;
	line-height: 1;
	color: #fff;
	background: rgba(33, 37, 41, 0.48);
	box-shadow: 0 1px 3px rgba(0,0,0,0.2);
	transition: background 0.15s ease, transform 0.1s ease;
}
.autods-jc-dash .autods-jc-overlay-btn:hover:not(:disabled) {
	background: rgba(33, 37, 41, 0.72);
	transform: scale(1.06);
}
.autods-jc-dash .autods-jc-overlay-start:hover:not(:disabled) {
	background: rgba(40, 167, 69, 0.55);
}
.autods-jc-dash .autods-jc-overlay-end:hover:not(:disabled) {
	background: rgba(220, 53, 69, 0.5);
}
.autods-jc-dash .autods-jc-overlay-btn:disabled {
	opacity: 0.32;
	cursor: not-allowed;
	transform: none;
	pointer-events: none;
}
.autods-jc-dash .autods-jc-overlay-btn .fa {
	margin-left: 1px;
}
.autods-jc-dash .autods-jc-overlay-end .fa {
	margin-left: 0;
}
.autods-jc-dash .autods-jc-tech-img {
	width: 100%;
	height: 100%;
	object-fit: cover;
	display: block;
}
.autods-jc-dash .autods-jc-tech-ph {
	font-size: 1.35rem;
	font-weight: 700;
	color: #495057;
	line-height: 1;
}
.autods-jc-dash .autods-jc-tech-icon {
	font-size: 2.25rem;
	color: #adb5bd;
	line-height: 1;
}
.autods-jc-dash .autods-jc-timer-below {
	text-align: center;
	margin-top: 0.4rem;
	width: 100%;
	max-width: 10rem;
}
.autods-jc-dash .autods-jc-timer-below .autods-sa-gauge-pct {
	font-size: 1.05rem;
	font-weight: 700;
	color: #212529;
	line-height: 1.15;
	margin: 0;
	font-variant-numeric: tabular-nums;
}
.autods-jc-dash .autods-jc-timer--delayed .autods-sa-gauge-pct { color: ${RED_D}; }
.autods-jc-dash .autods-jc-timer-below .autods-sa-gauge-sub {
	font-size: 0.62rem;
	color: #6c757d;
	margin: 0.1rem 0 0;
	max-width: 92px;
	margin-left: auto;
	margin-right: auto;
	line-height: 1.25;
}
.autods-jc-dash .autods-jc-timer--delayed .autods-sa-gauge-sub { color: ${RED_D}; font-weight: 600; }
.autods-jc-dash .autods-sa-tabs {
	display: flex;
	flex-wrap: wrap;
	gap: 0.25rem 1.25rem;
	border-bottom: 1px solid #dee2e6;
	margin: 0 -1.5rem;
	padding: 0.35rem 1.5rem 0;
	background: ${HEADER_BG};
}
.autods-jc-dash .autods-sa-tab {
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
	touch-action: manipulation;
}
.autods-jc-dash .autods-sa-tab--active { color: #212529; }
.autods-jc-dash .autods-sa-tab--active::after {
	content: "";
	position: absolute;
	left: 0;
	right: 0;
	bottom: 0;
	height: 2px;
	background: #212529;
	border-radius: 2px 2px 0 0;
}
.autods-jc-dash .autods-sa-shell { display: flex; flex-direction: column; gap: 0; }
.autods-jc-dash .autods-sa-panel { display: none; padding-top: 1rem; }
.autods-jc-dash .autods-sa-panel--active { display: block; }
.autods-jc-dash .autods-sa-kv-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
	gap: 0.75rem 1.25rem;
}
.autods-jc-dash .autods-sa-kv span {
	display: block;
	font-size: 0.72rem;
	color: #868e96;
	text-transform: uppercase;
	letter-spacing: 0.03em;
	margin-bottom: 0.2rem;
}
.autods-jc-dash .autods-sa-kv strong { font-size: 0.9rem; font-weight: 600; color: #212529; }
.autods-jc-dash .autods-sa-text-link { color: ${BLUE_BADGE}; text-decoration: none; font-weight: 500; font-size: 0.9rem; }
.autods-jc-dash .autods-sa-text-link:hover { text-decoration: underline; }
.autods-jc-dash .autods-sa-muted { color: #868e96; font-size: 0.9rem; margin: 0; }
.autods-jc-dash .autods-sa-insp-row-stack { display: flex; flex-direction: column; gap: 0.65rem; }
.autods-jc-dash .autods-sa-insp-row-card {
	background: #fff;
	border: 1px solid #e9ecef;
	border-radius: 10px;
	padding: 0.75rem 1rem;
	box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.autods-jc-dash .autods-sa-insp-row-card-header { display: flex; flex-direction: column; align-items: flex-start; gap: 0.25rem; }
.autods-jc-dash .autods-sa-insp-row-title { font-weight: 600; font-size: 0.9rem; color: #212529; }
.autods-jc-dash .autods-sa-insp-row-meta { font-size: 0.78rem; color: #6c757d; }
.autods-jc-dash .autods-sa-insp-remarks {
	margin: 0.35rem 0 0;
	font-size: 0.82rem;
	line-height: 1.45;
	color: #333;
	white-space: pre-wrap;
	word-break: break-word;
}
.autods-jc-dash .autods-sa-insp-kv-mini {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
	gap: 0.5rem 1rem;
	font-size: 0.78rem;
}
.autods-jc-dash .autods-sa-insp-kv-mini span {
	display: block;
	font-size: 0.65rem;
	color: #868e96;
	text-transform: uppercase;
	letter-spacing: 0.03em;
	margin-bottom: 0.15rem;
}
.autods-jc-dash .autods-sa-insp-kv-mini strong { font-weight: 600; color: #212529; word-break: break-word; }
.autods-jc-dash .autods-sa-insp-edit-btn {
	flex-shrink: 0;
	border: 1px solid ${BLUE_BADGE};
	background: #fff;
	color: ${BLUE_BADGE};
	font-size: 0.72rem;
	font-weight: 600;
	padding: 0.5rem 0.85rem;
	min-height: 44px;
	border-radius: 6px;
	cursor: pointer;
	touch-action: manipulation;
	text-transform: uppercase;
	letter-spacing: 0.03em;
}
.autods-jc-dash .autods-sa-insp-edit-btn:hover { background: ${BLUE_BADGE}; color: #fff; }
.autods-jc-dash .autods-sa-cc-actions { margin: 1rem 0 0; }
.autods-jc-dash .autods-jc-sp-status {
	font-size: 0.72rem;
	font-weight: 700;
	padding: 0.2rem 0.5rem;
	border-radius: 6px;
	text-transform: uppercase;
	letter-spacing: 0.04em;
}
.autods-jc-dash .autods-jc-sp-status--pending { background: #fff3cd; color: #856404; }
.autods-jc-dash .autods-jc-sp-status--info { background: #cce5ff; color: #004085; }
.autods-jc-dash .autods-jc-sp-status--ok { background: #d4edda; color: #155724; }
.autods-jc-dash .autods-jc-sp-status--bad { background: #f8d7da; color: #721c24; }
.autods-jc-dash .autods-sa-badge {
	font-size: 0.65rem;
	font-weight: 700;
	min-width: 1.1rem;
	padding: 0.1rem 0.35rem;
	border-radius: 8px;
	background: #e9ecef;
	color: #495057;
	line-height: 1.2;
}
.autods-jc-dash .autods-sa-badge--blue { background: #cce5ff; color: #004085; }

@media (max-width: 768px) {
	.autods-jc-dash.autods-sa {
		border-radius: 10px;
		margin-bottom: 1.25rem;
	}
	.autods-jc-dash .autods-sa-top {
		padding: 1rem max(1rem, env(safe-area-inset-right, 0px)) 0 max(1rem, env(safe-area-inset-left, 0px));
	}
	.autods-jc-dash .autods-sa-head {
		flex-direction: column;
		align-items: stretch;
		gap: 1rem;
	}
	.autods-jc-dash .autods-sa-photo {
		width: 100%;
		max-width: 260px;
		min-height: 88px;
		margin: 0 auto;
	}
	.autods-jc-dash .autods-sa-title-block {
		min-width: 0;
		width: 100%;
		text-align: center;
		padding-bottom: 0;
	}
	.autods-jc-dash .autods-sa-meta-grid {
		grid-template-columns: 1fr;
	}
	.autods-jc-dash .autods-sa-gauge {
		align-self: center;
		margin: 0.25rem auto 0;
		max-width: 100%;
	}
	.autods-jc-dash .autods-sa-tabs {
		margin: 0 -1rem;
		padding-left: 1rem;
		padding-right: 1rem;
		flex-wrap: nowrap;
		overflow-x: auto;
		overflow-y: hidden;
		-webkit-overflow-scrolling: touch;
		scrollbar-width: thin;
		overscroll-behavior-x: contain;
		gap: 0.25rem 0.75rem;
	}
	.autods-jc-dash .autods-sa-tab {
		flex-shrink: 0;
		white-space: nowrap;
		min-height: 44px;
		padding-left: 0.45rem;
		padding-right: 0.45rem;
	}
	.autods-jc-dash .autods-sa-body {
		padding: 0.85rem max(1rem, env(safe-area-inset-right, 0px)) max(1.25rem, env(safe-area-inset-bottom, 0px)) max(1rem, env(safe-area-inset-left, 0px));
	}
	.autods-jc-dash .autods-sa-insp-kv-mini {
		grid-template-columns: 1fr;
	}
	.autods-jc-dash .autods-sa-insp-row-card {
		padding: 0.85rem 0.9rem;
	}
}

@media (max-width: 480px) {
	.autods-jc-dash .autods-sa-title-block h1 {
		font-size: 1.2rem;
		word-break: break-word;
	}
	.autods-jc-dash .autods-sa-gauge-ring {
		width: 120px;
		height: 120px;
	}
	.autods-jc-dash .autods-sa-gauge-ring .autods-sa-donut {
		width: 120px;
		height: 120px;
	}
	.autods-jc-dash .autods-jc-tech-photo-wrap {
		width: 72px;
		height: 72px;
	}
	.autods-jc-dash .autods-jc-overlay-btn {
		width: 30px;
		height: 30px;
		min-width: 30px;
		min-height: 30px;
		font-size: 11px;
	}
	.autods-jc-dash .autods-jc-tech-photo-overlay {
		padding: 0 6px 6px;
		gap: 5px;
	}
	.autods-jc-dash .autods-jc-timer-below {
		max-width: 100%;
		padding: 0 0.25rem;
	}
	.autods-jc-dash .autods-jc-timer-below .autods-sa-gauge-pct {
		font-size: 1.05rem;
	}
	.autods-jc-dash .autods-jc-timer-below .autods-sa-gauge-sub {
		font-size: 0.68rem;
		max-width: 16rem;
	}
	.autods-jc-dash .autods-sa-tab {
		font-size: 0.68rem;
		padding-left: 0.4rem;
		padding-right: 0.4rem;
	}
}
</style>
<div class="autods-sa autods-jc-dash">
	<div class="autods-sa-top">
		<div class="autods-sa-head">
			${img_block}
			<div class="autods-sa-title-block">
				<h1>${esc(plate)}</h1>
				<p class="autods-jc-dash-subtitle">${esc(__("Job Card"))} · <strong>${esc(d.name)}</strong></p>
				${header_meta_html}
			</div>
			<div class="autods-sa-gauge autods-jc-status-gauge">
				<div class="autods-jc-gauge-visual">
					<div class="autods-sa-gauge-ring">
						${donut_svg(jc_pct, ringColor)}
						<div class="autods-sa-gauge-inner autods-jc-gauge-avatar-only">
							${render_tech_avatar_with_overlays(
								tech_id && emp_map[tech_id] ? emp_map[tech_id] : null,
								tech_id,
								start_disabled,
								end_disabled
							)}
						</div>
					</div>
				</div>
				<div id="autods-jc-timer-box" class="autods-jc-timer-below">
					<p id="autods-jc-timer-main" class="autods-sa-gauge-pct">${esc(timer_main_initial)}</p>
					<div id="autods-jc-timer-sub" class="autods-sa-gauge-sub">${esc(timer_sub_initial)}</div>
				</div>
			</div>
		</div>
		<div class="autods-sa-tabs">
			<button type="button" class="autods-sa-tab autods-sa-tab--active" data-autods-tab="work">${esc(
				__("Work Details")
			)}${badge(workRows.length, true)}</button>
			<button type="button" class="autods-sa-tab" data-autods-tab="spareparts">${esc(
				__("Spareparts")
			)}${badge(spRows.length, true)}</button>
		</div>
	</div>
	<div class="autods-sa-body">
		<div class="autods-sa-shell">
			<div class="autods-sa-panel autods-sa-panel--active" data-autods-panel="work">
				${render_work_detail_cards(workRows)}
			</div>
			<div class="autods-sa-panel" data-autods-panel="spareparts">
				${render_spareparts_cards(spRows)}
			</div>
		</div>
	</div>
</div>`;

		fld.$wrapper.empty().html(html);
		bind_job_card_dashboard_ui(fld, frm);
	}

	const refresh_fields = [
		"repair_order",
		"customer",
		"vehicle_unit",
		"plate_no",
		"repair_date",
		"expected_completion_date",
		"actual_completion_date",
		"status",
		"work_area",
		"technician",
		"technician_skills_group",
		"repair_type",
		"planning_summary",
		"start_time",
		"end_time",
		"total_hours",
		"work_details",
		"spareparts_requests",
	];

	function jc_dash_refresh(frm) {
		render_job_card_dashboard(frm);
	}

	const jc_dash_handlers = {
		refresh: jc_dash_refresh,
		work_details_add: jc_dash_refresh,
		work_details_remove: jc_dash_refresh,
		spareparts_requests_add: jc_dash_refresh,
		spareparts_requests_remove: jc_dash_refresh,
	};
	refresh_fields.forEach(function (fn) {
		jc_dash_handlers[fn] = jc_dash_refresh;
	});

	frappe.ui.form.on("Job Card", jc_dash_handlers);
})();
