# Task7 Presentation Route And Slide Support

## 1. Concise storyline

建议把整套平台讲成一条连续故事，而不是六个独立页面：

1. 先建立 month truth  
   `ETL Pipeline` 负责把当月 source files 落成 canonical backbone。
2. 再证明 backbone 可读  
   `Canonical Operations Overview` 负责让观众先信任这个月的 `fact_machine_hour`。
3. 然后讲 energy story  
   `Energy Analysis` 负责解释“哪里耗能、多少可归因、哪些 machine 值得先看”。
4. 再讲行动优先级  
   `Operational Decision Support` 负责给 operator 一个 deterministic worklist。
5. 再讲 model evidence  
   `Efficiency Prediction & Governance` 负责解释 active model 的 current-month coverage 与 review evidence。
6. 最后讲 maintenance evidence  
   `Maintenance` 负责补完 machine history 与 coverage closure。

一句话版本：

> 我们先把月度制造数据整理成一个可信的 canonical machine-hour backbone，再从同一 backbone 分别看 operations、energy、review priority、model evidence 与 maintenance evidence。

## 2. Proposed slide-to-module mapping

| Slide | Title idea | 对应模块 | 核心 message |
|---|---|---|---|
| 1 | Problem & Scope | none | 平台目标是统一月度制造资料，并提供 reviewer-friendly analytics，而不是做 solver |
| 2 | End-to-End Data Backbone | `🔄 ETL Pipeline` | filename-first detection -> ETL storage -> Silver -> Gold `fact_machine_hour` |
| 3 | Canonical Month Truth | `📊 Canonical Operations Overview` | 先确认 selected month 的 KPI、coverage、energy-by-state |
| 4 | Energy Whereabouts | `⚡ Energy Analysis` | 解释 energy mix、attribution coverage、residual honesty |
| 5 | Machines To Review First | `⚡ Energy Analysis` / `🎯 Operational Decision Support` | 先从 energy attention 过渡到 machine-level worklist |
| 6 | Operational Decision Support | `🎯 Operational Decision Support` | worklist + top driver + recommended action |
| 7 | Model-Backed Intervention Preview | `🎯 Operational Decision Support` | one comparable row, active saved model, narrow templates, no realized-saving claim |
| 8 | Prediction Governance & Review Coverage | `🤖 Efficiency Prediction & Governance` | active artifact summary + inference readiness + Model Review Queue |
| 9 | Maintenance Evidence Closure | `🔧 Maintenance` | evidence coverage + machine history + all-time vs recent window |
| 10 | What We Can Defend | all | claims we can defend vs claims we avoid |

## 3. Recommended live-demo route

### Primary route

`Latest Run Snapshot -> Canonical Operations Overview -> Energy Analysis -> Operational Decision Support -> Efficiency Prediction & Governance -> Maintenance`

### Why this route works

- 它先让观众接受 backbone，再接受 analytics
- 它把最强的 live-demo page 放在中段：`Energy` 和 `Operational Decision Support`
- 它把 `ML` 定位成 evidence/governance，而不是重复 `Optimization`
- 它把 `Maintenance` 放到后段做 closure，更容易守住“不是 predictive-maintenance model”的边界

## 4. Screenshot capture list

最值得截图的不是“每个页面都截一张”，而是“每个页面只截最能代表 story 的那一块”。

### Must-capture screenshots

- `🔄 ETL Pipeline`
  - `🧭 Latest Run Snapshot`
  - 理由：这是最好的 backbone-opening slide
- `📊 Canonical Operations Overview`
  - KPI cards + `Energy by State (kWh)`
  - 理由：可以一页证明 Gold backbone 已经可读
- `⚡ Energy Analysis`
  - `Attribution Coverage & Residual Energy`
  - `Energy Mix & Machine Attention`
  - 理由：最适合讲“为什么这不是黑箱”
- `🎯 Operational Decision Support`
  - `Opportunity Worklist`
  - `Selected Machine Review`
  - 理由：最适合讲 operator action flow
- `🎯 Operational Decision Support`
  - `Model-Backed Intervention Preview`
  - 理由：这是 flagship preview block
- `🤖 Efficiency Prediction & Governance`
  - `Active Model Summary`
  - `Selected-Month Inference Readiness`
  - `Model Review Queue`
  - 理由：把 ML 从“看不懂的图”改成 reviewer-friendly story
- `🔧 Maintenance`
  - `Maintenance Coverage Snapshot`
  - `Machine Evidence Lookup`
  - 理由：最适合讲 all-time vs recent-window contract

### Optional screenshots

- `Historical Runs`
- `Reference & Audit: Detailed attribution categories`
- `Historical Hour Signals`
- `Supporting Evidence: Team Signals`
- `Supporting Evidence: All template outcomes`

## 5. Reusable slide captions

以下文案可以直接复用或轻改：

### ETL / backbone

