# Repair Order (RO) dashboard — CSS style summary

This document summarizes the visual system used by the **service advisor dashboard** rendered on Repair Order, Repair Estimate, and Service Appointment forms. Use it when re‑implementing the same look in another app or extracting styles into shared CSS.

## Source files

| File | Role |
|------|------|
| `autods/public/js/repair_service_dashboard.js` | **Canonical styles.** A `<style>` block is injected with the dashboard HTML (search for ``const html = \`<style>``). Class prefix: `.autods-sa` |
| `autods/public/js/job_card_dashboard.js` | **Same tokens and patterns**, scoped under `.autods-jc-dash` so rules apply only inside the Job Card shopfloor dashboard. Adds timer/technician overlay styles (`.autods-jc-*`). |

There is no separate `.css` file; styles are embedded in JS template strings. Constants at the top of each file define shared colors.

---

## Design tokens (JavaScript constants → use as CSS variables elsewhere)

These are the values referenced inside the injected `<style>` blocks:

| Token (JS name) | Hex | Usage |
|-----------------|-----|--------|
| `GREEN` | `#28a745` | Success / current job card border, positive hints, high completion on donut |
| `AMBER` | `#ffc107` | Mid completion on progress ring |
| `RED_D` | `#dc3545` | Low completion, delayed timer states |
| `GRAY_RING` | `#868e96` | Neutral ring segment |
| `BLUE_BADGE` | `#007bff` | Primary actions, links, numbered concern index, outline buttons |
| `BG_MUTED` | `#F4F7F9` | Page background behind the white “shell” |
| `HEADER_BG` | `#ffffff` | Header strip and tab bar background |

**Bootstrap‑aligned grays** (hard‑coded in CSS, not variables in JS):

- Text primary: `#333333`, `#212529`
- Secondary / labels: `#868e96`, `#6c757d`, `#495057`, `#adb5bd`
- Borders / dividers: `#dee2e6`, `#e9ecef`, `#f1f3f5`
- Light fills: `#f8f9fa`, `#fafbfc`, `#e9ecef`
- Accent text (service titles): `#3d5a6c`

**Elevation:** `box-shadow: 0 1px 2px rgba(0,0,0,0.04)` on cards and shell; concern index uses `0 1px 3px rgba(0, 123, 255, 0.35)`.

---

## Typography

- **Stack:** `"Inter", "Segoe UI", system-ui, sans-serif`
- **Page title (plate / headline):** `1.35rem`, weight `700`, letter-spacing `-0.02em`, line-height `1.25`, color `#333333`
- **Section / panel labels:** Uppercase micro‑labels — `0.62rem`–`0.78rem`, weight `600`–`700`, letter-spacing `0.03em`–`0.06em`, color `#868e96` or `#495057`
- **Tabs:** `0.72rem`, weight `600`, letter-spacing `0.06em`; inactive `#868e96`, active `#212529` with `3px` bottom bar (`#212529`, radius `2px 2px 0 0`) — Job Card variant uses `2px` underline
- **Body / tables:** `0.78rem`–`0.9rem` with comfortable line-height (`1.35`–`1.45`)

---

## Layout structure

Rough DOM / region model (class names):

1. **Root** `.autods-sa` — max-width `1100px`, centered (`margin: 0 auto 2.5rem`), `border-radius: 12px`, `overflow: hidden`, `background: BG_MUTED`
2. **Top** `.autods-sa-top` — white background, padding `1.35rem 1.5rem 0`
3. **Head row** `.autods-sa-head` — flex, `align-items: flex-end`, `gap: 1.5rem`, wrap; contains vehicle photo, title block, optional gauge
4. **Tabs** `.autods-sa-tabs` — flex wrap, bottom border `#dee2e6`, negative horizontal margin to align with top padding
5. **Body** `.autods-sa-body` — muted background, padding `1rem 1.5rem 1.5rem`
6. **Content shell** `.autods-sa-shell` — white card: `border: 1px solid #e9ecef`, `border-radius: 10px`, `padding: 1.25rem`, light shadow

**Panels:** `.autods-sa-panel` hidden by default; `.autods-sa-panel--active` `display: block`.

---

## Responsive breakpoints (as in RO dashboard)

| Breakpoint | Behavior |
|------------|----------|
| `max-width: 640px` | Meta grid (header two‑column) collapses to one column |
| `max-width: 720px` | Job card panels (`.autods-sa-jc-panel`) stack column; mechanic column full width cap |
| `max-width: 900px` | Job card head row grid becomes two columns; third cell spans full width |

---

## Major component groups (class prefix cheat sheet)

| Prefix | Purpose |
|--------|---------|
| `.autods-sa-photo`, `.autods-sa-title-block`, `.autods-sa-header-meta`, `.autods-sa-meta-*` | Vehicle image, H1, two‑column meta with Font Awesome icons |
| `.autods-sa-gauge-*` | Donut completion: `112px` ring, inner text stack, optical `translateY(-3px)` on inner |
| `.autods-sa-tab`, `.autods-sa-tab--active`, `.autods-sa-badge`, `.autods-sa-badge--blue` | Tab bar and count badges |
| `.autods-sa-jc-*` | Job card rows in “health” view: white card `12px` radius, green highlight `.autods-sa-jc-panel--current`, avatar ring, service title in `#3d5a6c` |
| `.autods-sa-insp-*` | Inspections: section heads, row cards, tables, nested `<details>`, edit outline button |
| `.autods-sa-kv`, `.autods-sa-kv-grid` | Key/value detail grids (`minmax(200px, 1fr)`) |
| `.autods-sa-cc-*` | Customer concerns: `<details>` cards, blue circular index, chevron via rotated borders, diagnostics sub‑tables |
| `.autods-sa-text-link`, `.autods-sa-muted`, `.autods-sa-ro-hint` | Links (`BLUE_BADGE`), muted copy, green uppercase RO hint |

**Job Card dashboard only:** root combines `.autods-jc-dash.autods-sa`; many selectors are written as `.autods-jc-dash .autods-sa-…` to avoid leaking into the rest of the form. Extra classes: `.autods-jc-tech-photo-wrap`, `.autods-jc-overlay-btn`, `.autods-jc-timer-below`, etc.

---

## Interaction & accessibility patterns

- Tabs are `<button type="button">`; active state is class‑based
- Concern rows use native `<details>` / `<summary>` with `::-webkit-details-marker { display: none }` and custom chevron (`.autods-sa-cc-chev`)
- Tables use `border-collapse`, light row borders, uppercase compact headers
- Touch: Job Card variant sets `-webkit-tap-highlight-color: transparent`, `touch-action: manipulation` on tabs and overlay buttons, `min-height: 44px` on some controls

---

## Porting checklist

1. **Copy or mirror the token table** as `:root` CSS variables (e.g. `--autods-bg-muted`, `--autods-primary`, `--autods-success`).
2. **Load Inter** (or keep the same fallback stack) for parity.
3. **Keep the `1100px` max width and 12px / 10px radius scale** — it defines the “card in a muted tray” look.
4. **Namespace all rules** (e.g. `.my-app-ro .autods-sa …`) if embedding inside an existing design system to avoid collisions.
5. **Gauge SVG** is generated in JS, not CSS; ring colors map to `GREEN` / `AMBER` / `RED_D` by completion percentage in application logic.
6. For a **single static CSS file**, extract the block between `<style>` and `</style>` from `repair_service_dashboard.js` and replace `${BG_MUTED}`, `${HEADER_BG}`, `${BLUE_BADGE}`, `${GREEN}` with the literal hex values above.

---

## Reference line numbers (approximate)

In `repair_service_dashboard.js`, the main style block runs roughly **lines 1996–2863** (within the `render_dashboard` template). Constants are at **lines 6–12**.
