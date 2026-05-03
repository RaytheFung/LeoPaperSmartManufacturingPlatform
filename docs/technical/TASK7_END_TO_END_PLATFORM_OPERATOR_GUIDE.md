# Task7 End-to-End Platform Operator Guide

## 1. Current accepted system state

### 1.1 平台现在是什么

当前平台是一个以 `fact_machine_hour` 为唯一主干的 Smart Manufacturing Analytics Platform。它不是一组彼此分离的小页面，而是一个单一 canonical [可信任、经过统一语义整理的 machine-hour row] 数据骨架，再从这个骨架分流到六个 routed modules：

- `🔄 ETL Pipeline`
- `📊 Canonical Operations Overview`
- `⚡ Energy Analysis`
- `🤖 Efficiency Prediction & Governance`
- `🎯 Operational Decision Support`
- `🔧 Maintenance`

当前 accepted baseline 是 presentation-preparation stage，不是继续 rebuild stage。换句话说，系统重点已经从“继续改算法/改结构”转成“稳定操作、诚实解释、便于演示”。

### 1.2 当前 live boundary

以下边界目前必须保持清楚：

- no artifact promotion  
  现行 active artifacts 仍是 `Task 4L` 保存的 bundle；Task 7 不重新训练、不提升新 artifacts，也不把任何候选结果说成新的 active truth。
- no solver  
  `🎯 Operational Decision Support` 是 phase-1 rule-based decision support，不是 constraint-aware scheduling solver。
- no predictive-maintenance model  
  `🔧 Maintenance` 现在是 evidence-and-coverage-first 页面，不是 predictive-maintenance model。
- no duplicate active month data  
  同一个月份 rerun 时，会覆盖该月 active ETL/canonical snapshot；系统没有双 active month toggle。

### 1.3 什么是 direct-source-verified，什么是 evidence-based

Task 7 文档必须区分两类事实：

| 类型 | 本指南中代表什么 | 本次已用到的例子 |
|---|---|---|
| direct-source-verified | 直接从 live repo code、live SQLite、active model provenance、当前 screenshot 文件本身读到的事实 | `app.py` route labels、`fact_machine_hour` month coverage、`models/*.provenance.json`、`maintenance_records` row count、preview 字段名 |
| evidence-based | 来自已通过 task reports、AppTest smoke、manual-review packet、read-only demo smoke 的事实 | `024-081` 作为 supported preview 例子、`024-105` blocked preview 例子、Task4T-6E smoke counts |

如果你在 presentation 里要说“这个页面现在显示什么”，优先用 direct-source-verified。  
如果你要说“这个 machine 在某次 June 2025 smoke 里曾经如何表现”，那是 evidence-based，要明确语境。

### 1.4 当前 live data / artifact anchors

以下是本次 Task 7 直接读到的 live anchors：

- `manufacturing_data.db`
  - `fact_machine_hour` 覆盖 `2025-01` 到 `2025-06`
  - 总 row 数 `378,352`
  - 全期间 distinct machines `88`
  - `June 2025` row 数 `62,639`，distinct machines `87`
- `maintenance_records`
  - stored rows `14,378`
  - matched machine count `61`
  - month coverage `20`
  - earliest stored maintenance `2024-01-02 08:55:53.713000`
  - latest stored maintenance `2025-08-14 17:27:59.583000`
- active ML artifacts
  - `models/production_efficiency_model.pkl`
  - `models/production_preprocessor.pkl`
  - active `artifact_version_id = 20260401_000808`
  - selected model `random_forest`
  - provenance `task_tag = Task 4L`

### 1.5 当前 frozen / intentionally out of scope

- 不改 routed application logic
- 不重训 models 作为本任务输出
- 不 promote 新 artifacts
- 不写 `manufacturing_data.db`
- 不回到 quantity/anomaly policy scope
- 不把 `Operational Decision Support` 包装成 solver
- 不把 `Maintenance` 包装成 predictive-maintenance engine
- 不把 screenshot/example 说成固定 live benchmark

## 2. Whole-platform workflow map

### 2.1 ETL-led data workflow

```text
Upload monthly Energy + CSI + MES files
-> detect month/year from filename first
-> manual confirmation when needed
-> write ETL storage + Bronze raw tables
-> materialize Silver tables
-> rebuild selected-month Gold partition in fact_machine_hour
-> inspect Latest Run Snapshot
-> move into routed analytics pages
```

### 2.2 Canonical analytics workflow

```text
fact_machine_hour
-> CanonicalGoldReader
-> Canonical Operations Overview
-> month KPI / coverage audit / energy-by-state summary
```

### 2.3 Energy workflow

```text
fact_machine_hour
-> CanonicalEnergyReader
-> state energy attribution
-> attribution coverage + residual energy
-> machine attention views
-> daily / maintenance / hourly supporting context
```

### 2.4 ML review workflow

```text
fact_machine_hour
-> CanonicalMLReader
-> build month input rows
-> block unsupported rows honestly
-> latest eligible row per machine
-> active saved predictor only
-> Model Review Queue
-> Scenario Lab
```

### 2.5 Optimization review workflow

```text
fact_machine_hour
-> CanonicalOptimizationReader
-> month-scoped machine summary
-> deterministic opportunity score
-> Opportunity Worklist
-> selected machine review
-> Model-Backed Intervention Preview if a valid seed row exists
```

