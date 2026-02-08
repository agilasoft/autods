# Design: Repair Estimate (Service Module)

**Version:** 1.0  
**Aligned with:** Repair Order  
**Module:** Service  

---

## 1. Purpose

Repair Estimate is a **pre-authorization / quote** document in the Service module. It allows:

- Capturing vehicle, customer, concerns, and proposed service/parts/sundry lines **before** committing to a Repair Order.
- Customer or insurance approval workflow (submit → approve/reject).
- **Creating a Repair Order** from an approved estimate, copying header and line data so work can start.

Repair Estimate is **aligned with Repair Order** in structure (tabs, sections, child tables, field names) so that "Create Repair Order" is a straightforward copy with minimal mapping.

---

## 2. Document Lifecycle

```
Draft → (Submit) → Submitted → (Approve / Reject)
                              → Approved → (Create Repair Order) → Converted to RO
                              → Rejected
```

- **Draft:** Editable estimate.
- **Submitted:** Sent for approval; limited edits if needed (configurable).
- **Approved:** Ready to convert to Repair Order.
- **Rejected:** Closed; optional reason/notes.
- **Converted to RO:** After "Create Repair Order" is used; link to the created Repair Order stored on the estimate.

Repair Order will get an optional **Link** field: `repair_estimate` → Repair Estimate (set when created from estimate).

---

## 3. DocType: Repair Estimate

**Naming:** `naming_series` (e.g. `RE-.#########`)  
**Module:** Service  
**Is Submittable:** Yes (for approval workflow).

### 3.1 Field Layout (aligned with Repair Order)

| Section / Tab        | Fields / Tables |
|----------------------|-----------------|
| **Details**          | Same header as Repair Order (see below). |
| **Insurance**         | Same as Repair Order. |
| **Concerns**         | Concerns table, Diagnostics table. |
| **Service Items**    | Table: Repair Estimate Service Items. |
| **Spareparts**       | Table: Repair Estimate Parts. |
| **Sundry Items**     | Table: Repair Estimate Sundry Items. |
| **Totals**           | Total Service / Parts / Sundry amounts, Grand Total. |
| **Inspection**       | Optional: Repair Estimate Service Inspection (same structure as RO). |
| **Photos**           | Optional: Repair Estimate Photos. |
| **Other Information**| SLA, Terms and Conditions (same as RO). |

No **Dashboard** tab (no Job Cards until there is a Repair Order).

---

## 4. Header Fields (Details tab)

Aligned with Repair Order; estimate-specific fields called out.

| Field                     | Type    | Notes |
|---------------------------|---------|--------|
| `naming_series`           | Select  | e.g. RE-.######### |
| **estimate_date**         | Date    | **Estimate-specific.** Default: today. |
| **validity_date**         | Date    | **Estimate-specific.** Quote valid until. |
| **status**                | Select  | **Estimate-specific.** Draft / Submitted / Approved / Rejected / Converted to RO. |
| `service_order_type`      | Link    | Service Order Type. |
| `repair_type`             | Link    | Repair Type. |
| `service_advisor`         | Link    | Employee. |
| `customer`                | Link    | Customer. |
| `vehicle_unit`            | Link    | Vehicle Unit (required). |
| `plate_no`                | Data    | From vehicle_unit. |
| `vehicle_id_no`           | Data    | From vehicle_unit. |
| `odometer`                | Data    | |
| `vehicle_engine_number`   | Data    | From vehicle_unit. |
| `vehicle_chassis_number`  | Data    | From vehicle_unit. |
| `expected_completion_date`| Datetime| Optional. |

**Vehicle Unit Information (collapsible):** Same as Repair Order (make, model, variant, year, edition, color, transmission, drive, fuel, body, warehouse, purchase date/price, current cost).

**Insurance tab:** Same as Repair Order: `insurance_claim_no`, `insurance_company`, `warranty`.

---

## 5. Child Tables (aligned with Repair Order)

### 5.1 Repair Estimate Service Items

Mirror **Repair Order Service Items.**

| Field            | Type    | Notes |
|------------------|---------|--------|
| `service_item`   | Link    | Item (custom_service_job_item). |
| `service_category` | Link  | From item. |
| `description`    | Text    | |
| `bill_type`      | Select  | Customer / Insurance / Warranty. |
| `bill_to`        | Link    | Customer. |
| `hours`          | Float   | |
| `rate`           | Currency| |
| `amount`         | Currency| Read-only: hours × rate. |

### 5.2 Repair Estimate Parts

Mirror **Repair Order Parts.**

| Field         | Type    | Notes |
|---------------|---------|--------|
| `item`        | Link    | Item. |
| `item_name`   | Data    | From item. |
| `item_type`   | Select  | Mechanical Part / Body Part / Paint Material / Other. |
| `qty`         | Float   | |
| `uom`         | Link    | From item. |
| `rate`        | Currency| |
| `amount`      | Currency| Read-only: qty × rate. |
| `bill_type`   | Select  | Customer / Insurance / Warranty. |
| `bill_to`     | Link    | Customer. |
| `warehouse`   | Link    | Optional. |
| (Paint)       |         | color_code, paint_type if item_type = Paint Material. |
| `description` | Text    | |

### 5.3 Repair Estimate Sundry Items

Mirror **Repair Order Sundry Items.**

| Field         | Type    | Notes |
|---------------|---------|--------|
| `item`        | Link    | Item. |
| `item_name`   | Data    | From item. |
| `description` | Text    | |
| `qty`         | Float   | |
| `uom`         | Link    | From item. |
| `rate`        | Currency| |
| `amount`      | Currency| Read-only: qty × rate. |
| `bill_type`   | Select  | Customer / Insurance / Warranty. |
| `bill_to`     | Link    | Customer. |

