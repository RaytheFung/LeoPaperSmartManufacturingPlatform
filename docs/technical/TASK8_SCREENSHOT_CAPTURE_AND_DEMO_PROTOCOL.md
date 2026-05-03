# Task8 Screenshot Capture And Demo Protocol

## 1. Grounding rule for screenshots

Current screenshot-related facts:

- repo tree does not contain a routed-page screenshot pack for final deck use
- iCloud TextEdit manual packets do contain prior review screenshots for:
  - ETL / Unified View (`2026-04-05`)
  - Energy (`2026-04-05`)
  - Optimization (`2026-04-05`)
  - ML prediction / governance (`2026-04-06`)
  - Maintenance (`2026-04-06`)

Use boundary:

- those packet screenshots are planning references only
- they are useful for field interpretation and visual planning
- they should not be treated as final presentation assets
- the final deck should use one fresh, stylistically consistent capture set from the current live routed app

## 2. Curated final screenshot set

Do not capture “all pages.”

Capture one hero shot per module plus a small number of close-ups for flagship blocks.

### Required hero-shot pack

| ID | Module | Exact capture target | Why this shot matters | Existing packet reference found | Fresh final capture still needed |
|---|---|---|---|---|---|
| H1 | `🔄 ETL Pipeline` | `🧭 Latest Run Snapshot` first screen with latest month, deltas, and next-step area visible | best opening proof of month truth | yes | yes |
| H2 | `📊 Canonical Operations Overview` | first screen with KPI cards, `Coverage & Confidence Audit`, and the top of `Energy by State (kWh)` visible | best proof that the month is readable | yes | yes |
| H3 | `⚡ Energy Analysis` | first screen with `Attribution Coverage & Residual Energy` and the main energy-mix visual | best proof that Energy story is honest, not black-box | yes | yes |
| H4 | `🎯 Operational Decision Support` | `Opportunity Worklist` first screen | best operator-facing prioritization proof | yes | yes |
| H5 | `🤖 Efficiency Prediction & Governance` | first screen with `Active Model Summary` and `Selected-Month Inference Readiness` | best framing for current ML evidence and active-artifact status | yes | yes |
| H6 | `🔧 Maintenance` | `Maintenance Coverage Snapshot` first screen | best evidence-chain closing shot | yes | yes |

### Required flagship close-ups

| ID | Module | Exact capture target | Preferred machine / month | Why this close-up matters |
|---|---|---|---|---|
| D1 | `🔄 ETL Pipeline` | `🎯 Target Month Confirmation` with detection cards and final confirmed month | current rehearsal month | shows one-month-write semantics clearly |
| D2 | `⚡ Energy Analysis` | `Machines to Review First` with selected machine context visible | current rehearsal month | gives a bridge from Energy story to machine review |
| D3 | `🎯 Operational Decision Support` | `Model-Backed Intervention Preview` with selected-machine review context still visible | `024-081`, `June 2025` if still clean at rehearsal | flagship action-evidence visual |
| D4 | `🤖 Efficiency Prediction & Governance` | `Model Review Queue` | current rehearsal month | proves ML page role as reviewer-facing queue |
| D5 | `🤖 Efficiency Prediction & Governance` | `Scenario Lab` | `166-002` or current best supported candidate | shows narrow, honest template-based scenario evidence |
| D6 | `🔧 Maintenance` | `Machine Evidence Lookup` | `166-002` | shows all-time vs recent-window contract cleanly |

Final recommended capture count: `12` images

That is enough for the main deck. More than this usually adds visual clutter rather than clarity.

## 3. What does not need to be captured

Repo code screenshots are generally unnecessary for the main deck.

Avoid using these as main-slide visuals:

- raw Python code
- raw SQL
- full audit tables
- full blocked-row tables
- raw maintenance browse tables
- `Historical Runs` dumps

Why:

- they slow the narrative down
- they invite implementation-detail questions too early
- they do not help a reviewer understand the current product story faster

## 4. One optional technical appendix slide

If one technical credibility appendix slide is needed, keep it to exactly one item:

- preferred option: a clean route/data-flow diagram
  - `app.py -> routed module -> canonical reader/helper -> fact_machine_hour / maintenance_records`

Only if the panel explicitly wants code should you use a code visual, and even then keep it narrow:

- show one short call-chain excerpt or one small template-definition excerpt
- do not show dense implementation blocks
- do not let appendix code visuals replace the main reviewer-facing product narrative

## 5. Guided live demo protocol

### Core recommendation

The presenter should drive the live demo.

Do not hand the app to the panel before the presenter has completed one guided walkthrough.

### Primary demo route

```text
ETL Snapshot
-> Canonical Operations Overview
-> Energy Analysis
-> Operational Decision Support
-> Model-Backed Intervention Preview
-> ML Review Queue or Scenario Lab
-> Maintenance Evidence
```

### Pre-demo preset rule

Use one pre-verified month and three pre-verified machine examples:

- primary month: `June 2025` unless final rehearsal proves another month is cleaner
- supported preview case: `024-081`
- honest blocked preview case: `024-105`
- maintenance-rich case: `166-002`

Evidence note:

- these are accepted planning anchors from current docs and prior smokes
- they still need one final rehearsal check before the real presentation

### Presenter sequence

1. Open `🔄 ETL Pipeline` and show `🧭 Latest Run Snapshot` only.
2. Move to `📊 Canonical Operations Overview` and show month KPI, `Coverage & Confidence Audit`, and `Energy by State (kWh)`.
3. Move to `⚡ Energy Analysis` and show attribution coverage, residual energy, and one `Machines to Review First` view.
4. Move to `🎯 Operational Decision Support`, keep `Machine family` on the rehearsed setting, and show `Opportunity Worklist`.
5. Inspect `024-081` and read the `Model-Backed Intervention Preview` with explicit no-savings wording.
6. If time allows, move to `🤖 Efficiency Prediction & Governance` and show `Model Review Queue` or `Scenario Lab`.
7. Finish on `🔧 Maintenance` with `166-002` to close the evidence chain.

### Keep collapsed unless directly asked

- `Reference & Audit`
- `Context & Diagnostics: Historical Hour Signals`
- `Supporting Evidence: Team Signals`
- raw blocked-row detail
- `Admin / Details`
- maintenance raw browse
- retraining/provenance detail

## 6. Guided panel-try protocol

### Exact recommendation

Panel manual try should happen after PPT and after the presenter-led guided live demo.

It should not happen during module-by-module explanation.

### Why

- the panel first needs the architecture and claim boundary
- then it needs one clean end-to-end proof
- only after that is a controlled interaction useful rather than disruptive

### Recommended control model

Best practice:

- presenter keeps keyboard/mouse ownership
- panel requests one change at a time
- presenter performs the change and narrates the result

If the panel explicitly insists on direct control, restrict it to one current page and one requested interaction.

### Safe interactions that are allowed

| Surface | Allowed safe interaction | Notes |
|---|---|---|
| `🔄 ETL Pipeline` | view `🧭 Latest Run Snapshot`; optionally switch to `📈 Historical Runs` for provenance only | no upload, no processing |
| `📊 Canonical Operations Overview` | switch `Select month to view` among already materialized months | do not open audit-sample exploration unless asked |
| `⚡ Energy Analysis` | change `Attention view`; change `Selected machine context` from the prepared list | keep to read-only story surfaces |
| `🎯 Operational Decision Support` | change `Machine family`; change `Inspect machine`; open preview expander content | keep to rehearsed families/machines first |
| `🤖 Efficiency Prediction & Governance` | change `Select month`; change `Select review candidate`; read `Scenario Lab` output | no retraining |
| `🔧 Maintenance` | change `Select machine`; optionally open the observed maintenance-age evidence | do not enter upload/admin paths |

### Interactions that should definitely not be handed to the panel for free exploration

| Surface | Do not allow | Why |
|---|---|---|
| `🔄 ETL Pipeline` | file upload, manual override changes, `🚀 Process ...` | write path and timing risk |
| `🤖 Efficiency Prediction & Governance` | `Retrain from canonical Gold` | changes artifacts and breaks demo scope |
| `🔧 Maintenance` | `Process Maintenance Data`, upload integration, raw browse wandering | write/admin path, timing risk |
| any page | uncontrolled switching across all sidebar pages | breaks narrative and increases blocker risk |
| any page | free exploration of unverified months/machines | may produce awkward but avoidable blockers |

## 7. Fallback behavior during live demo or panel try

### If preview is blocked

Say this directly:

> This machine currently has no safe saved-model seed row for preview, so the system blocks instead of fabricating output.

Then do one of these:

- switch to the rehearsed supported case `024-081`
- or pivot to `🤖 Efficiency Prediction & Governance` and show `Scenario Lab` on `166-002`
- or treat `024-105` as the planned honesty example and move on

### If a selected month is empty

Do this:

- immediately switch back to the pre-verified month, normally `June 2025`
- if the panel is specifically probing month availability, explain that the page is honestly stopping on a non-materialized month
- if time has already been lost, fall back to the prepared screenshot instead of reopening ETL processing scope

### If a machine has no maintenance evidence

Do this:

- say the machine currently has no matched maintenance evidence
- switch to `166-002`
- if the question is about overall coverage rather than machine detail, stay on `Maintenance Coverage Snapshot` and do not force another lookup

### If the Optimization worklist becomes empty

Do this:

- reset to the rehearsed `Machine family`
- relax support filters only if the presenter already rehearsed that exact fallback
- otherwise switch to the prepared screenshot and continue the narrative verbally

### If time compresses unexpectedly

Cut in this order:

1. skip deep Energy live browsing
2. skip ML live if Optimization preview already succeeded
3. keep Maintenance as the final evidence closure

Do not cut:

- opening claim boundary
- one backbone proof page
- one flagship live action page
- one honest final close

## 8. Final protocol summary

- screenshot strategy: `6` hero shots + `6` flagship close-ups
- code screenshots for main deck: unnecessary
- optional technical appendix: one route/data-flow diagram only
- panel try timing: after PPT and after guided live demo
- safe demo mode: presenter-controlled, one change at a time
- risky paths to avoid: ETL processing, retraining, maintenance upload/admin free exploration