### 2.6 Maintenance evidence workflow

```text
maintenance_records
-> MaintenanceEvidenceReader
-> coverage snapshot
-> machine evidence lookup
-> recent history window
-> compact evidence context reused on ML / Optimization
```

## 3. Key terms you should understand first

下列词在操作和讲解时会频繁出现；第一次看到就先用这个意思理解：

| Term | 快速解释 |
|---|---|
| canonical | canonical [可信任、经过统一语义整理的 machine-hour row]，不是 raw row，也不是 UI 临时拼接结果 |
| Bronze | Bronze [原始落地层]，尽量保存 source truth，不急着做业务解释 |
| Silver | Silver [source-specific canonical tables]，每个 source 先整理成可用结构 |
| Gold | Gold [跨 source 的统一 machine-hour backbone]，当前就是 `fact_machine_hour` |
| support path | support path [模型推论时输入有多直接，分成 `Direct canonical row` / `Adapted row` / `Defaulted row`] |
| inferable | inferable [active saved model 可以安全做出推论] |
| preview | preview [模型情境预览，不等于实际执行或已实现节省] |
| weighted kWh / Good Unit | weighted kWh / Good Unit [用 `sum(energy_total_kwh) / sum(good_qty)` 计算，不是简单平均 row ratio] |
| residual / unallocated energy | residual / unallocated energy [有 energy，但当下 canonical state evidence 不足以把它放进具体 operating state] |
| eligible rows | eligible rows [在当前页面的支持规则下可纳入计算/排序的 rows] |
| recent window | recent window [为了可读性只展示最近一段 history，不代表 all-time 全部 history 被删除] |

## 4. Guided ETL workflow

### 4.1 为什么 ETL 一定是第一站

`🔄 ETL Pipeline` 是整个系统的入口，因为下游五个页面都依赖它产出的 month-scoped truth：

- ETL/provenance tables 让你知道“这个月到底处理了什么”
- Bronze/Silver/Gold 让 routed analytics pages 有正式数据骨架
- 如果 ETL 没跑对，后面的 `Energy` / `ML` / `Optimization` / `Maintenance context reuse` 都只会变成误读

所以标准操作顺序不是“先看 024-081 有没有 preview”，而是：

`先确认当月 ETL truth -> 再进入 analytics page`

### 4.2 Upload New Data 怎么走

标准操作：

1. 打开 `🔄 ETL Pipeline`
2. 在 `📤 Upload New Data` 上传：
   - Energy files
   - CSI file
   - MES file
3. 查看 `Detected Month`、`Detected Year`、`Detection Source`、`Confidence`
4. 只在需要时开启 `Use manual override for the target month/year`
5. 在 `Final month to write` / `Final year to write` 做最终确认
6. 点击 `🚀 Process {Month Year}`
7. 处理完成后检查 `Canonical Silver` / `Canonical Gold` 是否成功

### 4.3 一个实操例子

如果你准备演示 `June 2025`：

1. 先上传 June 的 Energy / CSI / MES 月度文件
2. 确认页面是否自动识别出 `June 2025`
3. 如果 month 被识别出，但 year 没有可靠读出，就手动确认 `2025`
4. 点 `Process June 2025`
5. 成功后不要马上跳去 ML，先看 `🧭 Latest Run Snapshot`
6. 再进入 `📊 Canonical Operations Overview` 做当月 backbone 确认

这个顺序比较适合现场 demo，因为它让观众先接受“数据 backbone 已经确定”，再看智能模块。

### 4.4 Month/year detection 是怎么工作的

当前 ETL detection contract：

- filename first  
  优先从上传文件名推断 month/year
- workbook-sample fallback  
  只有在 filename 信息不够时，才对 `.xlsx` / `.xlsm` 做窄范围 sample 读取
- conflict blocking  
  如果不同文件指向不同 month/year，页面会 block processing，而不是偷偷继续
- manual override visible  
  即使自动识别成功，manual override 也保持可见

### 4.5 ETL 会把什么写进 SQLite / supporting tables

#### A. ETL / provenance tables

- `etl_runs`
- `machine_inventory`
- `three_way_matches`
- `machine_monthly_presence`
- `etl_energy_data`
- `etl_csi_data`
- `etl_mes_data`

这些表主要回答：

- 这次 run 是什么月份
- matching 结果如何
- 哪些 machine 在这个月出现
- 当前 provenance / historical comparison 是什么

#### B. Bronze raw tables

通过 `BronzeRawStore` 写入：

- `raw_energy_hourly`
- `raw_csi_event`
- `raw_mes_report`
- `raw_maintenance_txn`  
  只有 maintenance 被一起整合或单独上传时才会更新

#### C. Silver tables

通过 `CanonicalMaterializer` 写入：

- `energy_meter_hour`
- `csi_job_event`
- `mes_report_event`
- `maintenance_txn_event`

#### D. Gold table

- `fact_machine_hour`

这就是所有 canonical routed analytics pages 的正式 backbone。

### 4.6 `Latest Run Snapshot` 是干什么的

`🧭 Latest Run Snapshot` 不是第二个“历史列表”，它回答三个现场最有用的问题：

- 刚刚最后一次处理的是哪个月
- 相比上一个 distinct month，有没有 gained / lost three-way matches
- 接下来操作员该做什么

