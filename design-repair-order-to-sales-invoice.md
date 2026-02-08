# Design: Sales Invoice from Repair Order (with Billing Types)

**Version:** 1.0  
**Module:** Service  
**Purpose:** Create Sales Invoice(s) from Repair Order with aligned tax/totals and correct handling of Customer, Insurance, and Warranty billing.

---

## 1. Overview

Repair Orders have line-level **bill type** (Customer, Insurance, Warranty) and optional **bill_to** (Customer link for Insurance/Warranty party). Today:

- **Create Sales Invoice** creates a single Sales Invoice for lines with `bill_type = "Customer"` only.
- **Insurance Journal Entry** and **Warranty Journal Entry** create Journal Entries for Insurance and Warranty amounts.

This design:

1. Aligns Repair Order with Sales Invoice **tax and total fields** so that creating Sales Invoices is smooth and predictable.
2. Bills **Customer**, **Insurance**, and **Warranty** accordingly: Customer and Insurance via Sales Invoices (party = customer / insurance company); Warranty via Sales Invoice (party = warranty provider) or Journal Entry, as configured.

---

## 2. Current State

### 2.1 Repair Order

- **Header:** customer, vehicle_unit, repair_date, status, insurance_claim_no, insurance_company, warranty (Customer link), etc.
- **Child tables:** Service Items, Spareparts (Repair Order Parts), Sundry Items — each row has:
  - **bill_type:** Customer | Insurance | Warranty
  - **bill_to:** Link to Customer (optional; used for Insurance/Warranty party)
- **Totals (no tax):** total_service_items_amount, total_parts_amount, total_sundry_items_amount, grand_total.

### 2.2 Sales Invoice (ERPNext)

- **Totals:** total, net_total, total_taxes_and_charges, grand_total, rounded_total (and base_*).
- **Tax:** tax_category, taxes_and_charges (template), **taxes** (table: account_head, charge_type, rate, tax_amount, total, etc.).
- **Items:** item_code, qty, rate, amount, item_tax_template, income_account, cost_center, etc.

### 2.3 Gaps

- Repair Order has no tax template or tax table, so SI created from RO relies on SI defaults; RO grand_total can differ from SI grand_total after tax.
- Only Customer-billable lines are invoiced; Insurance is handled by JE only; Warranty by JE only. No Sales Invoices for Insurance/Warranty parties.

---

## 3. Goals

1. **Repair Order alignment:** Add to Repair Order the same conceptual fields as Sales Invoice for taxes and totals (tax template, taxes table, net_total, total_taxes_and_charges, grand_total) so that:
   - User sees tax and final total on the RO.
   - When creating SI, we can copy tax setup and totals for a consistent experience.
2. **Billing by type:**
   - **Customer:** Sales Invoice with party = Repair Order customer; lines where bill_type = Customer.
   - **Insurance:** Sales Invoice(s) with party = insurance company (RO.insurance_company or line.bill_to); one SI per distinct insurance company.
   - **Warranty:** Either (a) Sales Invoice with party = warranty provider (RO.warranty or line.bill_to), or (b) Journal Entry only (no receivable). Design recommends (a) for consistency and receivables tracking, with option to use JE if preferred.
3. **Single action:** One action “Create Invoices” (or keep separate buttons) that can create up to three Sales Invoices (Customer, Insurance, Warranty) and optionally Warranty JE, so all bill types are handled from the same place.

---

## 4. Repair Order: Tax and Total Fields (Alignment with Sales Invoice)

To make RO → SI creation smooth and managed, add the following to **Repair Order** so that totals and taxes mirror Sales Invoice.

### 4.1 New Fields on Repair Order (Totals section)

