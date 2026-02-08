# Vehicle Sales: Quotation to Delivery Flow

**Document version:** 1.0  
**Module:** Vehicle Sales (AutoDS)  
**Scope:** End-to-end flow from Quotation to Delivery, including cost and revenue accounting; adding costs on Vehicle Unit (accessories, features, configurations); how inventory cost is updated for the serial number; and **Vehicle Unit as an accounting dimension** for P&amp;L, inventory cost, and movement tracking per vehicle unit (auto-populated from serial numbers).

---

## 1. Overview

Vehicle sales in AutoDS use standard **ERPNext** transactions (Quotation → Sales Order → Delivery Note → Sales Invoice), with custom **Vehicle Sales** fields and **Vehicle Unit** linking for tracking and reporting. Accounting for **cost** (inventory, COGS) and **revenue** (sales income) follows ERPNext’s stock and accounts logic; Vehicle Unit cost fields support **management reporting** and reconciliation. Adding costs to a vehicle unit (accessories, features, configurations) **for inventory and COGS** requires: (1) **Stock Entry** to issue the accessory items from warehouse, (2) a **Job Card** to record installation work and installation cost, and (3) once installed, **adding that total cost to the vehicle serial number’s inventory** (so the Stock Ledger valuation for that serial no includes base + accessories + installation). The **Configurations & Accessories** tab on Vehicle Unit records cost for reporting; to reflect it in the ledger and in COGS on sale, the Stock Entry + Job Card + add-cost-to-serial process (see §3.3.1) must be followed.

---

## 2. Transaction Flow (Quotation to Delivery)

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│ Quotation   │ ──► │ Sales Order │ ──► │ Delivery Note│ ──► │ Sales Invoice │
│ (Vehicle   │     │ (Vehicle    │     │ (Serial No   │     │ (against DN   │
│  Sales)    │     │  Sales)     │     │  assigned)   │     │  or standalone)│
└─────────────┘     └─────────────┘     └──────────────┘     └───────────────┘
       │                    │                    │                    │
       │                    │                    │                    │
       ▼                    ▼                    ▼                    ▼
 Vehicle Quotation    Items flow as         Vehicle Unit         Vehicle Unit
 Accessories          standard items        linked (Code=        linked
 (accessory, item,    (no Vehicle Unit      Serial No);          (custom_vehicle_
  qty, rate,          link yet)              Status = Sold        unit)
  installation cost)