当前 live snapshot 例子：

- latest month: `June 2025`
- run records retained for that month: `3`
- previous distinct month: `May 2025`
- gained matches vs previous month: `1`
- lost matches vs previous month: `1`

### 4.7 `Historical Runs` 是干什么的

`📈 Historical Runs` 的定位是 provenance [过程留痕]，不是 active truth switcher。

它适合做的事：

- 看历史 run 记录
- 做 presentation comparison
- 下载/整理 run-level 结果
- 管理 log 顺序

它不适合被解释成：

- 月份版本切换器
- canonical rollback 机制
- “我删掉这条 run record 就会把 `fact_machine_hour` 回退”的工具

### 4.8 Rerun / replacement semantics

这一点必须讲清楚：

- rerun 同一个月份时，`etl_energy_data` / `etl_csi_data` / `etl_mes_data` 的同月数据会被替换
- canonical materialization 对该月走 full-overlay month replace
- 同一个月不会在 active runtime 里保留两套并列 truth
- `Historical Runs` 里保留的 run records 只是 provenance records

### 4.9 如果用户期待 deletion / toggle / rollback

要诚实讲：

- UI 有删除 ETL run record 的操作，但那是删 `etl_runs` record，不是 rollback `fact_machine_hour`
- 当前系统没有“保留两个 active June 版本并在前端切换”的设计
- 当前系统也没有正式 exposed 的 one-click rollback for canonical month partition

推荐说法：

> 这个系统对同月 rerun 的设计是 replace active month snapshot，不是 dual-version toggle。

## 5. Module-by-module operator guide

## 5.1 `🔄 ETL Pipeline`

### Purpose

建立当月正式 data backbone，并提供 run provenance。

### Who it is for

- 数据操作员
- demo 主讲人
- 需要确认 month truth 的 reviewer

### Where it sits in the whole flow

这是全平台第一步。

### First click / first choice

- 先看 `📤 Upload New Data`
- 或在 live demo 时先开 `🧭 Latest Run Snapshot`

### Key sections

- `📤 Upload New Data`
- `🧭 Latest Run Snapshot`
- `📈 Historical Runs`

### What the main outputs mean

- `Detected Month / Year`
  - 当前上传文件推断出的目标月份
- `Detection Source`
  - 结果是 filename 还是 workbook sample 得来的
- `Confidence`
  - 当前 detection 可信度
- `Canonical Silver / Canonical Gold`
  - 代表 materialization 是否成功

### Main story vs supporting evidence

- main story
  - 当月 source data 是否被稳定写入并 materialize 成 canonical truth
- supporting evidence
  - gained/lost matches
  - historical inventory context
  - run logs

### Data backbone / storage

- 主要 write path：`etl_*`, Bronze, Silver, `fact_machine_hour`
- route file：`modules/etl_module.py`

### Honest blocked states

- 文件缺失
- month/year conflicts
- Bronze rows 不足，导致 canonical materialization block

### If something looks abnormal

- 先不要跳去下游模块
- 回到 detection details 看哪份文件 month/year 冲突
- 如果 materialization warning 出现，先把它当 data-backbone issue，不要在下游页面硬解释

## 5.2 `📊 Canonical Operations Overview`

### Purpose

提供 selected month 的 canonical Gold 总览，让操作者先确认 backbone 再进入专题页面。

### Who it is for

- operator
- presenter
- reviewer

### Where it sits in the whole flow

它是 ETL 完成后的第一张“月度真相确认页”。

### First click / first choice

- 先选 month
- 先看六张 KPI card
- 再看 `Coverage & Confidence Audit`

### Key sections

- status chips
- `Canonical Gold Month View`
- `Coverage & Confidence Audit`
- `Machine State Summary`
- `Audit Sample Rows`
- export

### What each key output means

- `Total Energy`
  - 该月 canonical energy 总量
- `Total Good Qty`
  - 该月 canonical good quantity 总量
- `Weighted kWh / Good Unit`
  - 加权效率，不是 row mean
- `Canonical Machine-Hour Rows`
  - 当前月 page slice 的 Gold rows 数
- `Unknown / Unattributed`
  - 当前月里 state evidence 不足的 row 占比
- `Positive-Good Coverage`
  - 能支持效率 KPI 的 row 占比
- `Maintenance-Flag Coverage`
  - 有 maintenance signal 的 row 占比
- `Energy by State (kWh)`
  - 当前月 energy 在 canonical machine states 里的分布

### Main story vs supporting evidence

- main story
  - backbone 有没有足够完整地支持月度解释
- supporting evidence
  - row composition by state
  - audit sample rows

### Data source / backbone

- `fact_machine_hour` only
- reader：`core/canonical_gold_reader.py`

### Common issues / honest blocked states

- month 没有 `fact_machine_hour`
- `Unknown / Unattributed` 占比偏高
- selected month 没有 positive-good support

### What to do next if abnormal

- 如果 month 为空：回 ETL
- 如果 `Unknown / Unattributed` 高：说明这月 state attribution 需要更保守解读，不要硬讲 state-level business conclusion
- 如果 KPI 支撑不足：先讲 row coverage，再决定是否继续做 Energy / ML demo

## 5.3 `⚡ Energy Analysis`

### Purpose

把当前月 energy 解释成“哪里在耗能、多少可归因、哪些 machine 值得先看”。

