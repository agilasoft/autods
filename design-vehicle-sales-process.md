# Vehicle Sales: Process, Configuration & Cost Monitoring

## Current process (review)

### 1. Purchasing
- **ERPNext**: Vehicle units are received via **Purchase Receipt** or **Stock Entry** (Material Receipt).
- The **Item** for the vehicle must have **Has Serial No** enabled; each unit is identified by a **Serial No** (VIN/code).
- **Vehicle Unit** master uses **Code** = Serial Number; the same value links the unit to inventory (Stock Ledger Entry uses `serial_no`).
- **Purchase Date** and **Purchase Price** can be entered manually on Vehicle Unit, or are updated when a Purchase Receipt is submitted (see Integration below).

### 2. Receipt
- Receipt is the same as purchasing: Purchase Receipt or Stock Entry receives the item with serial numbers into a **Warehouse**.
- **Vehicle Unit**:
  - **Warehouse**: Set to the warehouse where the unit is stocked.
  - **Current Cost**: Updated on save from **Stock Ledger Entry** (latest `valuation_rate` for that serial no + warehouse). This keeps vehicle inventory cost aligned with ERPNext valuation.
- If no Stock Ledger value exists, **Current Cost** falls back to **Purchase Price**.

### 3. Sales
- **Quotation** and **Sales Order** have a **Vehicle Sales** checkbox (custom field).
- Quotation can include **Vehicle Quotation Accessories** (child table: accessory, item, qty, rate, installation cost, amount).
- Sales Order is created from Quotation; items (vehicle + accessories) flow as standard ERPNext items.
- There is no mandatory link from Sales Order item to Vehicle Unit; the link is established at delivery when serial no is assigned.

### 4. Delivery
- **Delivery Note** is created from Sales Order (or independently). When vehicle items are delivered, **Serial No** is set on the item row.
- On **Delivery Note submit**, the app now:
  - Finds **Vehicle Unit**(s) whose **Code** matches the serial no(s) on the delivery.
  - Sets **Delivery Note** and **Sales Invoice** (if against Sales Invoice) on the Vehicle Unit.
  - Sets **Status** = **Sold**.

---

## New: Vehicle unit configuration & cost monitoring

### Vehicle Unit configuration
- New tab **Configurations & Accessories** with child table **Vehicle Unit Accessory**.
- Each row: **Accessory** (Link to Vehicle Accessory), **Item**, **Type** (Accessory / Configuration / Optional Fitting), **Qty**, **Unit Cost**, **Installation Cost**, **Total Cost**.
- **Unit Cost** and **Installation Cost** default from **Vehicle Accessory** (default_price, installation_cost) when the accessory is selected.
- **Total Cost** = (Unit Cost × Qty) + Installation Cost (computed on validate).

### Cost monitoring on Vehicle Unit
- **Total Accessory / Config Cost**: Sum of all child **Vehicle Unit Accessory** `total_cost` (read-only).
- **Total Unit Cost**: **Current Cost** (from Stock Ledger) + **Total Accessory / Config Cost** (read-only).
- **Current Cost** continues to be updated from **Stock Ledger Entry** on save, so inventory valuation stays in sync with ERPNext.

### Transaction links (read-only on Vehicle Unit)
- **Purchase Receipt**: Set when a PR that contains this unit’s serial no is submitted.
- **Delivery Note**: Set when a Delivery Note that delivers this unit’s serial no is submitted.
- **Sales Invoice**: Set from the Delivery Note’s against_sales_invoice when applicable.

---

## Integration with ERPNext accounting

- **Inventory value**: Vehicle items are stock items; valuation is in **Stock Ledger Entry** and flows to **GL** via ERPNext’s stock valuation (e.g. Stock Ledger → reconciliation with **Stock Balance** and **General Ledger**).
- **Vehicle Unit**:
  - **Current Cost** = latest valuation rate from Stock Ledger for that serial no + warehouse.
  - **Total Unit Cost** = Current Cost + accessory/configuration cost (for management reporting; the accounting inventory value remains the Stock Ledger value).
- **Vehicle Inventory Cost** report:
  - Lists Vehicle Units with: Serial/VIN, Item, Make, Model, Status, Warehouse, **Inventory Cost (SLE)**, **Accessory/Config Cost**, **Total Unit Cost**, and links to Purchase Receipt, Delivery Note, Sales Invoice.
  - Filters: Status, Warehouse, Company.
  - Use this report to monitor vehicle inventory cost and trace back to Purchase Receipt, Delivery Note, and Sales Invoice.

---

## Summary

| Area              | Implementation |
|-------------------|----------------|
| Purchasing        | Purchase Receipt / Stock Entry with serial no; Vehicle Unit code = serial no. |
| Receipt           | Same as above; Vehicle Unit warehouse and current cost from SLE. |
| Sales             | Quotation (Vehicle Sales + accessories) → Sales Order. |
| Delivery          | Delivery Note with serial no; on submit → Vehicle Unit: Delivery Note, Sales Invoice, Status = Sold. |
| Configuration     | Vehicle Unit tab “Configurations & Accessories” (Vehicle Unit Accessory child table). |
| Cost monitoring   | Total accessory cost + Total unit cost on Vehicle Unit; costs default from Vehicle Accessory. |
| Accounting tie-in | Current cost from Stock Ledger; Vehicle Inventory Cost report for reconciliation and tracing. |
