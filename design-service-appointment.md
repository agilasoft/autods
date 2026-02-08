# Design: Service Appointment System (Service Module)

**Version:** 1.0  
**Aligned with:** Repair Order, Repair Estimate  
**Module:** Service  

---

## 1. Purpose

Service Appointment is a **scheduling and booking** document in the Service module. It allows:

- **Booking vehicle service slots** by date and time (appointment window).
- Capturing customer, vehicle, service advisor, and appointment type **before** a Repair Order or Repair Estimate exists.
- **Calendar view** for advisors and reception to see daily/weekly appointments and manage capacity.
- Optional workflow: create a **Repair Estimate** or **Repair Order** from a confirmed appointment when the vehicle arrives.
- Status tracking: Scheduled → Confirmed → In Progress → Completed (or No-show / Cancelled).

Service Appointment is **lightweight** compared to Repair Order: it focuses on *when* and *who*, not on line items. It can optionally link to Repair Estimate or Repair Order once work is authorized.

---

## 2. Document Lifecycle

```
Draft / Scheduled → Confirmed → In Progress → Completed
                    ↘ No-show
                    ↘ Cancelled
```

- **Scheduled:** Appointment created; date/time and customer/vehicle set; awaiting confirmation (optional step).
- **Confirmed:** Customer or system confirmed; slot is reserved.
- **In Progress:** Vehicle arrived; appointment is being serviced (optional: link to RO created).
- **Completed:** Service done; optionally linked Repair Order submitted/closed.
- **No-show:** Customer did not arrive; slot can be freed.
- **Cancelled:** Appointment cancelled; optional reason/notes.

**Optional link to downstream documents:**

- `repair_estimate` — Link to Repair Estimate (set when "Create Repair Estimate" is run from appointment).
- `repair_order` — Link to Repair Order (set when "Create Repair Order" is run, or when RO is created from linked estimate).

---

## 3. DocType: Service Appointment

**Naming:** `naming_series` (e.g. `SA-.#########`)  
**Module:** Service  
**Is Submittable:** No (status-driven; no accounting impact).

### 3.1 Calendar View

Service Appointment **must support Calendar View** for scheduling.

| Requirement | Implementation |
|-------------|----------------|
| **Start** | Datetime: `appointment_date` + `appointment_start_time` (or single `scheduled_start` Datetime field). |
| **End** | Datetime: `appointment_date` + `appointment_end_time` (or single `scheduled_end` Datetime field). |
| **Title** | Display: customer name + vehicle (plate_no) or appointment subject. |
| **Color / style** | By `status` (e.g. Scheduled=default, Confirmed=blue, In Progress=orange, Completed=green, Cancelled=grey). |

**Frappe calendar configuration:**

- **Option A:** Two fields: `appointment_date` (Date), `appointment_start_time` (Time), `appointment_end_time` (Time). In calendar JS, derive start/end as combined datetime.
- **Option B:** Two fields: `scheduled_start` (Datetime), `scheduled_end` (Datetime). Map directly to calendar `start` / `end`.

Calendar view filters: by **service_advisor**, **status**, **appointment_date** range.

### 3.2 Field Layout (Tabs / Sections)

| Section / Tab   | Content |
|-----------------|---------|
| **Details**     | Appointment date/time, status, customer, vehicle, advisor, type, notes. |
| **Service Info**| Optional: service_order_type, repair_type, brief description/subject. |
| **Links**       | repair_estimate, repair_order (read-only when set). |
| **Other**       | Notes, internal remarks, cancellation reason (if status = Cancelled). |

No child tables required for core appointment; keep it single-document for calendar performance.

---

## 4. Header Fields (Details)