### Who it is for

- operator
- presenter
- reviewer

### Where it sits in the whole flow

位于 backbone 已确认之后，作为主题化 energy lens。

### First click / first choice

- 先选 month
- 先看 KPI
- 再看 `Attribution Coverage & Residual Energy`
- 最后看 `Machines to Review First`

### Key sections

- KPI cards
- `Attribution Coverage & Residual Energy`
- `Energy Mix & Machine Attention`
- `Context & Diagnostics: Daily Energy Attribution Over Time`
- `Supporting Evidence: Maintenance Context`
- `Hourly Energy Pattern`

### What each key output means

- `Attributed energy`
  - 能放入具体 operating state 的 energy
- `Residual energy`
  - 仍然存在，但当前 state evidence 不足，故保留为 `Unallocated / Energy-Only`
- `state-attributed positive-energy rows`
  - 在 positive-energy rows 中，有多少 row 成功进入 state attribution
- `Energy Mix`
  - 例如 Production / Setup / Planned Stop / Unplanned Stop / Idle / Maintenance / Unallocated
- `Machines to Review First`
  - 这是 attention lens，不是 solver recommendation

### Main story vs supporting evidence

- main story
  - 这个月 energy 主要去了哪里
  - 当前 attribution 的覆盖与残留程度如何
  - 哪些 machine 值得进一步 review
- supporting evidence
  - daily stacked series
  - maintenance-age curve
  - average-per-row hourly chart

### Data source / backbone

- `fact_machine_hour` only
- reader：`core/canonical_energy_reader.py`

### A practical operator example

如果你在 `June 2025` 演示：

1. 先用 main pie chart 说明 Production / Setup / Planned Stop 的 energy mix
2. 再指出 residual energy 仍被诚实保留，而不是被硬塞进某个 state
3. 然后看 `Machines to Review First`
4. 如果你想把故事转进 optimization，可说：
   - “接下来我会去 `🎯 Operational Decision Support`，用同一个 canonical backbone 看 machine-level priority”

### Common issues / honest blocked states

- 没有可用 month
- machine attention list 为空
- maintenance curve rows 不够

### What to do next if abnormal

- machine attention list 为空：说明当前 support rule 太严格或当月 positive-good rows 不足，不要硬讲 ranking
- residual energy 偏高：先强调 attribution honesty，而不是把它说成系统失败
- maintenance curve 为空：直接跳过 supporting evidence，不影响主故事

## 5.4 `🤖 Efficiency Prediction & Governance`

### Purpose

用 active saved model 对当前月份做 machine-level review，而不是做执行排程。

### Who it is for

- reviewer
- presenter
- 需要理解 model coverage 的 operator

### Where it sits in the whole flow

在 backbone 与 energy story 之后，用来回答：

- 当前月份有多少 row 真正 inferable
- 哪些 machine 值得 model review
- active artifact 的 provenance 是什么

### First click / first choice

- 先看 `Active Model Summary`
- 再看 `Selected-Month Inference Readiness`
- 再看 `Model Review Queue`
- 最后才打开 `Scenario Lab`

### Key sections

- `Active Model Summary`
- `Selected-Month Inference Readiness`
- `Model Review Queue`
- `Scenario Lab`
- `Model Governance`
- `Reference & Audit`

### What each key output means

- `Active Model Summary`
  - 当前 active artifact 的 version、trained time、holdout metrics
- `Selected-Month Inference Readiness`
  - 当前选中月份，有多少 canonical rows 现在能被 active model safely score
- `Direct canonical / Adapted / Defaulted / Blocked`
  - support path coverage，不是 improvement trend
- `Model Review Queue`
  - 一个 deterministic review ranking，不是执行队列
- `Comparable Baseline`
  - peer median baseline，不是理论最优值
- `Scenario Lab`
  - 单个 review candidate 的 model-backed scenario evidence

### Main story vs supporting evidence

- main story
  - active artifacts 是否可用
  - 当前月份 inference coverage 如何
  - 哪些 machine 值得先 review
- supporting evidence
  - blocked reason detail
  - full prediction evidence table
  - deep governance metadata

### Data source / backbone

- canonical input source：`fact_machine_hour`
- reader：`core/canonical_ml_reader.py`
- ranking helper：`core/ml_review_queue.py`
- predictor：`core/ml_predictor.py`
- active artifacts：
  - `models/production_efficiency_model.pkl`
  - `models/production_preprocessor.pkl`

### A practical operator example

标准演示不要一上来就讲 retraining。更好的顺序是：

1. 在 `June 2025` 先说明 active model 仍是 `Task 4L` bundle
2. 再说明当前 selected month 的 inference readiness
3. 打开 `Model Review Queue`
4. 选一个上方 candidate 去看 `Scenario Lab`

如果你已经打算在后面切到 `🎯 Operational Decision Support`，这里就把 `Scenario Lab` 讲成“model evidence”，不要讲成“执行建议”。

### Common issues / honest blocked states

- blocked rows 多
- selected month inferable rows 少
- `Scenario Lab` 没有 supported template

### What to do next if abnormal

- blocked rows 多：优先讲 blocked reason，而不是硬讲 model 不准
- inferable rows 少：说明 selected month readiness 不足，不要把这页讲成全面 coverage
- `Scenario Lab` 无支持模板：转去 `Reference & Audit` 或换 machine，不要 fabricate scenario

