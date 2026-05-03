# Task8 Future Upgrade Roadmap

## 1. Roadmap grounding rule

This roadmap starts from the current accepted system reality:

- one canonical [可信任、经过统一语义整理的 machine-hour row] backbone
- routed Energy / Optimization / ML / Maintenance pages already presentation-ready
- `Operational Decision Support` still phase-1 rule-based
- `Scenario Lab` and intervention preview still narrow, template-based, and active-saved-model only
- `Maintenance` still evidence-first, not predictive

So the roadmap should be presented like this:

```text
current defendable product
-> immediate hardening and productization
-> stronger model and evidence quality
-> longer-term operational intelligence expansion
```

That keeps roadmap ambition separate from today’s claim boundary.

## 2. Three-layer roadmap

### Layer map

```text
Layer 1: Immediate post-demo hardening / productization
-> Layer 2: Model quality / evidence quality upgrades
-> Layer 3: Operational intelligence expansion
```

## 3. Layer 1: immediate post-demo hardening / productization

| Upgrade | Current limitation it addresses | What enabling condition / data is needed first | Why it matters to product value |
|---|---|---|---|
| Demo-safe read-only operating mode | write-capable controls, admin paths, and reviewer-facing paths still live in the same app shell | role/profile separation, page-level capability flags, locked demo presets for month/machine defaults | safer panel demos, safer pilot usage, lower risk of accidental writes |
| Final presentation/export pack | screenshot capture is still manual and deck refresh is still presentation-operator work | standardized capture framing, export templates, optional page-level screenshot helpers | faster deck maintenance and more repeatable storytelling |
| UI/UX hardening for guided operation | current pages are presentation-ready, but they still expose some secondary surfaces that can distract a first-time reviewer | audience mode defaults, persistent collapsed-state presets, curated first-screen summaries | stronger first impression and easier handoff to non-developer presenters |
| Deployment and runtime hardening | current usage is still local Streamlit-first and presenter-controlled | environment packaging, secrets/config handling, auth boundary, cache policy, startup health checks | moves the platform from demo-ready toward pilot-ready |
| Background job governance for ETL and retraining | ETL and retraining are still manual/synchronous user actions | job orchestration, run-status tracking, artifact registry, explicit approval workflow | reduces operator friction and creates auditable production operations |

Layer 1 message for the panel:

- this layer does not change the intelligence claim
- it makes the current product safer, smoother, and easier to deploy

## 4. Layer 2: model quality / evidence quality upgrades

### Key terms used here

- `scrap` [废品 / waste quantity]
- `confidence calibration` [让模型置信度更接近真实误差分布的校准]
- `cost-sensitive ranking` [把能耗、良率、scrap、maintenance cost proxy 更明确地折算到同一个 review priority]

| Upgrade | Current limitation it addresses | What enabling condition / data is needed first | Why it matters to product value |
|---|---|---|---|
| Richer non-zero `scrap` coverage and better scrap signal | current worklist already includes scrap rate, but the signal is not yet mature enough to carry a stronger quality-cost story everywhere | better upstream quantity/event alignment, richer non-zero scrap observations, clearer month/machine-level validation rules | makes the prioritization story more financially relevant and less energy-only |
| Better confidence calibration | current confidence is useful for ordering evidence strength, but not yet positioned as a tightly calibrated operational risk signal | holdout redesign, calibration evaluation, confidence-to-error backtesting on stable month slices | helps reviewers trust “strong evidence” vs “light evidence” more appropriately |
| More reliable cost-sensitive ranking | the current Optimization score is explainable, but it is still a heuristic mixture rather than a cost-aware action value function | agreed business weights, stable cost proxies, validated outcome logging for actions taken | improves prioritization quality and makes the worklist more product-valuable to operators |
| Broader intervention templates with honest support contracts | current template scope is intentionally narrow: `Maintenance Refresh`, `Crew Support +1`, `Combined Support` | more feature support in canonical inputs, stronger template validity rules, outcome review on executed actions | expands scenario usefulness while keeping the same honesty standard |
| Better comparable-baseline logic | current ML baseline is deliberately safe and median-based, which is good for presentation rigor but conservative for operational opportunity estimation | richer peer segmentation, more stable task/material families, robust machine-family coverage checks | gives the review queue a sharper but still explainable comparison target |
| Stronger maintenance evidence leading toward a predictive-maintenance path | Maintenance is still descriptive evidence, not a predictive path | cleaner failure/repair labels, event-to-outcome linkage, maintenance horizon definition, enough positive target density | opens a defensible path from “history evidence” to “future maintenance intelligence” without overclaim |

Layer 2 message for the panel:

- this layer improves how good the evidence is
- it still does not justify solver claims unless the enabling conditions are truly met

## 5. Layer 3: longer-term operational intelligence expansion

### Key term used here

- `constraint-aware scheduling` [显式考虑 machine / shift / setup / maintenance / demand 约束的排程优化]

| Upgrade | Current limitation it addresses | What enabling condition / data is needed first | Why it matters to product value |
|---|---|---|---|
| Real `constraint-aware scheduling` engine | current `Operational Decision Support` is still phase-1 rule-based prioritization rather than true schedule generation | explicit constraints, objective function, shop-floor acceptance rules, scenario simulation environment, reliable input freshness | turns “what to review first” into “what plan should we run” |
| Closed-loop action logging and outcome learning | current preview and worklist do not yet learn from executed follow-up actions | action capture workflow, post-action KPI measurement, intervention taxonomy, causal review discipline | creates a path from scenario evidence to measurable operational learning |
| Cross-module action center | current app explains modules well, but action ownership still lives across separate pages | common action object, operator notes, status tracking, monthly review cadence | improves operator adoption and makes the platform feel like one product, not several reports |
| Multi-horizon operational intelligence | current pages are month-scoped reviewer surfaces more than rolling operational command tools | rolling window design, alert thresholds, stable daily/weekly refresh policy, deployment/runtime maturity | increases business usefulness between monthly review cycles |
| Deployment-grade collaboration and governance | current workflow is presenter/operator friendly, but not yet a full governed collaboration product | auth, roles, audit logs, artifact/version governance, shared deployment environment | allows controlled expansion from demo usage to team usage |

Layer 3 message for the panel:

- this is where the platform can later become operational intelligence infrastructure
- but these claims belong to the roadmap, not to the current presentation of the app

## 6. How to present the roadmap honestly

### Recommended phrasing

Use this progression:

1. `Today we can defend the backbone, the review workflow, and the evidence chain.`
2. `Next we would harden the product experience and operating safety.`
3. `After that we would improve evidence quality and model reliability.`
4. `Only then would stronger scheduling or predictive claims become appropriate.`

### What to avoid

Avoid phrasing like:

- `the next version will optimize the factory automatically`
- `we only need minor polish before predictive maintenance`
- `the solver is basically the next easy step`
- `the preview already proves the roadmap direction`

## 7. Final roadmap summary

- Layer 1 upgrades make the current product safer and more deployable
- Layer 2 upgrades make the evidence and ranking more trustworthy
- Layer 3 upgrades expand into genuine operational intelligence only after data and governance maturity catches up

That is the strongest ambitious-but-defensible roadmap framing for the current system state.