| Field                     | Type     | Notes |
|---------------------------|----------|--------|
| **total**                 | Currency | Sum of line amounts (same as current sum; can rename/keep grand_total as display only or keep both for SI alignment). |
| **net_total**             | Currency | After discount; initially = total. Optional: add discount_percentage / discount_amount on RO later. |
| **tax_category**         | Link     | Tax Category (optional; same as SI). |
| **taxes_and_charges**    | Link     | Sales Taxes and Charges Template (optional). |
| **taxes**                 | Table    | Child: Repair Order Taxes (see below). |
| **total_taxes_and_charges** | Currency | Sum of tax row amounts. |
| **grand_total**           | Currency | net_total + total_taxes_and_charges (keep existing field name). |
| **rounded_total**         | Currency | Optional; for SI alignment. |
| **currency**              | Link     | Optional; default company currency. |
| **conversion_rate**       | Float    | Optional; default 1. |

Existing **total_service_items_amount**, **total_parts_amount**, **total_sundry_items_amount** remain for breakdown; **total** = sum of those three; **grand_total** = total (or net_total) + total_taxes_and_charges.

### 4.2 Child DocType: Repair Order Taxes

Mirror **Sales Taxes and Charges** (structure only; same columns needed for tax calculation):

| Field       | Type    | Notes |
|------------|---------|--------|
| charge_type | Select | Actual / On Net Total / On Previous Row Amount / On Previous Row Total / On Item Quantity |
| row_id     | Data    | Reference row (for On Previous Row *) |
| account_head | Link  | Account |
| description | Data   | |
| rate       | Percent | |
| tax_amount | Currency | Computed |
| total      | Currency | Computed |
| cost_center | Link   | Optional |

(Other columns from Sales Taxes and Charges can be added as needed: included_in_print_rate, base_*, etc.)

### 4.3 Calculation Flow on Repair Order

1. **validate:**  
   - Compute line amounts (existing): service hours×rate, parts qty×rate, sundry qty×rate.  
   - total = total_service_items_amount + total_parts_amount + total_sundry_items_amount.  
   - net_total = total (or apply discount if added later).  
   - If taxes_and_charges is set and taxes table is empty, **set_taxes()** from template (same logic as SI).  
   - Recompute **taxes** table (tax_amount, total per row) from net_total and template rates.  
   - total_taxes_and_charges = sum(tax_amount).  
   - grand_total = net_total + total_taxes_and_charges.  
   - rounded_total = round(grand_total) if rounding is used.

2. **Client:** On change of taxes_and_charges or tax_category, fetch tax template and refresh taxes table (same as Sales Invoice).

This keeps RO’s totals and tax structure identical in meaning to SI, so when we create SI we can copy taxes_and_charges, taxes, and totals for consistency.

---

## 5. Child Table Additions (Optional for Tax)

If we want item-level tax (e.g. item_tax_template) to flow to SI:

- Add **item_tax_template** (Link to Item Tax Template) to **Repair Order Service Items**, **Repair Order Parts**, and **Repair Order Sundry Items**. When building SI items, copy this to SI item row so SI’s tax calculation uses it.

Otherwise, document-level tax template on RO is enough for “same fields as SI” and smooth creation.

---

## 6. Billing by Type: Behavior

### 6.1 Customer

- **Party:** Repair Order **customer**.
- **Lines:** All rows (service items, parts, sundry) where **bill_type = "Customer"** (and bill_to empty or bill_to = customer).
- **Document:** One **Sales Invoice** per Repair Order for customer.
- **Link:** Sales Invoice **repair_order** = current Repair Order (custom field on SI if not present).
- **Tax/totals:** Set SI.taxes_and_charges = RO.taxes_and_charges (or from company/customer default), SI.tax_category = RO.tax_category; copy RO.taxes to SI.taxes if we have RO taxes; then run **set_missing_values()** and **calculate_taxes_and_totals()**. If RO has no template, use company default Sales Taxes and Charges Template.

### 6.2 Insurance