## 5.5 `🎯 Operational Decision Support`

### Purpose

基于 canonical Gold 做 deterministic machine prioritization，并提供 selected-machine review。

### Who it is for

- operator
- presenter
- reviewer

### Where it sits in the whole flow

它承接 Energy / ML 之后的“那我下一步先看哪台 machine”问题。

### First click / first choice

- 先选 month
- 看 `Opportunity Worklist`
- 再用 `Support Toolbar`
- 最后选 `Inspect machine`

### Key sections

- month KPI strip
- `Opportunity Worklist`
- `Support Toolbar`
- `Selected Machine Review`
- `Model-Backed Intervention Preview`
- `Score Decomposition`
- `Supportive Context`
- `Historical Hour Signals`
- `Team Signals`

### What each key output means

- `Opportunity Score`
  - 当前公式是：
    `40% energy intensity + 30% non-productive share + 15% maintenance recency + 15% scrap rate`
- `Priority`
  - `High` / `Medium` / `Low`
- `Top Driver`
  - 当前 machine 在 worklist 上最主要的解释因子
- `Recommended Action`
  - 给 operator 的下一步 review 方向
- `Eligible Rows`
  - 该 machine 有多少 row 支撑当前 energy-intensity summary
- `Weighted kWh / Good Unit`
  - machine-level weighted ratio

### Main story vs supporting evidence

- main story
  - 哪些 machine 值得先 review
  - 为什么
  - 如果 seed row 可用，preview 会给出可讲解的 scenario evidence
- supporting evidence
  - score decomposition
  - historical hour signals
  - team signals
  - full scored table

### Data source / backbone

- summary source：`fact_machine_hour`
- reader：`core/canonical_optimization_reader.py`
- preview source：shared intervention-preview layer + active `MLPredictor`
- maintenance context：`core/maintenance_evidence.py`

### A practical operator example

如果你要用 family `024` 做标准演示：

1. 进 `June 2025`
2. 在 `Machine family` 选 `024`
3. 先给观众看 `Opportunity Worklist`
4. 再选 `Inspect machine = 024-081`
5. 说明它为什么排前面
6. 然后读 `Model-Backed Intervention Preview`

当前 evidence-based 例子里：

- `024-081` 是一个适合演示 supported preview 的 machine
- `024-105` 是一个适合演示 honest blocked path 的 machine

所以你可以这样讲：

> 先用 `024-081` 展示“系统能给什么 evidence”，再用 `024-105` 展示“系统不能支持时会如何诚实 block”。

### Common issues / honest blocked states

- support filters 太严，worklist 为空
- selected machine 没有 preview
- preview 有结果但 improvement 很小

### What to do next if abnormal

- worklist 为空：放宽 `Minimum eligible rows` 或 `Minimum total good qty`
- selected machine 无 preview：可以换 machine；也可以保留这个 blocked case 作为 honesty example
- delta 很小：直接说 limited incremental benefit is still a valid model outcome

## 5.6 `🔧 Maintenance`

### Purpose

提供 maintenance evidence [已有维修记录的覆盖与机台历史证据]，而不是做 predictive-maintenance forecasting。

### Who it is for

- operator
- presenter
- reviewer

### Where it sits in the whole flow

它更适合放在整体 demo 后段，作为 evidence closure，而不是开场主舞台。

### First click / first choice

- 先看 top status banner
- 再看 `Maintenance Coverage Snapshot`
- 最后用 `Machine Evidence Lookup`

### Key sections

- status banner
- `Maintenance Coverage Snapshot`
- `Machine Evidence Lookup`
- `Supporting Visuals`
- `Observed Energy Intensity vs Maintenance Age`
- `Legacy/Admin Maintenance Risk View`
- `Admin / Details`

### What each key output means

- `Stored Records`
  - 当前 maintenance tables 里存了多少条记录
- `Matched Records`
  - 其中多少能连到 canonical machine
- `Integrated Machines`
  - 有 linked maintenance history 的 canonical machines 数
- `Canonical Coverage`
  - linked maintenance history 对 canonical machine 集合的覆盖
- `Total Events (All Time)`
  - 全部已匹配 maintenance events
- `Recent Events Shown`
  - 为了可读性展示的 recent window，不等于 all-time event 总数
- `PM Ratio (All Time)` / `PM Ratio (Recent Window)`
  - 维修类型构成，只是描述性 evidence

### Main story vs supporting evidence

- main story
  - 当前 maintenance evidence 的覆盖有多大
  - 某台 machine 的 history 有多完整
- supporting evidence
  - month-level record counts
  - work-order type mix
  - maintenance-age energy curve
  - legacy/admin risk table

### Data source / backbone

- primary source：`maintenance_records`
- helper：`core/maintenance_evidence.py`
- supporting energy curve：`fact_machine_hour` via `core/canonical_energy_reader.py`

### A practical operator example

如果你要演示“有 history 的 machine 长什么样”：

1. 打开 `🔧 Maintenance`
2. 在 machine dropdown 选 `166-002`
3. 先讲 `Total Events (All Time)` vs `Recent Events Shown`
4. 再讲 `Latest Work Order Type`
5. 最后再决定要不要展开 supporting visuals

当前 live evidence 里，`166-002` 很适合做这个示例，因为它：

