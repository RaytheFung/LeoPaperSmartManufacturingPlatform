# Task8 Per-Slide Speaker Notes

## Slide 1. One Canonical Backbone, Multiple Reviewer-Facing Lenses

- Slide title: `One Canonical Backbone, Multiple Reviewer-Facing Lenses`
- Purpose: 先用一句话把平台定位清楚，让 panel 知道这不是六个分离的小工具。
- What visual should appear: title slide + 六个 routed modules 的简洁流程条。
- Key message: 平台的价值在于把 monthly manufacturing data 整理成一个 canonical [可信任、经过统一语义整理的 machine-hour row] backbone，再从同一 backbone 展开多个 reviewer-friendly analytical lenses。
- Speaker bullets:
  - 今天我不会把系统讲成六个孤立页面，我会把它讲成一个统一 workflow。
  - 核心主干是 `fact_machine_hour`，不是临时拼接图表。
  - 六个 routed modules 只是从同一 truth 出发的不同观察角度。
  - 我会明确分开 current defendable system 和 future upgrade roadmap。
- Transition sentence to the next slide: `在进入 architecture 之前，我先把 current claim boundary 讲清楚。`
- Do not overclaim: 不要把平台开场就说成 fully autonomous optimization platform。

## Slide 2. What We Can Defend Today

- Slide title: `What We Can Defend Today`
- Purpose: 先把 defendable claims 和 avoid claims 讲清楚，避免 panel 用错误期待看后面的 live demo。
- What visual should appear: 左右两栏对照，左边 `Can defend`，右边 `Should avoid`。
- Key message: 当前系统是可演示、可解释、边界明确的 analytics platform，不是 solver，也不是 predictive-maintenance engine。
- Speaker bullets:
  - 当前 accepted baseline 已经从 rebuild 转到 presentation-preparation stage。
  - `🎯 Operational Decision Support` 是 phase-1 rule-based support，不是 constraint-aware scheduling。
  - `🤖 Efficiency Prediction & Governance` 使用 active saved artifacts，但 preview 不是 realized saving。
  - `🔧 Maintenance` 现在是 evidence-and-coverage-first，不是 predictive-maintenance model。
  - blocked case 应该被当成 honest boundary，而不是要被隐藏的瑕疵。
- Transition sentence to the next slide: `接下来我用一张 architecture 图说明，这些边界为什么在系统结构上是合理的。`
- Do not overclaim: 不要说 blocked case 只是 UI bug 或暂时没算出来。

## Slide 3. System Architecture / Data Flow

- Slide title: `System Architecture / Data Flow`
- Purpose: 给 panel 一个稳定的全局心智模型。
- What visual should appear: arrow map `Energy + CSI + MES files -> ETL -> Bronze -> Silver -> Gold fact_machine_hour -> six routed modules`，另一路 `maintenance_records -> Maintenance + reused context`。
- Key message: 系统的可信度来自清楚的数据流，不来自单一漂亮图表。
- Speaker bullets:
  - ETL 先处理 monthly source files，再写入 Bronze [原始落地层]、Silver [source-specific canonical tables]、Gold [跨 source 的 machine-hour backbone]。
  - 主要 routed analytics 都从 `fact_machine_hour` 读取，而不是从 legacy `unified_view` 回退。
  - `maintenance_records` 走的是 evidence chain，它服务 `Maintenance` 页面，也复用到 ML 和 Optimization context。
  - 这个结构解释了为什么我们能同时做到 unified month truth、energy story、review priority 和 maintenance evidence closure。
- Transition sentence to the next slide: `既然 backbone 是这样建立的，第一张必须让 panel 信任的页面就是 ETL 和 canonical backbone。`
- Do not overclaim: 不要把 maintenance table 说成已经形成 failure labels 或 predictive target。

## Slide 4. ETL And Canonical Backbone

- Slide title: `ETL And Canonical Backbone`
- Purpose: 解释为什么 ETL 是整场 presentation 的第一站。
- What visual should appear: `🧭 Latest Run Snapshot` hero shot + 一个小型 `Target Month Confirmation` close-up。
- Key message: 系统先确认 month truth，再进入任何分析页面。
- Speaker bullets:
  - ETL 的职责不是做复杂可视化，而是确定这个月到底被写成什么 truth。
  - target month detection 是 filename-first，必要时才做 workbook-sample fallback。
  - 如果 month/year signals 冲突，系统会 block processing，而不是偷偷继续。
  - same-month rerun 会 replace active month snapshot，不是双版本 toggle。
  - 这一步讲清楚后，后面的 `Overview`、`Energy`、`Optimization` 才有可信基础。
