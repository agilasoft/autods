# General Repair & Repair Module Removal - Safety Analysis

**Status: ✅ Completed** (2026-02-14)

## Summary

| Action | Safe? | Notes |
|--------|-------|-------|
| Remove **General Repair** | ✅ Yes | All DocTypes have **Service** duplicates |
| Remove **Repair** | ⚠️ Partial | Moved 3 DocTypes + Inspection Item to Service first |

---

## Repair Module - Required by Service

**Repair Order** (Service) uses these child DocTypes from **Repair**:

| DocType | Used By | Service Has Duplicate? |
|---------|---------|------------------------|
| RO Customer Bill | Repair Order (table) | ❌ No |
| RO Insurance Bill | Repair Order (table) | ❌ No |
| GR Order Diagnostic Inspection | Repair Order (table) | ❌ No |
| Repair Order Diagnostics | Repair Order (table) | ✅ Yes (Service) |
| Repair Order PreRepair Inspection | Repair Order (table) | ✅ Yes (Service) |
| Repair Order Spareparts | Job Card (validation msg) | ❌ No - but Repair Order uses **Repair Order Parts** (Service) |

**Action for Repair:** Move RO Customer Bill, RO Insurance Bill, GR Order Diagnostic Inspection to Service module, then remove Repair. Repair Order Diagnostics and Repair Order PreRepair Inspection already exist in Service.

---

## General Repair Module - All Duplicated in Service

| General Repair DocType | Service Duplicate |
|-----------------------|-------------------|
| Job Card | ✅ Job Card |
| Gate Pass | ✅ Gate Pass |
| Spareparts Request | ✅ Spareparts Request |
| Spareparts Request Item | ✅ Spareparts Request Item |
| Service Inspection | ✅ Service Inspection |
| Service Inspection Item | ✅ Service Inspection Item |
| Service Inspection Template | ✅ Service Inspection Template |
| Service Inspection Template Item | ✅ Service Inspection Template Item |
| Default Service Inspection | ✅ Default Service Inspection |
| Job Card Work Detail | ✅ Job Card Work Detail |
| Job Card Spareparts Request | ✅ Job Card Spareparts Request |
| Technician Group | ✅ Technician Group |
| Technician Skill | ✅ Technician Skill |
| Technician Skills Group | ✅ Technician Skills Group |
| Work Area | ✅ Work Area |
| Service Category | ✅ Service Category |
| Repair Concern | ✅ Repair Concern |
| General Repair Settings | ✅ (also in Repair) |
| Inspection Item | ✅ (also in Repair) |
| GR Order Diagnostics | Used by General Repair Order only |
| GR Order PreRepair Inspection | Used by General Repair Order only |
| GR Order Diagnostic Inspection | Used by Repair Order (Repair module) |
| General Repair Order | Legacy - not used by Repair Order |

**Action for General Repair:** Safe to remove entirely. Reports/dashboards/number cards reference Repair Order, Job Card (Service) - move to Service module.

---

## Items to Move to Service Before Removal

1. **From Repair:** `ro_customer_bill`, `ro_insurance_bill`, `gr_order_diagnostic_inspection` → change module to "Service"
2. **General Repair reports/dashboards/number cards** → change module to "Service" (or delete if Service has equivalents)

---

## Job Card Validation Note

`job_card.py` - Updated message to "Repair Order Parts" for consistency.

---

## Completed Actions

1. **Moved to Service:** RO Customer Bill, RO Insurance Bill, GR Order Diagnostic Inspection, Inspection Item
2. **Deleted:** General Repair and Repair module folders
3. **Patch:** `remove_general_repair_and_repair_modules` removes orphaned Module Defs before sync
4. **Orphaned (intentionally removed):** Repair Order Spareparts, GR Order PreRepair Inspection, GR Order Diagnostics, General Repair Order, General Repair Settings, Sales and Pricing DocTypes (module not in modules.txt)