- all-time events `165`
- recent events shown `50`
- latest work-order type `AM`

### Common issues / honest blocked states

- 没有 maintenance records
- records 有，但 machine-linked evidence 不足
- 某 machine 没有 matched history

### What to do next if abnormal

- 没有 records：去 `Admin / Details` 上传
- machine 没有 history：直接说“目前没有 matched maintenance evidence”，不要补脑
- maintenance-age curve 为空：只讲 coverage snapshot，不影响主故事

## 6. How to read `Model-Backed Intervention Preview`

### 6.1 先讲结论：这是什么，不是什么

`Model-Backed Intervention Preview` 是一个 preview [模型情境预览，不等于实际执行或已实现节省]。

它是：

- active saved model 的输出
- 建立在 one real comparable machine-hour seed row 上
- 用非常窄的 scenario templates 去比较 baseline 与 scenario

它不是：

- realized saving
- executed optimization plan
- whole-month savings calculator
- scheduling solver

### 6.2 Screenshot reference 怎么用

本次 Task 7 另外读了一个 screenshot reference：

- 来源：`1st Manual Operating on 'Optimization' Module.rtfd/螢幕截圖 2026-04-05 下午8.13.50.png`
- 日期要讲清楚：这是 `2026-04-05` manual-review packet 的 screenshot，不是今天 live page 的固定 benchmark

在那张 screenshot 里，主卡片显示：

- `Baseline kWh / Unit = 0.8935`
- `Baseline confidence = 0.80`
- `Best supported scenario = Combined Support`
- `Best delta @ seed volume = -0.0115 kWh`

这张图最适合拿来教“怎么读字段”，不适合拿来声称“live system 永远是这个数”。

### 6.3 Field-by-field reading guide

#### `Baseline kWh / Unit`

意思：

- baseline [基线] 是 active saved model 对当前 seed row 的 predicted efficiency
- 单位是 `kWh / unit`
- 它是“这个 comparable row 在不改 template 前”的模型预测值

演示说法：

> 这是 active saved model 对当前 comparable machine-hour row 的 baseline prediction。

不要说：

> 这是机器现在真实会消耗的固定值。

#### `Baseline confidence`

意思：

- 这是模型对 baseline prediction 的 confidence
- 它帮助你判断“这条 preview 能讲多重”
- confidence 高，不等于现实一定会发生；它只代表当前模型输出的确定度更高

演示说法：

> confidence 帮我们决定这条 preview 适合当 strong evidence 还是 light evidence。

#### `Best supported scenario`

意思：

- 在当前支持的 scenario templates 里，哪个 supported scenario 的 predicted result 最好
- 当前 template scope 很窄，只包括：
  - `Maintenance Refresh`
  - `Crew Support +1`
  - `Combined Support`

注意：

- “best” 只是在当前 template set 内比较
- 不代表 global optimum

#### `Best delta @ seed volume`

意思：

- 这不是整个机器整月的 saving
- 它是：
  - `delta_vs_baseline * seed_production_qty`
- 所以它只是在当前 comparable seed row volume 下的 estimated kWh change

演示说法：

> 这里的 delta 是按当前 seed row 的 comparable production volume 算出来的，不是月度总节省。

#### comparable seed-row context line

典型格式：

`Comparable seed row: {timestamp} | support path: {Direct/Adapted/Defaulted} | current comparable production volume: {x}`

它告诉你三件事：

- 这条 preview 用的是哪一个 timestamp 的 real row
- 这条 row 的 support path 是什么
- 当前比较是按多少 production volume 做的

如果 support path 不是 `Direct canonical row`，你在演示里要更保守。

#### comparison table row by row

在 `Optimization` route 里，主 preview 下方会先出现一个简化 comparison table。

读法：

- `Baseline`
  - 当前 real seed row 的 baseline model prediction
- `Best scenario row`
  - 当前最优 supported scenario 的对比
- `Meaning`
  - 帮你把数字翻成一句人话，例如：
    - limited incremental benefit
    - lowers predicted energy intensity
    - raises predicted energy intensity

如果 `Meaning` 告诉你 benefit 很有限，这不是失败，而是 honest result。

#### the blue explanatory note

蓝色说明条的核心信息是：

> Estimated kWh change is calculated at the seed row's current comparable machine-hour volume.

它存在的目的就是防止误讲成：

- realized saving
- full-month impact
- executed plan

演示时最好直接顺手读出来。

#### supporting-evidence disclosure below

在 `🎯 Operational Decision Support` 的 preview 下方，完整 template table 会放在 `Supporting Evidence: All template outcomes` disclosure 里。

它的作用是：

- 把所有 supported / unsupported template 都保留
- 让观众知道系统没有偷偷把 unsupported path 隐藏掉

如果你在 `🤖 Efficiency Prediction & Governance` 的 `Scenario Lab` 里看同一类 preview，完整 scenario table 会更直接地显示在主内容里；两页的 underlying logic 相同，但页面层级不同。

### 6.4 这些字段之间是什么关系

按理解顺序读最清楚：

1. `Comparable seed row`  
   先确认比较对象是谁。
2. `Baseline kWh / Unit` + `Baseline confidence`  
   先知道当前 seed row 的模型基线。
3. `Best supported scenario`  
   看当前 template set 内，哪个 supported path 最好。