- Transition sentence to the next slide: `确认 backbone 之后，下一步不是马上讲智能，而是先证明这个月的 canonical truth 本身可读。`
- Do not overclaim: 不要把 `Historical Runs` 说成 rollback or version-control system。

## Slide 5. Unified / Energy Story

- Slide title: `Unified / Energy Story`
- Purpose: 把 `📊 Canonical Operations Overview` 和 `⚡ Energy Analysis` 合成一个 reviewer-friendly story。
- What visual should appear: 左侧 `Canonical Gold Month View` + `Coverage & Confidence Audit`，右侧 `Attribution Coverage & Residual Energy` 与 `Energy by State (kWh)`。
- Key message: 先证明这个月 readable，再解释 energy 去了哪里，以及哪些部分被诚实保留为 residual / unallocated。
- Speaker bullets:
  - `Overview` 页的任务是证明 selected month 的 KPI、coverage、state attribution 已经足以支持解释。
  - `Weighted kWh / Good Unit` 是 weighted ratio，不是简单 row mean。
  - `Energy Analysis` 最重要的价值不是图多，而是它把 attributed energy 和 residual energy 分开讲清楚。
  - `Machines to Review First` 是 attention lens，不是 solver recommendation。
  - 这张 slide 让 panel 理解：平台不是黑箱，它会保留不知道的部分，而不是硬分配。
- Transition sentence to the next slide: `在知道 energy story 之后，panel 最自然的问题就是，那我该先看哪台 machine。`
- Do not overclaim: 不要把 residual energy 讲成系统失败，也不要把 machine attention 讲成自动行动建议。

## Slide 6. Operational Decision Support

- Slide title: `Operational Decision Support`
- Purpose: 解释系统如何把 month-level story 转成 machine-level review priority。
- What visual should appear: `Opportunity Worklist` + `Selected Machine Review` + preview highlight card。
- Key message: `🎯 Operational Decision Support` 提供 deterministic worklist，不提供排程承诺。
- Speaker bullets:
  - worklist 的价值是把 review priority 排清楚，而不是直接给出 production schedule。
  - 目前 score 来自 energy intensity、non-productive share、maintenance recency、scrap [废品 / waste quantity] rate 的组合。
  - presenter 应该重点讲 `Top Driver` 和 `Recommended Action`，这样 panel 比较容易理解 why this machine first。
  - `Model-Backed Intervention Preview` 放在 selected-machine review 里，是为了让 action discussion anchored to one real case。
  - 推荐用 `024-081` 作为 supported example，再用 `024-105` 作为 honest blocked example。
- Transition sentence to the next slide: `不过这页强调的是 operational priority，接下来我要把 model evidence 本身独立出来。`
- Do not overclaim: 不要把这页说成 constraint-aware scheduling 或 optimization engine。

## Slide 7. ML Review Queue / Scenario Lab

- Slide title: `ML Review Queue / Scenario Lab`
- Purpose: 把 ML 页定位成 evidence and governance，而不是执行控制台。
- What visual should appear: `Active Model Summary`、`Selected-Month Inference Readiness`、`Model Review Queue`，以及一张 `Scenario Lab` close-up。
- Key message: ML 页回答的是 inferable [active saved model 可以安全做出推论] coverage、review priority、scenario evidence，不是“模型帮你执行什么”。
- Speaker bullets:
  - active artifacts 仍然是 `Task 4L` saved bundle，presentation 里不应该暗示有新 promotion。
  - `Selected-Month Inference Readiness` 讲的是 current-month coverage，不是 retraining readiness。
  - `Model Review Queue` 把 predicted excess、confidence、support path 合成 deterministic review priority。
  - `Scenario Lab` 只比较安全模板：`Maintenance Refresh`、`Crew Support +1`、`Combined Support`。
  - unsupported scenario 仍然保留并诚实显示，这一点本身就是 reviewer-facing strength。
- Transition sentence to the next slide: `有了 model evidence 之后，最后还需要一个独立的 maintenance evidence closure。`
- Do not overclaim: 不要把 preview 说成 realized saving、executed intervention、或 guaranteed improvement。

## Slide 8. Maintenance Evidence Closure

