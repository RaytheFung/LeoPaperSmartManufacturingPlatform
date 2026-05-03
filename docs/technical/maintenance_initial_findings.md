# Maintenance Initial Findings

## What the file really is
- The maintenance export is **not one row = one maintenance event**.
- Across the 2025 full-year + 2026-01-01 to 2026-03-12 files, I counted **8,800 transaction rows** but only **3,012 unique work orders**.
- Average lines per work order is **2.92**, median **1**, and one work order can span up to **345** lines.
- Most rows are material issue/return transactions, so this file is strongest for **asset mapping**, **parts consumption**, and **maintenance workload mix**; it is weaker for exact downtime duration unless more fields/tables exist.

## Work order type mix
- AM: 4,835 rows
- PM: 1,818 rows
- CM: 1,689 rows
- EV: 222 rows
- OP: 143 rows
- EM: 93 rows

## Why this file is strategically important
- It contains both `資產` and `資產老編號`, which gives a direct **new-code ↔ legacy-code crosswalk**.
- This is the best available evidence to stabilize machine alias mapping for families such as `024↔1024`, `035↔1035`, `166↔1166`, and `256↔1234`.
- It also exposes component assets like `UV和IR系統`, `印刷座`, `飛達`, so phase-2 maintenance analytics can be more granular than whole-machine only.

## FYP-safe recommendation
- For the FYP deliverable, treat this export as **maintenance transaction / parts log**, not as a full CMMS event log.
- Use it first for:
  1. machine alias registry enrichment;
  2. maintenance type counts by machine;
  3. last-maintenance-date proxy;
  4. parts-consumption hotspot ranking.
- Do **not** oversell it as precise downtime-labelled predictive-maintenance training data yet.