4. `Best delta @ seed volume`  
   把“每单位变化”翻成“当前 seed row volume 下大概差多少 kWh”。
5. `comparison table`  
   让你把 baseline 与 scenario 放在一起读。
6. blue note + supporting evidence  
   帮你控制 claim boundary。

### 6.5 一个标准 demo 例子

推荐用两个 machine 配对演示：

- supported case：`024-081`
- blocked case：`024-105`

你可以这样做：

1. 在 `🎯 Operational Decision Support` 选 `June 2025`
2. `Machine family` 选 `024`
3. 先 inspect `024-081`
4. 解释：
   - worklist 为什么把它排在前面
   - preview 为何可用
   - best scenario 只是当前 supported templates 里的最好结果
5. 再切到 `024-105`
6. 解释：
   - 这个 machine 可能会被 honest block，因为当前月没有 eligible canonical saved-model seed row

这样观众会同时看到：

- 系统能给 evidence 的情况
- 系统不能支持时也会诚实停止的情况

### 6.6 在 presentation 里该怎么说

推荐说法：

- “这是 active saved model 在 one comparable machine-hour row 上做的 scenario preview。”
- “这里的 delta 是按 seed row current comparable volume 算的，不是月度总 saving。”
- “如果 best scenario improvement 很有限，这也是 valid outcome。”

### 6.7 什么绝对不要说

- “系统已经帮我们找到最佳排程。”
- “这个数就是本月一定能省下来的电。”
- “这个 preview 等于已经执行过的优化计划。”
- “只要做 maintenance refresh 就一定会下降到这个值。”
- “没显示结果只是 UI 问题。”

## 7. Presentation interpretation notes by module

| Module | presenter should emphasize | first-pass 可以跳过什么 | supporting evidence only | honest claim boundary |
|---|---|---|---|---|
| `🔄 ETL Pipeline` | month truth、filename-first detection、rerun replaces active month snapshot | partial/single-system tables | historical inventory context | 不是 version control / rollback tool |
| `📊 Canonical Operations Overview` | `fact_machine_hour` backbone、weighted KPI、energy-by-state | audit sample rows | row composition by state | 不是 raw-source explorer |
| `⚡ Energy Analysis` | attribution coverage、residual honesty、energy mix、machine attention | daily anomaly detail、average-per-row hourly chart | maintenance-age curve | 不是 causal engine，也不是 solver |
| `🤖 Efficiency Prediction & Governance` | active model summary、selected-month readiness、review queue | full blocked row table、deep governance provenance | raw prediction evidence | 不是 execution page，也不是 auto-improvement proof |
| `🎯 Operational Decision Support` | opportunity worklist、top driver、recommended action、preview honesty | full scored table、team signals | historical hour signals、all template outcomes disclosure | 不是 scheduling solver |
| `🔧 Maintenance` | evidence coverage、machine history contract、all-time vs recent window | legacy/admin risk view | maintenance-age energy curve | 不是 predictive-maintenance model |

## 8. Recommended 18-20 minute live-demo route

### 8.1 Primary route

| Time | Module / action | 要展示什么 | 建议说法 | 默认收起/跳过 |
|---|---|---|---|---|
| 1.0 min | Platform framing | 首页标题 + 六模块 | “整个系统围绕一个 canonical machine-hour backbone 展开。” | none |
| 2.5 min | `🔄 ETL Pipeline` -> `Latest Run Snapshot` | latest month、previous month delta、next steps | “先确认 live data backbone 已经落地，再进入分析页面。” | 不现场重新上传文件，除非你要演 ETL |
| 2.5 min | `📊 Canonical Operations Overview` | KPI + `Coverage & Confidence Audit` + `Energy by State (kWh)` | “这一页先告诉我们这个月的 canonical truth 是否足够稳定。” | `Audit Sample Rows` |
| 3.0 min | `⚡ Energy Analysis` | attribution coverage、energy mix、machine attention | “Energy 页面回答的是哪里耗能、多少可归因、哪些 machine 值得先看。” | daily / hourly reference expanders |
| 3.5 min | `🎯 Operational Decision Support` | worklist + family `024` filter + inspect `024-081` | “这里不是 solver，而是 deterministic prioritization support。” | `Historical Hour Signals`、`Team Signals` |
| 3.0 min | same page -> preview | `Model-Backed Intervention Preview` | “这是 one comparable row 的 model-backed preview，不是 realized saving。” | `Supporting Evidence: All template outcomes` 先不展开 |
| 2.5 min | `🤖 Efficiency Prediction & Governance` | active model summary + readiness + review queue | “Optimization 讲执行优先级，ML 这页讲 inference coverage 和 review evidence。” | full blocked detail / governance appendix |
| 2.0 min | `🔧 Maintenance` | coverage snapshot + machine `166-002` history | “Maintenance 现在是 evidence page，不是 predictive-maintenance model。” | legacy risk view |
| 0.5-1.0 min | recap | claim boundaries + limitations | “我们展示的是可信 backbone、review support、evidence-based preview。” | none |

总时长约 `18.5-19.5` 分钟。

### 8.2 Transition wording you can reuse

- ETL -> Overview  
  “数据已经落地，接下来先确认 canonical month view。”
- Overview -> Energy  
  “确认 backbone 后，再看 energy 在 operating states 里的分布。”
