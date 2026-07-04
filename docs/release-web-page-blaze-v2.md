# AutoDS Blaze (v2) — ERPNext Web Page copy

Use **Website → Web Page**, **Content type: Page Builder**. Template names are standard Frappe sections.

**Codename:** Blaze — *Fast, bright, unstoppable* (Cycle 1, letter B).  
**Semantic position:** v2, **December** cadence release (the ship after Asphalt).

Suggested **route:** `releases/blaze` or `auto-ds/blaze`.

---

## 1. Hero with Right Image

| Field | Copy |
|--------|------|
| **Title** | Blaze |
| **Subtitle** | AutoDS **v2** picks up where Asphalt leaves off: a **December** release focused on **speed and clarity** across the dealership—snappier everyday workflows, sharper reporting, and refinements that make service, parts, and vehicle sales feel **bright and unstoppable** on ERPNext. Blaze assumes you are on **Asphalt (v1)** or an equivalent baseline; upgrade paths and notes ship with **general availability targeted for December 2026**. Expect iterative polish rather than a rewrite: faster lists where it matters, clearer defaults for dealer roles, and groundwork for the next trains (**Crux**, **Drift**) without forcing risky big-bang changes mid-season. |
| **Image** | Attach a bold, high-contrast hero (motion/light motif fits “Blaze”). |
| **Primary Action Label** | Release notes |
| **Primary Action URL** | `/releases/blaze#details` or your changelog URL |
| **Secondary Action Label** | Upgrade from Asphalt |
| **Secondary Action URL** | Link to migration / bench upgrade docs |
| **Restrict Image inside Container** | Your choice (on if artwork needs a frame). |

---

## 2. Markdown — Release date and expectations

**Template:** Markdown · **Align:** Left (or Center)

```markdown
## Release date

**General availability:** December 2026 (second release of the calendar year on the AutoDS cadence).

**Train:** Blaze is **v2**, immediately following **Asphalt (v1)** in June. Patch releases may ship after GA for regressions and critical fixes.

---

## What to expect from v2

- **Relationship to v1:** Blaze **extends and tightens** the Asphalt foundation—performance, UX, and reporting—rather than replacing core dealer objects. Plan upgrades as a **controlled bump** from v1 with release-note review.
- **Performance & usability:** Emphasis on **faster paths** for high-volume roles (service advisers, parts counters, sales coordinators) and **clearer** screens and defaults where dealers felt friction on v1.
- **Reporting & visibility:** Broader **operational insight**—trends, exceptions, and drill-downs that help managers act without exporting everything to spreadsheets.
- **Stability:** Same bar as v1: staging validation, backups, and reconciliation around cutover; Blaze should feel **safer** than skipping versions.

---

## Highlights vs Asphalt

| Area | Blaze (v2) focus |
|------|-------------------|
| Day-to-day speed | List and form optimizations; fewer clicks on common repair and parts flows |
| Dashboards & reports | Enhanced summaries and trends for service, parts consumption, and vehicle inventory |
| Dealer UX | Refinements to workspaces, labels, and guided paths informed by v1 feedback |
| Platform | ERPNext compatibility updates bundled per Blaze train; documented breaking changes if any |
| Roadmap | Sets up **Crux (v3)** for the next June without forcing premature architectural bets |
```

---

## 3. Section with Features

**Template:** Section with Features  

**Title:** What’s in Blaze v2  

**Subtitle:** Capability and polish building on Asphalt—confirm final scope in release notes at GA.  

**Columns:** 3  

**Feature rows:**

| Title | Content |
|--------|---------|
| Faster service desk paths | Streamlined estimate → order → job flows; less waiting on routine transitions. |
| Parts visibility | Improved consumption and demand signals for counters and controllers. |
| Vehicle sales clarity | Sharper inventory and reservation views; quicker answers on lot status. |
| Reporting upgrades | Deeper trends and breakdowns for workshop throughput and parts usage. |
| Role-first UX | Workspace and field tweaks tuned for how dealers actually work day to day. |
| Upgrade-friendly train | Designed as the **next step from Asphalt**, not a parallel product line. |
| Platform hygiene | Dependency and framework alignment with supported ERPNext lines for Blaze. |
| Toward Crux | Focus areas feed the **June v3** roadmap without blocking December adoption. |

*(Optional **URL** per row for deep docs; optional **Icon** images.)*

---

## 4. Section with CTA

| Field | Copy |
|--------|------|
| **Title** | Move up to Blaze |
| **Subtitle** | December 2026 GA — upgrade from Asphalt, brief your teams, and keep momentum through year-end. |
| **CTA Label** | View upgrade guide |
| **CTA URL** | Your docs or contact page |
| **CTA Description** | Need a staged rollout or hosting help? We’re here. |
| **Show Confetti** | Optional |

---

## Suggested section order

1. Hero with Right Image  
2. Markdown (release date & expectations)  
3. Section with Features  
4. Section with CTA  