- **Party:** Insurance company — **RO.insurance_company** or, if multiple insurers per line, **line.bill_to** (Customer type = Insurance).
- **Lines:** All rows where **bill_type = "Insurance"**; group by **bill_to** (or single insurer from RO.insurance_company).
- **Document:** One **Sales Invoice** per distinct insurance company (RO.insurance_company or line.bill_to). If all Insurance lines have the same bill_to (or use RO.insurance_company), one SI. If multiple insurers, one SI per insurer.
- **References:** Set SI.repair_order, SI.insurance_claim_no = RO.insurance_claim_no (if SI has such field; else custom). Customer = insurance company (Customer master).
- **Tax/totals:** Same as Customer: use RO tax template and taxes when creating SI, then calculate_taxes_and_totals().

### 6.3 Warranty

- **Option A (recommended):** Treat like Insurance — create **Sales Invoice** with party = **RO.warranty** (or line.bill_to for warranty provider). Lines: **bill_type = "Warranty"**. One SI per distinct warranty provider. Outstanding = amount from warranty provider (if they reimburse).
- **Option B:** No SI; only **Journal Entry** (current behavior): Debit expense, Credit income (no receivable). Use when warranty is internal or no party invoicing.

**Recommendation:** Implement Option A (Warranty as Sales Invoice) for consistency and to support “bill them accordingly” when warranty provider is a separate party. Add a setting in Service Settings: “Warranty billing: Sales Invoice | Journal Entry” to choose behavior.

---

## 7. Create Invoices: API and UX

### 7.1 Server: Single Entry Point

- **Method:** `RepairOrder.create_invoices_from_repair_order(bill_types=None)`  
  - **bill_types:** list, e.g. `["Customer", "Insurance", "Warranty"]`. If None, create for all that have lines.
- **Logic:**
  1. Ensure RO is submitted.
  2. For each bill_type in bill_types (or inferred from lines):
     - **Customer:** If any line has bill_type Customer → create one SI (customer = RO.customer), append items from service_items, spareparts, sundry_items where bill_type = Customer. Set taxes from RO (or default). set_missing_values(); calculate_taxes_and_totals(); insert. Return name.
     - **Insurance:** Group lines with bill_type = Insurance by bill_to (or RO.insurance_company). For each party, create one SI (customer = that party), append matching lines. Set taxes; calculate; insert. Return list of names.
     - **Warranty:** If setting = Sales Invoice: same as Insurance (party = RO.warranty or line.bill_to). If setting = Journal Entry: call existing make_warranty_journal_entry().
  3. Prevent duplicate billing: if a Sales Invoice already exists for this Repair Order and same party (e.g. link SI.repair_order and SI.customer), either skip or raise. Option: add a child table **Repair Order Invoices** (doctype) on RO: invoice_type (Customer/Insurance/Warranty), party (Customer link), sales_invoice (Link), journal_entry (Link). Before creating, check this table; after creating, append row.
- **Return:** List of created documents: e.g. `[{ "bill_type": "Customer", "party": "CUST-001", "sales_invoice": "SINV-2025-00001" }, { "bill_type": "Insurance", "party": "INS-001", "sales_invoice": "SINV-2025-00002" }]`.

### 7.2 Backward Compatibility

- Keep **make_sales_invoice()** as wrapper that calls create_invoices_from_repair_order with bill_types=["Customer"] and returns first SI (for existing “Create Sales Invoice” button).
- Keep **make_insurance_journal_entry()** for sites that prefer JE for insurance; optionally deprecate once Insurance SI is adopted.
- **make_warranty_journal_entry()** remains when “Warranty billing” = Journal Entry.

### 7.3 Client (Repair Order form)

- **Create → Create Sales Invoice:** Unchanged; creates only Customer SI (existing behavior).
- **Create → Create Invoices:** New button that opens a dialog:
  - Checkboxes: **Customer**, **Insurance**, **Warranty** (pre-checked if there are lines for that type).
  - Optional: “Warranty: Sales Invoice” vs “Warranty: Journal Entry” (or read from Service Settings).
  - On submit: call `create_invoices_from_repair_order` with selected bill types; show success and list of created SI (and JE if any); offer links to open each.