- Energy -> Optimization  
  “知道 energy story 后，我们再看 machine-level prioritization。”
- Optimization -> ML  
  “Optimization 负责 operational priority；ML 负责 model evidence 和 governance。”
- ML -> Maintenance  
  “最后用 maintenance evidence 补上 machine history context。”

### 8.3 What to leave collapsed unless asked

- `Reference & Audit` 类 disclosure
- `Historical Hour Signals`
- `Team Signals`
- full blocked rows detail
- legacy/admin maintenance risk table
- average-per-row hourly energy chart

## 9. Fallback demo route if one page becomes awkward

如果 live demo 中某页状态不顺：

### Fallback Route A

`Latest Run Snapshot -> Canonical Operations Overview -> Energy Analysis -> ML page -> Maintenance`

适用情况：

- `Operational Decision Support` 的 selected machine 恰好 preview blocked
- 你不想在现场解释 filter 调整

### Fallback Route B

`Latest Run Snapshot -> Canonical Operations Overview -> Operational Decision Support -> Maintenance`

适用情况：

- 你时间不足
- 你想把“主故事”集中在 worklist + preview + maintenance evidence

### Practical fallback notes

- 如果 `024-081` 画面 awkward，就换 `166-002` 做 maintenance evidence，不必硬撑 Optimization preview
- 如果 `Scenario Lab` 或 preview blocked，就把 blocked 当成 honesty case，不要说“系统坏了”
- 如果 maintenance curve 不够干净，就只展示 coverage snapshot + machine evidence lookup

## 10. Troubleshooting / abnormal-state guidance

| Situation | 你看到什么 | 真实意思 | 你应该怎么做 | 现场该怎么说 |
|---|---|---|---|---|
| no month data available | month dropdown 有，但页面 warn no rows | 该月没有可用 `fact_machine_hour` slice | 回 ETL 确认 month materialization | “这个月尚未 materialize，所以页面选择诚实停止。” |
| blocked ML rows | readiness 有大量 blocked | 当前 selected month 缺少 `good_qty`、maintenance recency、或 task mapping 等支持字段 | 先解释 blocked reason summary，再决定是否继续 | “这表示当前月 coverage 有边界，不表示模型在乱猜。” |
| no supported scenario preview for a machine | preview info block | 该 machine 当前月没有 eligible seed row，或 active predictor 无法给 `source == model` 结果 | 换 machine 或保留为 blocked example | “系统在没有安全 seed row 时不会 fabricate preview。” |
| filtered Optimization worklist becomes empty | worklist 空白 warning | 你把 support filters 设得太严格 | 放宽 family / min rows / min good qty | “这不是没有机器，而是当前 support rule 把它们过滤掉了。” |
| maintenance evidence unavailable for a machine | machine context block / no history | `maintenance_records` 里没有 matched history | 换 machine，或回上传流程 | “这个 machine 当前没有 matched maintenance evidence。” |
| ETL upload conflicts / month mismatch | detection warning, processing blocked | 上传文件指向不同 month/year | 修正文件组合或启用 manual override | “系统宁可 block，也不把冲突文件写成错误月份。” |
| user expects delete = rollback | 删除 run record 后下游没回退 | delete 只是 provenance record 管理 | 不把它当 canonical rollback 用 | “删除这里的 run record 不等于回退 active month truth。” |

## 11. Honest claim boundaries to keep repeating

### Claims we can defend

- 平台现在由一个 canonical `fact_machine_hour` backbone 驱动主要 routed analytics
- ETL rerun 对同月采用 replace active snapshot 逻辑
- `Energy Analysis` 会明确保留 residual / unallocated energy
- `Efficiency Prediction & Governance` 使用 active saved artifacts 做 current-month review
- `Operational Decision Support` 是 deterministic rule-based prioritization
- `Maintenance` 是 evidence-and-coverage-first

### Claims we should avoid

- “系统已经会自动优化生产排程”
- “preview 等于真实节能结果”
- “maintenance page 已经能预测故障”
- “blocked case 只是小 bug”
- “同月 run 可以并行保留多个 active versions”

## 12. Quick operator checklist

### Before live demo

- 确认 app 正常启动
- 确认 `June 2025` 或你的目标 month 已 materialize
- 确认 `024-081` 这类示例 machine 仍适合演示
- 准备一个 supported case + 一个 blocked case
- 准备一个 maintenance-rich case，例如 `166-002`

### During live demo

- 先讲 backbone，再讲智能
- 先讲主卡，再展开 evidence
- blocked 就诚实说 blocked
- 小 benefit 也当作 valid result

### After live demo

- 如果观众问更深的细节，再开 `Reference & Audit`
- 如果观众问为什么没有 solver / predictive maintenance，直接回到 frozen decisions

## 13. Final takeaways

这个平台当前最适合被理解成：

- 一个稳定的 canonical analytics platform
- 一个以 `fact_machine_hour` 为 backbone 的 reviewer-friendly 系统
- 一个会诚实 block unsupported claims 的 demo-ready product

它最不适合被误讲成：

- 自动决策引擎
- 已落地优化系统
- predictive-maintenance solution

只要你按 `ETL -> backbone -> energy -> optimization -> ML -> maintenance evidence` 这个顺序讲，并持续守住 claim boundary，这个平台已经足够支撑一场稳定、诚实、完整的 end-to-end presentation。