- Slide title: `Maintenance Evidence Closure`
- Purpose: 用 maintenance history 把整场故事收拢到 evidence chain，而不是再开一个预测新战场。
- What visual should appear: `Maintenance Coverage Snapshot` + `Machine Evidence Lookup`，建议使用 `166-002`。
- Key message: `🔧 Maintenance` 页面告诉 panel 现有 maintenance evidence 的覆盖和 machine-level history 深度。
- Speaker bullets:
  - 这页最值得强调的是 coverage contract，而不是复杂图形。
  - 页面明确区分 `Total Events (All Time)` 和 `Recent Events Shown`，避免历史范围混淆。
  - maintenance context 也会被复用到 ML 与 Optimization，但不会改写它们的 ranking logic。
  - 这页最适合放在 presentation 后段，作为 evidence closure，而不是开场主舞台。
- Transition sentence to the next slide: `前面的 slides 讲完 current system，现在我把 live demo route 和 panel interaction protocol 说清楚。`
- Do not overclaim: 不要把 maintenance history 讲成 failure prediction or PM threshold engine。

## Slide 9. Live Demo Route And Safe Panel Interaction

- Slide title: `Live Demo Route And Safe Panel Interaction`
- Purpose: 让 panel 知道 live demo 是 guided proof，不是自由探索。
- What visual should appear: timeline `ETL Snapshot -> Overview -> Energy -> Optimization -> ML -> Maintenance`，旁边一列 `Safe interactions only`。
- Key message: presenter 必须保留 narrative control，panel try 只能发生在安全、只读、预演过的 interactions 上。
- Speaker bullets:
  - live demo 的顺序要跟 slides 保持一致，这样 panel 不需要重新建立心智模型。
  - panel manual try 最好放在 PPT 和 presenter-led demo 之后，而不是模块讲解中间。
  - 安全 interaction 主要是 month dropdown、attention view、machine family、inspect machine、review candidate、maintenance machine selection。
  - upload、retrain、maintenance processing、`Admin / Details` free exploration 都不应该开放给 panel。
  - 如果某个 preview blocked，要把 blocked case 当 honesty proof，而不是临场硬修。
- Transition sentence to the next slide: `current system 到这里为止已经完整，最后一张谈 future upgrade 应该怎么讲才 ambitious but defensible。`
- Do not overclaim: 不要把 live demo 说成 unrestricted sandbox or user-acceptance free play。

## Slide 10. Future Upgrade Roadmap

- Slide title: `Future Upgrade Roadmap`
- Purpose: 告诉 panel 这个平台接下来可以走到哪里，同时保持 roadmap 和 current truth 分离。
- What visual should appear: 三层 roadmap，分别是 post-demo hardening、model/evidence quality、operational intelligence expansion。
- Key message: roadmap 的价值在于把 limitation -> enabling condition -> product value 连起来，而不是列 generic wishlist。
- Speaker bullets:
  - 第一层先做 hardening 与 productization，让 demo-safe workflow 变成 deployment-safe workflow。
  - 第二层做 data and model quality，例如 richer scrap signal、better confidence calibration、broader intervention templates。
  - 第三层才是更高阶的 operational intelligence，例如真正的 constraint-aware scheduling 与 predictive-maintenance path。
  - 每个 upgrade 都要先讲当前 limitation，再讲需要什么 data / label / workflow 才能落地。
- Transition sentence to the next slide: `所以最后我不会用 roadmap 盖过 current system，而是回到今天真正能 defend 的内容。`
- Do not overclaim: 不要把 roadmap 讲成已经 committed delivery plan 或已验证 capability。

## Slide 11. Conclusion / Claims We Can Defend

- Slide title: `Conclusion / Claims We Can Defend`
- Purpose: 用最短的 closing 把 current value、honest boundary、next step 一次说完。
- What visual should appear: 四条 defendable claims + 四条 avoid claims，底部一行 closing message。
- Key message: 当前平台已经能把 month truth、canonical analytics、review evidence、maintenance evidence 连接成一个稳定、诚实、可演示的 workflow。
- Speaker bullets:
  - 我们今天真正证明的是 one canonical backbone plus guided analytical lenses。
  - 我们证明了 system can explain, prioritize, and block honestly when support is missing。
  - 我们没有把 current system 误讲成 solver、predictive-maintenance engine、或 realized-savings calculator。
  - 下一步应该是 final deck assets、fresh screenshots、timed rehearsal，再之后才是 roadmap execution。
- Transition sentence to the next slide: `none`
- Do not overclaim: 结尾必须回到 current-state truth，而不是用 future upgrade 抢掉现在的边界。
