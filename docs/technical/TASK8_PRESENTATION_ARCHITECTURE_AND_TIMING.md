# Task8 Presentation Architecture And Timing

## 1. Current objective and frozen boundary

Task8 is presentation-planning support only.

This document assumes the current platform is already settled for presentation as one canonical [可信任、经过统一语义整理的 machine-hour row] backbone plus six routed modules:

- `🔄 ETL Pipeline`
- `📊 Canonical Operations Overview`
- `⚡ Energy Analysis`
- `🎯 Operational Decision Support`
- `🤖 Efficiency Prediction & Governance`
- `🔧 Maintenance`

Frozen claim boundary for this presentation:

- no solver
- no predictive-maintenance model
- no realized-savings claim from preview
- no new artifact promotion basis
- no app-logic change implied by this deck

The architecture of the talk should therefore behave like this:

```text
PPT framing
-> explain architecture and claim boundary
-> guided live demo as proof of the current workflow
-> controlled panel try on safe interactions only
-> Q&A
```

## 2. Explicit recommendation

### Preferred format

Use `PPT-first + guided live demo after`.

Do not use module-by-module live interleaving as the primary format.

### Why this is the right choice

`PPT-first + guided live demo after` is the stronger reviewer-facing structure because:

1. It lets the presenter define the current accepted scope before any live interaction appears.
2. It makes the `no solver / no predictive-maintenance / no realized-savings` boundary explicit before the panel sees action-oriented surfaces.
3. It keeps the narrative stable: architecture first, proof second, questions third.
4. It reduces risk from write-capable or time-consuming controls such as ETL processing, retraining, and maintenance upload.
5. It makes fallback easier because screenshots and slide logic remain the anchor even if one live step becomes awkward.

### Why module-by-module live interleaving is not preferred

Module-by-module interleaving is weaker here because it:

- repeatedly breaks the architecture story into small context switches
- exposes live controls before the panel has accepted what the system is and is not
- makes timing harder inside an `18-20` minute slot
- increases the chance that the panel starts treating the app as an open sandbox instead of a guided proof of current capability

## 3. Recommended timing split

### Preferred plan if Q&A is separate

Use this split:

- PPT: `9` minutes
- guided live demo: `9` minutes
- defended close / transition to separate Q&A: `1` minute

Total in-slot time: about `19` minutes

Why this is preferred:

- `9` minutes is enough to establish architecture, scope, and module roles without rushing
- `9` minutes is enough to prove the end-to-end route on live pages
- the final `1` minute protects the close so the talk does not end on an unfinished click

### Fallback plan if Q&A is inside the same `18-20` minute slot

Use this split:

- PPT: `8` minutes
- guided live demo: `6` minutes
- in-slot Q&A: `4` minutes
- defended close: `1` minute

Total in-slot time: about `19` minutes

What changes in this fallback:

- Energy stays mainly on slides instead of taking a full live segment
- the live proof narrows to `ETL Snapshot -> Overview -> Optimization preview -> Maintenance or ML`
- the presenter should keep one screenshot-backed fallback ready so Q&A does not force risky free exploration

## 4. Primary presentation flow

### Primary flow decision

Primary flow:

```text
Scope and architecture
-> ETL and canonical backbone
-> Unified / Energy story
-> Optimization
-> ML / Scenario Lab
-> Maintenance evidence
-> live proof of the same route
-> defended close
```

### Minute allocation

| Segment | Minutes | What to show | Why it belongs here |
|---|---:|---|---|
| Opening and positioning | 1.0 | title, objective, what the platform is and is not | establishes honest expectation early |
| System architecture / data flow | 1.5 | source files -> ETL -> Bronze / Silver / Gold -> routed modules | gives the panel one mental model before details |
| ETL and canonical backbone | 2.0 | ETL semantics, one-month-write rule, rerun semantics | proves that downstream pages are not disconnected dashboards |
| Unified / Energy story | 1.5 | month KPI, coverage, `Energy by State (kWh)`, residual energy | shows why the backbone is readable and why the Energy story is honest |
| Optimization + ML + Maintenance positioning | 2.0 | worklist role, review-queue role, maintenance-evidence role | separates operational support, model evidence, and maintenance context cleanly |
| Future upgrade + close of PPT section | 1.0 | roadmap headline and current-state boundary | shows ambition without blurring present capability |
| Live demo: `ETL Pipeline` | 1.5 | `🧭 Latest Run Snapshot` only | opens the demo from stable, read-only backbone proof |
| Live demo: `📊 Canonical Operations Overview` | 1.5 | KPI + `Coverage & Confidence Audit` + `Energy by State (kWh)` | confirms current month truth |
| Live demo: `⚡ Energy Analysis` | 1.5 | attribution coverage, energy mix, machine attention | proves the energy story on the routed page |
| Live demo: `🎯 Operational Decision Support` | 2.0 | `Opportunity Worklist` + selected machine review | gives the flagship operator-facing proof |
| Live demo: preview block | 1.5 | `Model-Backed Intervention Preview` | demonstrates the narrow scenario evidence contract |
| Live demo: `🤖 Efficiency Prediction & Governance` | 1.0 | `Model Review Queue` or `Scenario Lab` | clarifies that ML is review evidence, not execution |
| Live demo: `🔧 Maintenance` | 1.0 | coverage snapshot + machine evidence | closes the evidence chain |
| Final defended close | 1.0 | claims we can defend, what remains roadmap only | protects honesty at the end |