- `One month in, one canonical month out.`
- `The platform writes one active month truth, not multiple competing month versions.`
- `ETL detection is filename-first and blocks on conflicting month/year signals.`

### Canonical overview

- `Canonical Operations Overview is the first reviewer-facing checkpoint after ETL.`
- `The page reads fact_machine_hour only and does not fall back to legacy unified_view.`
- `Weighted kWh / Good Unit is a weighted ratio, not a simple average of row-level ratios.`

### Energy

- `Energy Analysis explains where monthly energy goes and how much remains explicitly residual.`
- `Residual energy is kept visible instead of being forced into a misleading operating-state bucket.`
- `Machine attention views help focus review, but they are not solver outputs.`

### Optimization

- `Operational Decision Support is phase-1 rule-based prioritization, not a scheduling solver.`
- `Opportunity Score combines energy intensity, non-productive share, maintenance recency, and scrap rate.`
- `Recommended Action is the practical operator-facing summary of the selected machine review.`

### Preview

- `The intervention preview is based on one real comparable machine-hour seed row.`
- `Best delta is calculated at the seed row's current comparable production volume.`
- `This is a model-backed scenario preview only, not a realized saving or executed plan.`

### ML governance

- `The ML page explains selected-month inference readiness and review evidence, not execution priority.`
- `Blocked rows remain visible as supporting evidence rather than being hidden or fabricated away.`
- `The active artifacts remain the Task 4L saved bundle; no new promotion is being claimed here.`

### Maintenance

- `Maintenance now leads with evidence coverage and machine history, not a predictive-maintenance claim.`
- `Recent Events Shown is a readability window, not the machine's all-time history count.`
- `Maintenance evidence is reused on ML and Optimization pages without re-scoring their outputs.`

## 6. Example machines to use in slides or live walkthrough

这些 machine 适合当前 presentation support pack：

- `024-081`
  - 用途：supported preview case
  - 适合展示 `Operational Decision Support` 的完整路径
- `024-105`
  - 用途：honest blocked preview case
  - 适合展示“系统不支持时不会 fabricate output”
- `166-002`
  - 用途：maintenance-rich case
  - 适合展示 `Maintenance` 页的 machine evidence contract

使用原则：

- 一个 supported case
- 一个 blocked case
- 一个 maintenance-rich case

这样 slide / live demo 都会更完整，也更诚实。

## 7. What to emphasize module by module

| Module | 主强调点 | 可弱化点 |
|---|---|---|
| ETL | month truth、conflict blocking、rerun semantics | partial-match tables |
| Canonical Overview | KPI、coverage、energy-by-state | audit sample rows |
| Energy | attribution coverage、energy mix、machine attention | daily / hourly appendix |
| Optimization | worklist、top driver、recommended action、preview boundary | full scored table |
| ML | active artifact、readiness、review queue | deep governance details |
| Maintenance | coverage snapshot、machine evidence | legacy risk/admin section |

## 8. Honest limitations to state explicitly

这些限制最好直接放一页，不要等问答才说：

- `Operational Decision Support` is not a solver.
- `Model-Backed Intervention Preview` is not a realized-saving engine.
- `Maintenance` is not a predictive-maintenance model.
- The current active ML artifacts remain the saved `Task 4L` bundle.
- Same-month reruns replace the active month snapshot; the system does not expose dual active month versions.
- Some machines will honestly block on preview because no eligible canonical seed row exists for the current month.

## 9. Claims we can defend vs claims we should avoid

### Claims we can defend

- The routed analytics pages are now anchored to canonical `fact_machine_hour`.
- The platform keeps residual / unallocated energy explicit.
- The ML and preview pages use the active saved model only.
- The optimization page is deterministic and explanatory.
- The maintenance page is evidence-and-coverage-first.

### Claims we should avoid

- “The system automatically optimizes the production schedule.”
- “The preview already proves realized monthly energy savings.”
- “The maintenance module predicts failure risk for operations.”
- “A blocked preview means the system is broken.”
- “Deleting an ETL history record rolls back the active canonical month.”

## 10. Short Q&A support prompts

如果现场被问到以下问题，可以用这些短句：

### “Why is this not a solver?”

> Because the current accepted scope is deterministic prioritization support built on canonical month summaries, not constraint-aware scheduling optimization.

### “Why is this preview not the same as savings?”

> Because it is calculated on one comparable machine-hour seed row at that row’s current volume, using the active saved model only.

### “Why do some machines block?”

> Because the system requires an eligible canonical seed row and a real saved-model path; when that support is missing, it blocks instead of fabricating output.

### “Why is maintenance not predicting?”

> The current maintenance scope is evidence and coverage first. It supports interpretation, but it is not being presented as a predictive-maintenance model.

## 11. Recommended closing message

建议最后一页或最后一句话这样收：

> 这个平台的价值不在于夸张地宣称 fully autonomous optimization，而在于把 ETL truth、canonical analytics、model evidence 与 maintenance evidence 连接成一个稳定、诚实、可演示的 operator workflow。