| Field | Type | Notes |
|-------|------|--------|
| `naming_series` | Select | e.g. SA-.######### |
| **appointment_date** | Date | **Required.** Day of appointment. Default: today or next working day. |
| **appointment_start_time** | Time | **Required.** Slot start. |
| **appointment_end_time** | Time | **Required.** Slot end; must be after start. |
| **status** | Select | Scheduled / Confirmed / In Progress / Completed / No-show / Cancelled. |
| `service_advisor` | Link | Employee (optional; for capacity view per advisor). |
| `customer` | Link | **Required.** Customer. |
| `vehicle_unit` | Link | Vehicle Unit (optional at booking; can be filled later). |
| `plate_no` | Data | From vehicle_unit. |
| `vehicle_id_no` | Data | From vehicle_unit. |
| **subject** or **description** | Small Text | Optional. Brief reason (e.g. "Annual service", "Brake check"). |

**Service Info (optional):**

| Field | Type | Notes |
|-------|------|--------|
| `service_order_type` | Link | Service Order Type. |
| `repair_type` | Link | Repair Type. |
| `contact_person` | Data | Optional. Contact name/phone for reminder. |
| `contact_mobile` | Data | Optional. |

**Links (read-only when set):**

| Field | Type | Notes |
|-------|------|--------|
| `repair_estimate` | Link | Repair Estimate. Set when "Create Repair Estimate" is run. |
| `repair_order` | Link | Repair Order. Set when RO is created from appointment or from linked estimate. |

**Other:**

| Field | Type | Notes |
|-------|------|--------|
| `notes` | Text | Internal notes. |
| `cancellation_reason` | Small Text | Shown when status = Cancelled. |

---

## 5. Calendar View Configuration (Frappe)

### 5.1 DocType Fields for Calendar

Use either:

- **Option A (recommended):**  
  - `appointment_date` (Date)  
  - `appointment_start_time` (Time)  
  - `appointment_end_time` (Time)  
  - In calendar JS: build start = `appointment_date` + `appointment_start_time`, end = `appointment_date` + `appointment_end_time`.

- **Option B:**  
  - `scheduled_start` (Datetime)  
  - `scheduled_end` (Datetime)  
  - Map directly to calendar start/end.

### 5.2 Calendar JS: `service_appointment_calendar.js`

```js
// Pseudo-config; actual API may use get_events_method or field_map
frappe.views.CalendarView.prototype.get_events_method = "autods.service.doctype.service_appointment.service_appointment.get_events";
// field_map: start → appointment_date + appointment_start_time (or scheduled_start)
//            end   → appointment_date + appointment_end_time   (or scheduled_end)
//            title → customer name + plate_no
// style_map: by status (Scheduled, Confirmed, In Progress, Completed, No-show, Cancelled)
```

- **get_events:** Server method (whitelisted) that accepts `start` and `end` (date range), returns list of events with `start`, `end`, `title`, `name`, `status`, etc. Use for filtering by advisor, status, and to compute title from customer/vehicle.
- **Filters:** service_advisor, status (optional quick filters above calendar).

### 5.3 Calendar Behavior

- **Views:** Day, Week, Month (standard Frappe calendar).
- **Drag-and-drop:** Optional; if supported, update `appointment_date` and start/end time on resize or move.
- **Click:** Open Service Appointment form.
- **Color:** By status for quick visual scan.

---

## 6. Server Logic (Service Appointment)

1. **validate**
   - If `appointment_end_time` <= `appointment_start_time`, raise validation (same day).
   - If using date + time, ensure end datetime > start datetime (e.g. cross-midnight not allowed or handled).
   - Optional: check overlapping appointments for same `service_advisor` (configurable).
2. **Status transitions**
   - Any → Cancelled: allow; set `cancellation_reason` optional.
   - Scheduled → Confirmed → In Progress → Completed: standard flow.
   - No-show: from Scheduled or Confirmed.
3. **Whitelist: create_repair_estimate**
   - Allowed when status in (Scheduled, Confirmed, In Progress) and `repair_estimate` is empty.
   - Create new Repair Estimate: copy customer, vehicle_unit, service_advisor, service_order_type, repair_type from appointment; set estimate_date = today; link appointment to estimate via a field on Repair Estimate (e.g. `service_appointment`) and set `repair_estimate` on appointment.
   - Return new document name (for redirect).