### 5.4 Repair Estimate Concerns

Mirror **Repair Order Concerns.**

| Field             | Type  | Notes |
|-------------------|-------|--------|
| `customer_concern`| Data  | |
| `concern`         | Link  | Repair Concern. |
| `description`     | Data  | From concern. |
| `notes`           | Long Text | |

### 5.5 Repair Estimate Diagnostics

Mirror **Repair Order Diagnostics.**

| Field             | Type  | Notes |
|-------------------|-------|--------|
| `customer_concern`| Data  | |
| `concern`         | Link  | Repair Concern. |
| `diagnostic`      | Link  | Repair Diagnostic. |
| `notes`           | Long Text | |

### 5.6 Repair Estimate Service Inspection (optional)

Same structure as **Repair Order Service Inspection** (inspection name, Service Inspection link, status, date, inspected by, remarks). Optional on estimate for pre-inspection notes.

### 5.7 Repair Estimate Photos (optional)

Same structure as **Repair Order Photos** (photo_type, description, image, taken_date, taken_by). Optional for before/during estimate photos.

---

## 6. Totals Section

Same as Repair Order:

- `total_service_items_amount` (Currency, read-only)
- `total_parts_amount` (Currency, read-only)
- `total_sundry_items_amount` (Currency, read-only)
- `grand_total` (Currency, read-only, bold)

Calculations: same as Repair Order (sum of child amounts; service = hours × rate per row).

---

## 7. Other Information Tab

Same as Repair Order:

- Service Level Agreement (link + notes)
- Terms and Conditions (link + fetched terms / tc_notes)

---

## 8. Repair Order Alignment Summary

| Repair Order              | Repair Estimate              |
|---------------------------|------------------------------|
| repair_date               | estimate_date (+ validity_date) |
| status (Draft/In Progress/…) | status (Draft/Submitted/Approved/Rejected/Converted to RO) |
| service_items → spareparts, sundry_items | Same table names and field sets |
| concerns, diagnostics      | Same                         |
| quality_inspections, photos| Same (optional on estimate)  |
| SLA, T&C                  | Same                         |
| —                         | repair_order (Link, set when converted) |

**Repair Order (new optional field):**

- `repair_estimate` — Link to Repair Estimate, set when "Create Repair Order" is run from an estimate.

---

## 9. Server Logic (Repair Estimate)

1. **validate**
   - Recompute child amounts (service: hours × rate; parts/sundry: qty × rate).
   - Recompute totals and grand_total.
2. **on_submit**
   - Optional: validate at least one line (service/parts/sundry); optional validations (e.g. validity_date >= estimate_date).
   - No stock or invoice: estimate is non-posting.
3. **Status transitions**
   - Draft → Submitted (on submit).
   - Submitted → Approved / Rejected (custom button or workflow).
   - Approved → Converted to RO when "Create Repair Order" is run (set status and `repair_order` link).
4. **Whitelist: create_repair_order**
   - Only if status = Approved and `repair_order` is empty.
   - Create new Repair Order:
     - Copy header: customer, vehicle_unit, repair_type, service_order_type, service_advisor, insurance fields, SLA, T&C, concerns, diagnostics.
     - Set Repair Order `repair_date` = today (or estimate validity_date); set `repair_estimate` = this estimate.
     - Copy service items → Repair Order Service Items.
     - Copy parts → Repair Order Parts.
     - Copy sundry items → Repair Order Sundry Items.
     - Optionally copy inspection rows and photos if implemented.
   - Submit the new Repair Order if desired (configurable).
   - Update Repair Estimate: status = "Converted to RO", `repair_order` = new RO name.
   - Return the new document name (e.g. for redirect).

---

## 10. Client Script (Repair Estimate)

- Formatters and list view: same as Repair Order where applicable.
- "Create Repair Order" button: visible when status = Approved and `repair_order` is empty; call `create_repair_order` and redirect to the new RO.
- Optional: "Submit" for approval, "Approve" / "Reject" if using simple workflow without Workflow DocType.

---

## 11. Permissions & List View

- Same module (Service) and role-based permissions as Repair Order (e.g. Service User, Service Manager).
- List view filters: status, customer, vehicle, estimate_date, validity_date.
- Standard filters: by status (Draft, Submitted, Approved, Rejected, Converted to RO).

---

## 12. Reports & Dashboards (optional)

- **Repair Estimate Summary:** List of estimates with status, customer, vehicle, grand_total, validity_date, linked RO.
- **Conversion rate:** Count Approved vs Converted to RO (optional KPI on Service workspace).

---

## 13. Implementation Checklist

- [ ] DocType: Repair Estimate (with all header fields and tabs).
- [ ] Child DocTypes: Repair Estimate Service Items, Parts, Sundry Items, Concerns, Diagnostics, Service Inspection, Photos.
- [ ] Repair Estimate: validate (amounts + totals), on_submit (status + validations), whitelist `create_repair_order`.
- [ ] Repair Order: add optional field `repair_estimate` (Link to Repair Estimate).
- [ ] Repair Estimate form: "Create Repair Order" button + client logic.
- [ ] Naming series RE-.######### (or as per standard).
- [ ] Optional: Workflow or buttons for Approve/Reject.
- [ ] Optional: Print format / PDF for customer-facing estimate.

---

*This design keeps Repair Estimate structurally aligned with Repair Order so that creating a Repair Order from an estimate is a direct copy of data with minimal transformation.*