---

## 8. Sales Invoice Custom Fields (if not present)

- **repair_order** (Link to Repair Order): Set on every SI created from RO; used for duplicate check and reporting.
- Optional: **insurance_claim_no** (Data) for Insurance SIs.

---

## 9. Service Settings Additions

| Field                         | Type    | Notes |
|------------------------------|---------|--------|
| **default_sales_taxes_and_charges** | Link | Sales Taxes and Charges Template; used when RO has no taxes_and_charges. |
| **warranty_billing_method**  | Select | "Sales Invoice" \| "Journal Entry". Default: Sales Invoice. |

---

## 10. Duplicate Prevention and Tracking

- **Option A:** Query: “Sales Invoice where repair_order = RO.name and customer = &lt;party&gt;”. If exists, skip or warn.
- **Option B:** Child table on Repair Order: **Repair Order Invoices** (invoice_type, party, sales_invoice, journal_entry). Before creating any SI/JE, check this table; after creating, append. Allows multiple SIs per party only if business allows (e.g. partial invoices); otherwise enforce one row per (invoice_type, party).

Recommendation: Start with Option A (simple); add Option B if partial or multiple invoices per party are required.

---

## 11. Implementation Checklist

### Phase 1: Repair Order tax/totals alignment

- [ ] Add to Repair Order: total, net_total, tax_category, taxes_and_charges, taxes (table), total_taxes_and_charges, grand_total (reuse or add), rounded_total, currency, conversion_rate.
- [ ] Create child DocType **Repair Order Taxes** (mirror Sales Taxes and Charges).
- [ ] Implement **set_taxes()** and tax calculation in Repair Order **validate** (and on load of taxes_and_charges in client).
- [ ] Optional: Add item_tax_template to Repair Order Service Items, Parts, Sundry Items.

### Phase 2: Create Invoices API

- [ ] Implement **create_invoices_from_repair_order(bill_types=None)** on RepairOrder:
  - Customer SI (existing logic, enhanced with RO taxes).
  - Insurance SI (one per insurer; party = insurance company).
  - Warranty SI or JE based on setting.
- [ ] Duplicate check (existing SI for same RO + party).
- [ ] Keep make_sales_invoice() as thin wrapper for backward compatibility.
- [ ] Add **default_sales_taxes_and_charges** and **warranty_billing_method** to Service Settings.

### Phase 3: Sales Invoice link and client

- [ ] Ensure Sales Invoice has **repair_order** (Link) — add custom field if not in core.
- [ ] New button **Create Invoices** with dialog (Customer / Insurance / Warranty); call create_invoices_from_repair_order; show created docs with links.
- [ ] Optional: Child table **Repair Order Invoices** on RO for tracking and duplicate prevention.

### Phase 4: Testing and docs

- [ ] Test: RO with only Customer lines → one Customer SI; totals match RO.
- [ ] Test: RO with Customer + Insurance → Customer SI + Insurance SI; correct parties and amounts.
- [ ] Test: RO with Warranty (SI and JE mode); duplicate creation prevented.
- [ ] Update user/docs for “Create Invoices” and billing types.

---

## 12. Summary

| Billing Type | Party            | Document           | Notes |
|-------------|------------------|--------------------|--------|
| Customer    | RO.customer      | Sales Invoice      | One SI; use RO tax/totals. |
| Insurance   | RO.insurance_company or line.bill_to | Sales Invoice | One SI per insurer. |
| Warranty    | RO.warranty or line.bill_to | Sales Invoice or Journal Entry | Configurable in Service Settings. |

Repair Order gets the same tax and total fields as Sales Invoice; creation of SI is smooth and managed; Customer, Insurance, and Warranty are billed accordingly via Sales Invoices (and optionally JE for Warranty).