4. **Whitelist: create_repair_order**
   - Allowed when status in (Scheduled, Confirmed, In Progress) and `repair_order` is empty (and optionally when `repair_estimate` is approved: create from estimate; else create blank RO with header from appointment).
   - If `repair_estimate` is set and approved: call Repair Estimate’s create_repair_order; set created RO’s link on this appointment (`repair_order`).
   - If no estimate: create new Repair Order from appointment header (customer, vehicle_unit, service_advisor, etc.); set `repair_order` on appointment.
   - Return new document name.

**Repair Estimate (optional new field):**  
- `service_appointment` — Link to Service Appointment (set when created from appointment).

**Repair Order (existing/optional):**  
- `repair_estimate` already in design; optionally `service_appointment` — Link to Service Appointment (set when created from appointment or from estimate that had appointment).

---

## 7. Client Script (Service Appointment)

- **Form:**  
  - "Create Repair Estimate" button: visible when status allows and `repair_estimate` is empty; call `create_repair_estimate`, redirect to new estimate.  
  - "Create Repair Order" button: visible when status allows and `repair_order` is empty; call `create_repair_order` (or open wizard: from estimate vs blank), redirect to new RO.  
  - List view: show status, appointment_date, appointment_start_time, customer, plate_no, service_advisor.
- **Calendar:**  
  - Default view option: Calendar (in DocType list view switcher).  
  - Formatters: status color, time range in list.

---

## 8. Permissions & List View

- **Module:** Service. Same role-based permissions as Repair Order (e.g. Service User, Service Manager).
- **List view:** Columns: name, appointment_date, appointment_start_time, appointment_end_time, customer, plate_no, service_advisor, status.
- **Standard filters:** status, appointment_date, service_advisor, customer.
- **Calendar view:** Available from list view toolbar; filters applied to calendar data.

---

## 9. Reports & Dashboards (Optional)

- **Appointment Summary:** Count by status (Scheduled, Confirmed, In Progress, Completed, No-show, Cancelled) for a date range.
- **Advisor utilization:** Appointments per service_advisor per day/week (for capacity).
- **Conversion:** Appointments → Repair Estimate → Repair Order (optional KPI on Service workspace).
- **No-show rate:** No-show count / total scheduled (optional).

---

## 10. Implementation Checklist

- [ ] DocType: Service Appointment (Details + Service Info + Links + Other).
- [ ] Fields: appointment_date, appointment_start_time, appointment_end_time, status, customer, vehicle_unit, service_advisor, subject/description, repair_estimate, repair_order, notes, cancellation_reason.
- [ ] Naming series SA-.######### (or as per standard).
- [ ] Calendar view: create `service_appointment_calendar.js` with get_events (whitelisted), field_map (start/end/title), style_map (status).
- [ ] Server: validate (time range, optional overlap check), whitelist `create_repair_estimate`, `create_repair_order`.
- [ ] Repair Estimate: add optional `service_appointment` (Link).
- [ ] Repair Order: add optional `service_appointment` (Link); ensure create_repair_order from estimate still sets repair_estimate.
- [ ] Form: "Create Repair Estimate" and "Create Repair Order" buttons + client logic.
- [ ] List view: columns and standard filters; enable Calendar view in DocType.
- [ ] Optional: Reminders (e.g. email/SMS day before) — separate hook or integration.
- [ ] Optional: Slot/availability logic (e.g. prevent double-book per advisor) in validate or custom API.

---

## 11. Alignment Summary

| Entity | Relationship with Service Appointment |
|--------|--------------------------------------|
| **Repair Estimate** | Can be created from appointment; optional link `service_appointment` on estimate. |
| **Repair Order** | Can be created from appointment (or from estimate created from appointment); optional link `service_appointment` on RO. |
| **Customer / Vehicle Unit** | Same as Repair Order; required on appointment for booking. |
| **Service Advisor** | Optional; used for calendar filter and capacity view. |
| **Shopfloor Schedule** | Independent (job-level scheduling); appointment is pre-RO. |

---

*This design provides a dedicated Service Appointment System with calendar view for booking and capacity management, and clear paths to Repair Estimate and Repair Order when the customer commits to work.*