Total: about `19.0` minutes

## 5. Fallback presentation flow

### Fallback flow decision

Fallback flow:

```text
PPT carries most of the architecture and Energy story
-> live demo proves only backbone + flagship action path
-> Q&A absorbs deeper panel questions
```

### Fallback minute allocation

| Segment | Minutes | What to show | What to compress |
|---|---:|---|---|
| Opening + scope boundary | 1.0 | title, what the platform is and is not | none |
| Architecture / data flow | 1.5 | arrow-map system architecture | keep verbal explanation tight |
| ETL + canonical backbone | 1.5 | one-month-write rule, rerun semantics, month truth | no deep provenance detail |
| Unified / Energy story | 1.0 | one slide with KPI + attribution/residual story | do not do a full live Energy walk |
| Optimization / ML / Maintenance role split | 2.0 | one-slide explanation of three module roles | avoid deep field-by-field detail |
| Future upgrade + claim boundary | 1.0 | roadmap headline, honest limitation boundary | keep examples brief |
| Live demo: `ETL Snapshot` | 1.0 | latest month and next-step framing | skip upload tab |
| Live demo: `Canonical Operations Overview` | 1.5 | month truth proof | skip sample rows |
| Live demo: `Operational Decision Support` + preview | 2.5 | worklist + selected machine + preview | this remains the flagship live segment |
| Live demo: `Maintenance` or `ML` | 1.0 | pick the cleaner of the two at rehearsal time | do not force both if time is tight |
| In-slot Q&A | 4.0 | answer from prepared claim boundary and safe controls | do not open write/admin paths |
| Defended close | 1.0 | current value, honest next step | none |

Total: about `18.5-19.0` minutes

## 6. Recommended slide-vs-demo split

### What should stay in PPT

Keep these mainly in PPT:

- system architecture / data flow
- frozen claim boundary
- one-month-write ETL semantics
- module role split:
  - `Operational Decision Support` = phase-1 rule-based prioritization
  - `Efficiency Prediction & Governance` = inferable [active saved model 可以安全做出推论] coverage and review evidence
  - `Maintenance` = evidence and coverage
- future-upgrade roadmap

### What should be proven live

Keep these mainly in the guided live demo:

- `🧭 Latest Run Snapshot`
- `Coverage & Confidence Audit`
- `Attribution Coverage & Residual Energy`
- `Opportunity Worklist`
- one supported `Model-Backed Intervention Preview`
- one maintenance evidence lookup

This split keeps the demo focused on visible proof rather than on concepts that slides explain better.

## 7. Reviewer-facing presenter rules

### Rule set

- Start by telling the panel that the app is being shown as a guided workflow, not as an open sandbox.
- Use the current accepted module order unless time pressure forces the fallback route.
- Keep `Reference & Audit`, `Historical Hour Signals`, `Team Signals`, `Admin / Details`, and retraining/upload actions closed unless a direct question requires them.
- If one live surface becomes awkward, fall back to the prepared slide or screenshot instead of improvising new scope.

### Recommended transition logic

```text
ETL proves month truth
-> Overview proves the month is readable
-> Energy explains where the month went
-> Optimization decides what to review first
-> ML explains model evidence
-> Maintenance closes the evidence chain
```

## 8. Final recommendation summary

- preferred presentation split: `PPT-first + guided live demo after`
- preferred timing when Q&A is separate: `9 min PPT + 9 min demo + 1 min close`
- fallback timing when Q&A is inside the same slot: `8 min PPT + 6 min demo + 4 min Q&A + 1 min close`
- preferred primary flow: `architecture -> backbone -> energy -> optimization -> ML -> maintenance -> close`
- preferred fallback flow: keep Energy mostly on slides and keep the live proof centered on `Overview -> Optimization preview -> Maintenance or ML`