```

### 2.1 Quotation

- **Vehicle Sales:** Quotation has a **Vehicle Sales** checkbox (custom field `custom_vehicle_sales`). When checked, the quotation is treated as a vehicle sale.
- **Items:** Vehicle item(s) and any other products are on the **Items** table (standard ERPNext).
- **Vehicle Quotation Accessories:** Child table **Vehicle Quotation Accessories** can be used for:
  - **Accessory** (Link to Vehicle Accessory)
  - **Item** (defaults from Vehicle Accessory)
  - **Qty**, **Rate**, **Installation Cost**, **Amount**
- **Link to Vehicle Unit:** None at quotation stage. The specific **Vehicle Unit** (and thus Serial No/VIN) is chosen at **delivery** when the serial no is set on the Delivery Note.

### 2.2 Sales Order

- Created from Quotation (standard **Create Sales Order**).
- **Vehicle Sales:** Sales Order has the same **Vehicle Sales** checkbox; it is carried/ set so the order is identifiable as a vehicle sale.
- **Items:** Vehicle and accessories flow as normal **Sales Order** items (item, qty, rate, etc.). No mandatory link to a Vehicle Unit at this stage.
- **Stock reservation:** Optional (ERPNext **Reserve Stock**); vehicle unit allocation is still by serial no at delivery.

### 2.3 Delivery Note

- Created from Sales Order (or manually). For vehicle items, **Serial No** must be set on the item row(s) so that the delivered unit is identified.
- **On submit** (AutoDS hook `on_delivery_note_submit`):
  - For each **Serial No** on the delivery items, the app finds the **Vehicle Unit** whose **Code** equals that serial no.
  - For each such Vehicle Unit it sets:
    - **Delivery Note** = this Delivery Note
    - **Sales Invoice** = from `against_sales_invoice` (if the DN is against a Sales Invoice)
    - **Status** = **Sold**
  - If a Vehicle Unit is found, the app sets on the **Delivery Note** and (when applicable) on the **Sales Invoice**:
    - **Vehicle Sales** = 1
    - **Vehicle Unit** = first linked Vehicle Unit (for quick reference).

So the **link from transaction to Vehicle Unit** is established at **Delivery Note submit** via Serial No ↔ Vehicle Unit Code.

### 2.4 Sales Invoice

- **Creation:** Sales Invoice can be created **from Delivery Note** (against Delivery Note) or independently. When created against a Delivery Note that delivered vehicle serial nos, the Sales Invoice is linked to that Delivery Note and thus to the same Vehicle Unit(s).
- **Serial number when stock is issued in Delivery Note:** When inventory is issued in the **Delivery Note** (and the Sales Invoice does **not** update stock), the Sales Invoice must still show the serial numbers for the delivered vehicle(s). AutoDS ensures this: on **Sales Invoice validate** (`on_sales_invoice_validate`), for each item row that has **delivery_note** and **dn_detail** but is missing **serial_no** or **serial_and_batch_bundle**, the app copies those fields from the linked **Delivery Note Item**. So the serial number is always reflected on the Sales Invoice even when issuance was done in the Delivery Note.
- **On submit** (AutoDS hook `on_sales_invoice_submit`):
  - If the Sales Invoice does not already have a **Vehicle Unit** set but has item rows with **Serial No** (or serials from **serial_and_batch_bundle**), the app finds a **Vehicle Unit** with matching **Code** and sets **Vehicle Sales** and **Vehicle Unit** on the Sales Invoice.
- **Accounting:** Revenue and receivables are posted by ERPNext when the Sales Invoice is submitted (see Section 4).

---

## 3. Cost Accounting

### 3.1 Inventory valuation (source of cost)

- Vehicle items are **stock items** with **Has Serial No** enabled.
- **Valuation** is in ERPNext **Stock Ledger Entry** (SLE): each serial no + warehouse has a **valuation_rate**.
- **Vehicle Unit**:
  - **Code** = Serial Number (same value as in SLE).
  - **Current Cost** is updated on **Vehicle Unit save** from the latest SLE `valuation_rate` for that serial no + warehouse (see `VehicleUnit.update_current_cost()`). If no SLE exists, it falls back to **Purchase Price**.
- So **accounting inventory value** for the vehicle is the **Stock Ledger** value; **Current Cost** on Vehicle Unit mirrors it for reporting and reconciliation.

### 3.2 Cost of Goods Sold (COGS)

- When a **Delivery Note** is submitted with stock items (e.g. vehicle + accessories), ERPNext:
  - Reduces **inventory** (Stock Ledger) for the delivered serial nos/items.
  - Uses **valuation_rate** from Stock Ledger for the outgoing value.
- When a **Sales Invoice** is submitted with **Update Stock** (or when it is linked to a Delivery Note that already moved stock), ERPNext posts **Cost of Goods Sold**:
  - **Debit:** Cost of Goods Sold (expense account from Item default or transaction)
  - **Credit:** Stock / Inventory (asset) — value from Stock Ledger at time of delivery/sale
- **Valuation method** (FIFO, Moving Average, etc.) is per Item/Company; vehicle cost in GL is therefore driven by **Stock Ledger**, not by Vehicle Unit’s **Current Cost** or **Total Unit Cost**.

### 3.3 Adding costs on Vehicle Unit (accessories, features, configurations)

Vehicle Unit has a **Configurations & Accessories** tab with a child table **Vehicle Unit Accessory**. Use it to record accessories, optional fittings, and configurations fitted to that specific unit. This drives **Total Accessory Cost** and **Total Unit Cost** on the Vehicle Unit.

**Child table fields (Vehicle Unit Accessory):**

| Field | Description |
|-------|-------------|
| **Accessory** | Link to **Vehicle Accessory** (master: code, name, item, default price, installation cost). |
| **Item** | Fetched from Vehicle Accessory; links to the stock/sales Item. |
| **Type** | Accessory / Configuration / Optional Fitting. |
| **Qty** | Quantity (default 1). |
| **Unit Cost** | Cost per unit; defaults from Vehicle Accessory **Default Price** if left blank. |
| **Installation Cost** | One-time installation cost; defaults from Vehicle Accessory **Installation Cost** if left blank. |
| **Total Cost** | Read-only: **(Unit Cost × Qty) + Installation Cost** (calculated on validate). |

**Behaviour:**

- When you select an **Accessory**, **Unit Cost** and **Installation Cost** default from **Vehicle Accessory** (default_price, installation_cost); you can override them per row.
- **Total Cost** is set automatically on save (see `VehicleUnitAccessory.set_total_cost()`).
- **Vehicle Unit** then:
  - **Total Accessory / Config Cost** = sum of all child **Vehicle Unit Accessory** `total_cost`.
  - **Total Unit Cost** = **Current Cost** (from Stock Ledger, see below) + **Total Accessory / Config Cost**.

So adding rows in **Configurations & Accessories** increases the unit’s **total cost for reporting**; it does **not** by itself change the serial number’s value in the **Stock Ledger**. For accessory and installation costs to be reflected in the **inventory cost of the vehicle serial number** (and thus in GL and COGS), the process in **3.3.1** must be followed.

#### 3.3.1 Required process: Stock Entry (issue accessories) + Job Card (installation) + add cost to serial number

Adding costs to a vehicle unit so that **inventory** (and COGS on sale) reflects them requires:

1. **Stock Entry (Material Issue)** — Issue the accessory items from warehouse to the job. This:
   - Consumes accessory inventory (reduces stock; valuation is in Stock Ledger for those items).
   - Records **material cost** (the value of accessories issued).
   - Can be linked to a **Job Card** (e.g. created from Material Request raised from the Job Card). AutoDS supports setting `job_card` and `repair_order` on Stock Entry when created from a Material Request linked to a Job Card.

2. **Job Card** — Record the installation work for the vehicle unit. The Job Card:
   - Links to **Vehicle Unit** (and optionally Repair Order).
   - Captures **installation cost** (labor, time, or a dedicated installation-cost field if configured).
   - Can drive the Material Request / Stock Entry for issuing accessories (step 1).
   - When completed, provides the **installation cost** to be added to the vehicle’s inventory value.

3. **Add cost to the vehicle serial number** — Once accessories are installed, the **total cost** (material cost from the Stock Entry + installation cost from the Job Card) must be **added to the inventory cost of the vehicle serial number**. That way:
   - The **Stock Ledger Entry** for that serial no + warehouse gets an updated **valuation_rate** that includes base vehicle cost + accessories issued + installation.
   - **Vehicle Unit**’s **Current Cost** (pulled from SLE on save) then reflects the full cost.
   - On sale, **COGS** will use this updated valuation, so gross margin is correct.

**How “add cost to serial number” is done:** In ERPNext, the inventory value of a serial number is changed only by **stock transactions**. So step 3 is typically done via a **Stock Entry** that increases the value of that vehicle serial no (e.g. a Repack, or a custom purpose that posts an additional valuation to the same serial + warehouse). The exact mechanism (manual Stock Entry, automated from Job Card completion, or custom app logic) depends on implementation; the requirement is that the serial number’s **valuation_rate** in the Stock Ledger includes the added accessory and installation cost.

**Summary of the flow:**

| Step | Document / action | Effect |
|------|-------------------|--------|
| 1 | **Stock Entry** (Material Issue) – issue accessories | Accessory stock reduced; material cost known. |
| 2 | **Job Card** – installation work and installation cost | Installation cost captured and linked to Vehicle Unit. |
| 3 | **Add cost to serial number** (e.g. Stock Entry that adds value to vehicle serial) | SLE **valuation_rate** for vehicle serial no increased; Vehicle Unit **Current Cost** reflects full cost on next save. |

After step 3, the vehicle serial number’s inventory cost in the ledger and on **Vehicle Unit** (Current Cost) includes base cost + accessories + installation; **Total Unit Cost** on Vehicle Unit can still add any further **Vehicle Unit Accessory** rows used for reporting only (or you may use SLE as the single source of cost once step 3 is implemented).

### 3.4 How inventory cost is updated for that serial number

The **inventory cost** shown for a vehicle serial number in the system has two parts:

1. **Current Cost (inventory valuation from ERPNext)**  
   - Sourced only from **Stock Ledger Entry** (SLE).  
   - On every **Vehicle Unit save**, `VehicleUnit.update_current_cost()` runs:
     - It looks up the latest **Stock Ledger Entry** for that **Code** (serial no) + **Warehouse** and reads **valuation_rate**.
     - **Current Cost** on Vehicle Unit is set to that `valuation_rate`.
     - If there is no SLE for that serial no + warehouse, **Current Cost** falls back to **Purchase Price** (e.g. from Purchase Receipt or manual).
   - The **serial number’s inventory value** in the GL is updated only by **stock transactions** that create or update SLEs: **Purchase Receipt**, **Stock Entry** (Material Receipt, Repack, or a Stock Entry that adds value to the vehicle serial after installation — see **3.3.1**). Adding rows on the Vehicle Unit **Configurations & Accessories** tab does **not** by itself create or change any Stock Ledger Entry for that serial number; to include accessory and installation cost in inventory, the process in 3.3.1 (Stock Entry issue + Job Card + add cost to serial) must be used.

2. **Accessory / configuration cost (management reporting only)**  
   - **Total Accessory Cost** on Vehicle Unit comes from the **Vehicle Unit Accessory** child table (see 3.3).  
   - It is **not** written to the Stock Ledger. So the **accounting** inventory value for the serial number includes accessory/installation cost only after the **add cost to serial number** step in 3.3.1 (e.g. a Stock Entry that increases the valuation of that serial no).

**Summary:**

| What you do | Effect on Vehicle Unit | Effect on Stock Ledger (serial no) |
|-------------|-------------------------|-------------------------------------|
| Add/edit **Vehicle Unit Accessory** rows | **Total Accessory Cost** and **Total Unit Cost** updated on save | No change |
| Save Vehicle Unit (no SLE change) | **Current Cost** refreshed from latest SLE for that serial + warehouse | No change |
| Submit **Purchase Receipt** / **Stock Entry** for that serial no | **Current Cost** will update on next Vehicle Unit save (from new SLE) | **valuation_rate** set/updated for that serial no + warehouse |
| **Stock Entry (add value to serial)** after installation (see 3.3.1) | **Current Cost** will update on next Vehicle Unit save to include accessory + installation cost | **valuation_rate** increased so inventory and COGS reflect full cost |

Once the “add cost to serial number” step is done, the vehicle serial’s SLE valuation (and thus **Current Cost** and COGS on sale) includes base cost + accessories issued + installation cost from the Job Card.

### 3.5 Vehicle Unit cost fields (management reporting)

- **Total Accessory / Config Cost:** Sum of **Vehicle Unit Accessory** `total_cost` (accessories/configurations fitted to the unit).
- **Total Unit Cost:** **Current Cost** (from Stock Ledger) + **Total Accessory / Config Cost**.
- These are **not** the source of GL entries; they are for:
  - **Vehicle Inventory Cost** report
  - **Vehicle Sales Summary** (e.g. total unit cost vs revenue)
  - Internal cost and margin analysis

### 3.6 Where cost appears in the flow

| Stage                     | Cost accounting (GL)                    | Vehicle Unit / reporting                    |
|---------------------------|-----------------------------------------|---------------------------------------------|
| Purchase Receipt          | Inventory (asset) increased; valuation in SLE | Vehicle Unit: Purchase Receipt, purchase_price |
| Add accessories/features (form only) | No GL change                      | Vehicle Unit: total_accessory_cost, total_unit_cost (from child table) |
| **Issue accessories** (Stock Entry – Material Issue) | Accessory inventory reduced        | Job Card / Material Request linked; material cost known |
| **Job Card** (installation) | Installation cost captured (labor/cost) | Linked to Vehicle Unit; installation cost for step below |
| **Add cost to serial** (Stock Entry that adds value to vehicle serial) | Vehicle serial’s SLE **valuation_rate** increased | **Current Cost** on next Vehicle Unit save includes accessory + installation |
| Vehicle Unit save         | No GL change                            | Current Cost refreshed from SLE for serial + warehouse |
| In stock                  | Inventory value in SLE                  | Vehicle Unit: current_cost, total_unit_cost |
| Delivery Note             | Inventory reduced; valuation from SLE | Vehicle Unit: delivery_note, status = Sold  |
| Sales Invoice             | COGS (expense) posted from SLE valuation| Vehicle Unit: sales_invoice                 |

---

## 4. Revenue Accounting

### 4.1 Sales Invoice GL entries (ERPNext standard)

When a **Sales Invoice** is submitted, ERPNext posts entries such as (conceptually):

- **Debit:** Debtors (Accounts Receivable) — **grand_total** (or equivalent per company setup)
- **Credit:** Sales / Revenue (income account from Item or default) — **net_total** (or per-item income)
- **Credit / Debit:** Tax accounts (from **Taxes and Charges** template)

Item rows use:
- **Income account** (from Item, Price List, or Sales Invoice default)
- **Cost center** (from Item or default)

So **revenue** is recognized when the Sales Invoice is submitted; the **amount** is the invoiced value (and tax as configured).

### 4.2 Vehicle-specific behaviour

- Vehicle and accessories are normal **Sales Invoice items**; they use the same revenue and tax logic as any other item.
- **Vehicle Sales** and **Vehicle Unit** on the Sales Invoice are for linking and reporting (e.g. **Vehicle Sales Summary**), not for separate revenue accounts unless you configure different **Income accounts** per item (e.g. “Vehicle Sales” vs “Accessories Sales”).

### 4.3 Where revenue appears in the flow

| Stage          | Revenue accounting (GL)                          |
|----------------|---------------------------------------------------|
| Quotation      | None (no GL impact)                              |
| Sales Order    | None (no GL impact)                              |
| Delivery Note  | None (inventory movement only; COGS when SI posts)|
| Sales Invoice  | Revenue (income) + Debtors + Tax                 |

---

## 5. Summary: Flow and accounting at a glance

| Step            | Document        | Cost accounting (GL)              | Revenue accounting (GL) | Vehicle Unit / app logic                    |
|-----------------|-----------------|------------------------------------|--------------------------|---------------------------------------------|
| 1. Quote        | Quotation       | —                                  | —                        | Vehicle Sales flag; Quotation Accessories   |
| 2. Order        | Sales Order     | —                                  | —                        | Vehicle Sales flag; items only              |
| 3. Deliver      | Delivery Note   | Inventory ↓ (SLE); COGS when SI    | —                        | Link Vehicle Unit (Code = Serial No); Sold  |
| 4. Invoice      | Sales Invoice   | COGS (expense) from SLE            | Revenue + Debtors + Tax  | Link Vehicle Unit if not already set        |

- **Cost accounting:** Inventory and COGS are driven by **Stock Ledger Entry** valuation. Vehicle Unit **Current Cost** and **Total Unit Cost** align with that for reporting and reconciliation (e.g. **Vehicle Inventory Cost** report).
- **Revenue accounting:** Recognized on **Sales Invoice submit** via standard ERPNext posting to Debtors, Sales/Income, and Tax accounts.

---

## 6. Vehicle Unit accounting dimension (P&amp;L and inventory per unit)

AutoDS adds **Vehicle Unit** as an **Accounting Dimension** in ERPNext so you can track **profit and loss**, **inventory cost**, and **all movements** per vehicle unit. The dimension is **auto-populated** from serial numbers on transactions.

### 6.1 What is set up

- A patch creates an **Accounting Dimension** with **Reference Document Type** = **Vehicle Unit** (label “Vehicle Unit”, fieldname **vehicle_unit**). ERPNext then adds the **vehicle_unit** field to all doctypes in its accounting-dimension list (e.g. **GL Entry**, **Sales Invoice**, **Sales Invoice Item**, **Delivery Note**, **Delivery Note Item**, **Stock Entry**, **Stock Entry Detail**, **Purchase Receipt**, **Purchase Receipt Item**, and others).
- **GL entries** (revenue, COGS, inventory, tax, etc.) carry the **vehicle_unit** dimension when it is set on the voucher. You can filter and report by Vehicle Unit in **General Ledger**, **Trial Balance**, **Profitability Analysis**, **Gross Profit**, and other reports that support accounting dimensions.

### 6.2 Auto-population from serial numbers

On **before_validate**, the app sets the **Vehicle Unit** dimension from serial numbers wherever the dimension field exists:

| Document        | Behaviour |
|-----------------|-----------|
| **Sales Invoice** | For each item row with **serial_no** or **serial_and_batch_bundle**, the app resolves the serial to a **Vehicle Unit** (Code = serial no) and sets **vehicle_unit** on the row and on the header (first vehicle unit). |
| **Delivery Note** | Same: **vehicle_unit** set on header and items from serial numbers on items. |
| **Stock Entry**   | Same: **vehicle_unit** set on header and **items** from serial numbers (all movements with a vehicle serial no are tagged). |
| **Purchase Receipt** | Same: **vehicle_unit** set on header and items from serial numbers. |
| **From Repair Order** | When **Sales Invoice** or **Stock Entry** has **repair_order** set, **vehicle_unit** is set from the Repair Order’s Vehicle Unit so revenue and costs are tracked per repair order and per vehicle (see §7). |

So **all movements** that involve a vehicle serial number (purchase, delivery, sales invoice, stock entry) get the **vehicle_unit** dimension set automatically. That flows into **GL Entry** and **Stock Ledger** (where applicable), so you can:

- Track **revenue and COGS per Vehicle Unit** (P&amp;L per unit).
- Track **inventory cost** and valuation by Vehicle Unit.
- Report on **all movements** (purchase, delivery, sale, stock entries) by Vehicle Unit.

### 6.3 Reports and filters

Use standard ERPNext reports with the **Vehicle Unit** dimension:

- **General Ledger** — filter or group by Vehicle Unit.
- **Trial Balance** — by Vehicle Unit.
- **Profitability Analysis** / **Gross Profit** — by Vehicle Unit for margin per unit.
- **Dimension-wise Accounts Balance** (and similar) — Vehicle Unit as the dimension.

Together with **Vehicle Inventory Cost** and **Vehicle Sales Summary**, this gives full P&amp;L, inventory cost, and movement tracking per vehicle unit.

---

## 7. Repair Order accounting dimension (revenue and costs per repair order)

AutoDS adds **Repair Order** as an **Accounting Dimension** so you can track **revenue and costs** for each repair order, together with **Vehicle Unit** for that repair. **Sales Invoice**, **Stock Entry**, and **Journal Entry** (e.g. labor-related costs, insurance/warranty entries using standard costs) created from or linked to a Repair Order are tagged with both **Repair Order** and **Vehicle Unit** dimensions.

### 7.1 What is set up

- A patch creates an **Accounting Dimension** with **Reference Document Type** = **Repair Order** (label “Repair Order”, fieldname **repair_order**). ERPNext adds the **repair_order** field to the same accounting doctypes (GL Entry, Sales Invoice, Sales Invoice Item, Stock Entry, Stock Entry Detail, Journal Entry, Journal Entry Account, etc.).
- When a **Sales Invoice** is created from a Repair Order (Create Sales Invoice), the app sets **repair_order** = that order and **vehicle_unit** = the Repair Order’s Vehicle Unit (on validate if not already set).
- When a **Stock Entry** is linked to a Repair Order (e.g. Material Issue from RO, or from Material Request from Job Card), **repair_order** is set and **vehicle_unit** is set from the Repair Order’s Vehicle Unit.
- When a **Journal Entry** is created from a Repair Order (e.g. Insurance Journal Entry, Warranty Journal Entry, or manual labor/standard-cost entries), **repair_order** is set on the JE and on each **accounts** row; **vehicle_unit** is set from the Repair Order on the header and on each row so GL entries carry both dimensions.

### 7.2 Resulting tracking

- **Revenue** from repair orders: filter **Sales Invoice** and GL by **Repair Order** (and optionally **Vehicle Unit**).
- **Costs** (parts, labor, standard costs): **Stock Entry** and **Journal Entry** post to GL with **repair_order** and **vehicle_unit**, so you can report cost and P&amp;L per repair order and per vehicle unit.
- Use **General Ledger**, **Trial Balance**, **Profitability Analysis**, or **Dimension-wise Accounts Balance** with filters on Repair Order and/or Vehicle Unit for service revenue and cost analysis.

---

## 8. Related documents and reports

- **Design:** `design-vehicle-sales-process.md` — process, configuration, and cost monitoring.
- **Vehicle Unit accounting dimension:** §6 — P&amp;L, inventory cost, and movements per vehicle unit; auto-populated from serial numbers.
- **Repair Order accounting dimension:** §7 — revenue and costs per repair order; Sales Invoice, Stock Entry, and Journal Entry tagged with Repair Order and Vehicle Unit.
- **Reports:**
  - **Vehicle Inventory Cost** — units with Inventory Cost (SLE), Accessory/Config Cost, Total Unit Cost; links to Purchase Receipt, Delivery Note, Sales Invoice.
  - **Vehicle Sales Summary** — sold units with delivery date, Delivery Note, Sales Invoice, customer, total unit cost (for margin analysis).
  - **General Ledger / Trial Balance / Profitability Analysis** — filter or group by Vehicle Unit dimension for per-unit tracking.

---

*This document describes the flow and accounting as implemented in AutoDS with ERPNext. Actual account names and valuation methods depend on your Company and Item setup.*
