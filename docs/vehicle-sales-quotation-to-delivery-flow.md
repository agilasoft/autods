# Vehicle Sales: Quote to Delivery

**Module:** Vehicle Sales (AutoDS)

Vehicle retail uses AutoDS documents, not the standard ERPNext Quotation, Sales Order, Delivery Note, or Purchase Receipt. Vehicle-tagged items (`Item.custom_vehicle_item`) are blocked on those standard documents when **Block vehicle items in standard flow** is enabled. The unit is not a stock item. Quantity lives on **Vehicle Unit**, and cost lives on **Vehicle Cost Ledger** with an optional Journal Entry.

## Flow

```
Purchase Order (vehicle PO)
        │
        ▼
Vehicle Receiving ──► Vehicle Unit (Available)
        │                 Vehicle Cost Ledger (Base)
        ▼
Opportunity / Customer
        │
        ▼
Vehicle Sales Quote (Open)
        │  submit order
        ▼
Vehicle Sales Order ──► Vehicle Unit (Reserved)
        │
        ├── Sales Invoice (update_stock = 0)
        │
        ▼
Vehicle Delivery Note ──► Vehicle Unit (Sold)
                          Vehicle Cost Ledger (COGS)
                          Journal Entry Dr COGS / Cr vehicle inventory
```

## Receiving

**Vehicle Receiving** is the inbound document for a vehicle purchase order.

- Match or create a **Vehicle Unit** from `chassis_number` (controlled by Vehicle Sales Settings `auto_create_vehicle_unit`).
- Post a **Vehicle Cost Ledger** row with `cost_type = Base` for `total_cost` (base, freight, and other landed cost).
- When `auto_post_je` is on, post a Journal Entry: debit `vehicle_inventory_account`, credit `stock_received_but_not_billed`.
- Company accounts and the default warehouse come from **Vehicle Sales Company Settings**.

`Item.custom_vehicle_item` must be a non-stock item. Inventory quantity is the unit status, not a stock ledger entry.

## Quote

**Vehicle Sales Quote** (`VSQ-.YYYY.-`) requires a customer, a vehicle unit, a company, and a base price.

- Accessories, discounts, and the sales taxes template are calculated on the quote.
- Submit sets status **Open** and moves a linked Opportunity to Quotation.
- A quote whose `valid_till` is in the past becomes **Expired** unless it is Ordered, Lost, or Cancelled.
- **Mark Lost** (submitted quotes only) requires a lost reason and can store a competitor. Ordered quotes cannot be marked lost.
- Creating a **Vehicle Sales Order** does not change the quote until that order is submitted. Submit sets the quote to **Ordered**. Cancelling the only submitted order returns it to **Open**.

## Sales order

**Vehicle Sales Order** reserves the vehicle unit when submitted, if the unit is Available: status **Reserved**, customer copied, `reserved_on` set.

Status is derived from delivery and billing:

| Delivery | Billing | Order status |
| --- | --- | --- |
| Not Delivered | Not Billed | To Deliver and Bill |
| Delivered | not Fully Billed | To Bill |
| not Delivered | Fully Billed | To Deliver |
| Delivered | Fully Billed | Completed |

**Advance Paid** is read-only. It is the sum of submitted Payment Entry allocations against the order's Sales Invoices, allocations that reference the order, and any unallocated amount on a Payment Entry whose **Vehicle Sales Order** field points at the order.

**Sales Invoice** is the standard ERPNext invoice: one line for the vehicle item, `update_stock = 0`, `custom_vehicle_sales = 1`, and links to the unit and the order. Stock does not move on the invoice. Billing status on the order follows submitted invoice totals.

## Delivery

**Vehicle Delivery Note** cannot be submitted until every delivery checklist line is checked.

On submit:

- Status becomes **Delivered**.
- A **Vehicle Cost Ledger** COGS row is posted for the unit's current cost.
- When `auto_post_je` is on, a Journal Entry debits COGS and credits vehicle inventory.
- The **Vehicle Unit** becomes **Sold** and stores the delivery note, customer, and invoice link.
- The sales order delivery status is refreshed.

Cancel reverses the ledger and journal entry and returns the unit to **Reserved** when this delivery was the one linked on the unit.

## Cost

**Vehicle Cost Ledger** `cost_type` values include Base, Freight, Landed Cost, Accessory, Installation, Adjustment, COGS, and Opening. `Vehicle Unit.current_cost` is the signed sum of submitted ledger rows. Deal gross on the sales desk is taxable selling price (net total minus discount) minus the COGS ledger amount.

Accessory items that are real stock can still be issued with a Stock Entry. That path capitalizes cost only when a ledger row (Accessory or Installation) is posted. The Configurations and Accessories table on the unit is the operational record of fitted accessories.

## Accounting dimension

Vehicle Unit is an accounting dimension. Journal entries from receiving and delivery carry the unit so inventory and COGS can be read per VIN.

## What this replaces

Earlier notes described a serial-number Delivery Note that updated stock ledger valuation. That is not the live retail path. Use Vehicle Receiving, Vehicle Sales Quote, Vehicle Sales Order, and Vehicle Delivery Note.
