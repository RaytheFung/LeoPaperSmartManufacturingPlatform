# Detailed Module Walkthrough Report (ZH)

本文不是新的产品设计提案，而是对当前 live repo 里既有后端逻辑的中文拆解说明。

目标只有一个：

- 让 presenter / operator / reviewer 能用“流程 + 机制 + 边界”真正讲清楚四个模块：
  - `Predictive Maintenance Prototype`
  - `🎯 Operational Decision Support`
  - `Model Review Queue`
  - `Scenario Lab`

---

## 0. 先给总图：这四个模块在整个平台里分别做什么

你可以先把它们粗分成两类：

### A. current-state review / prioritization

- `🎯 Operational Decision Support`
  - 回答：当前月下，哪些 machine 值得先 review？
  - 核心是 deterministic machine prioritization。

- `Model Review Queue`
  - 回答：当前月下，哪些 machine 的预测结果最值得先做 model-side review？
  - 核心是 model-backed review ranking。

### B. experimental / scenario / future-intelligence

- `Predictive Maintenance Prototype`
  - 回答：在 anchor month 的 current-state 风险视角下，哪些机器现在更值得关注维护风险？
  - 核心是 weak-label maintenance risk prototype。

- `Scenario Lab`
  - 回答：如果对某个 real seed row 施加一个很窄的 template intervention，active saved model 会给出怎样的 baseline vs scenario 对比？
  - 核心是 one-row scenario evidence，不是执行计划。

---

## 1. `Predictive Maintenance Prototype`

## 1.1 它到底在回答什么问题

这个模块回答的是：

- 在你当前选的 month 下
- 用这个月作为 current-state anchor
- 现在哪些机器看起来更值得优先关注
- 这个结论是来自：
  - 真正可以训练的 weak-label model
  - 还是因为标签条件不够，退回到 fallback evidence score

它**不是**在回答：

- 机器哪一天一定会坏
- 应该马上派哪张维修工单
- 这是已经上线的 predictive maintenance engine

一句话：

> 它是 current-state risk ranking prototype，不是故障时间预测器。

---

## 1.2 它的真实后端输入是什么

核心入口在：

- `core/experimental_maintenance_prototype.py`
  - `build_predictive_maintenance_prototype()`

它真正读的东西有两类：

### 1. fact backbone

来自 `fact_machine_hour`：

- `canonical_machine_id`
- `hour_ts`
- `good_qty`
- `energy_total_kwh`
- `idle_minutes`
- `setup_minutes`
- `planned_stop_minutes`
- `unplanned_stop_minutes`
- `production_minutes`
- `hours_since_last_maintenance`
- `days_since_last_maintenance`

### 2. maintenance history

来自 `maintenance_records`：

- `machine_id` / `canonical_machine_id`
- `transaction_date`
- `work_order_type`

所以这模块不是空想，它背后是：

- 真实 machine-day operational evidence
- 真实 maintenance event history

---

## 1.3 它的完整 workflow 是什么

你可以按下面这条箭头图来理解：

`selected month`
→ `build machine-day snapshots through anchor month`
→ `attach trailing 30-day operating features`
→ `read real maintenance events`
→ `attach past-event features + future-window weak labels`
→ `check whether weak-label model is usable`
→ `if usable: use weak-label model`
→ `else: use fallback evidence score`
→ `score latest monthly snapshot per machine`
→ `build current at-risk table`

下面逐步拆。

---

## 1.4 第一步：build machine-day snapshots

函数：

- `build_predictive_maintenance_prototype()`
- `_build_machine_day_snapshots()`

这里做的不是直接对 machine-hour 评分，而是先把 hour-level row 聚成 machine-day snapshot。

为什么？

- 因为 maintenance 风险更适合在“天”这个粒度看
- 这样才能把“近期维护频率”“近期能耗强度”“近期非生产占比”这些 trailing features 做得更稳定

注意：

- `selected month` 只是 anchor current-state view
- 不是只用这个月做训练

后端会把 snapshot 保留到：

- `snapshot_date <= anchor month end`

也就是说：

- 你选 `June 2025`
- 它看的是“到 2025-06-30 为止的 machine-day 历史”
- 然后在这个范围里抽出当前月的 latest snapshot 做风险表

---

## 1.5 第二步：加 trailing 30-day features

函数：

- `_add_trailing_operational_features()`

它按 machine 分组，然后滚动算近 30 天特征，包括：

- `total_good_qty_30d`
- `total_energy_kwh_30d`
- `nonproductive_minutes_30d`
- `tracked_minutes_30d`
- `weighted_kwh_per_good_unit_30d`
- `nonproductive_share_30d`

这些特征的意义很直白：

- 近 30 天产量多少
- 近 30 天耗电多少
- 近 30 天非生产分钟占比多高
- 单位产量能耗是不是偏高

这一步非常关键，因为后面无论是 weak-label model 还是 fallback evidence score，都要靠这些近期特征。

---

## 1.6 第三步：构造 maintenance-side features 与 weak labels

函数：

- `_read_maintenance_events()`
- `_attach_maintenance_features_and_labels()`

这是整个模块最容易被误解的地方。

### 它先做 past-side 特征

对于每个 machine-day snapshot，它往回看：

- 到 snapshot_date 为止，历史上一共有多少 maintenance events
- 最近 30 天里有多少 maintenance events
- PM ratio 是多少

得到的典型字段有：

- `cumulative_maintenance_count`
- `recent_events_count_30d`
- `maintenance_intensity_30d`
- `pm_ratio_all_time`
- `pm_ratio_recent_30d`
- `days_since_last_maintenance`

### 然后才做 future-side weak label

对每个 snapshot，它再往未来看：

- `snapshot_date < event_date <= snapshot_date + horizon_days`

如果这个未来窗口内有真实 maintenance event：

- `label = 1`

如果没有：

- `label = 0`

但有一个前提：

- 这个未来窗口必须真的“看得到”

也就是代码里的：

- `snapshot_date + horizon_days <= max_event_date`

如果未来窗口根本没有被历史数据完整覆盖，那就：

- `label_available = 0`
- 不允许把它当监督样本

这点非常重要。

所以你可以这样讲：

> 这个模块不是随便贴标签。它只在真实 future maintenance window 可观察时，才给 snapshot 附 weak label。

---

## 1.7 第四步：决定 weak-label model 能不能用

函数：

- `_fit_weak_label_model()`

系统不是只要有 label 就硬上模型，它有一套 usability gate。

### gate 条件

如果以下任一条件不满足，就不用模型：

- labeled snapshots 少于 `200`
- positive labels 少于 `25`
- negative labels 少于 `25`
- unique snapshot dates 少于 `20`
- time-aware split 之后 train 或 eval 为空
- time-aware split 后 train 或 eval 变成单类

为什么这么做？

- 因为这个原型的立场是“宁可诚实退回 evidence score，也不假装模型可用”

所以：

- `Weak-label model`
  - 代表标签条件够
- `Fallback evidence score`
  - 代表标签条件不够

不是系统坏了，而是系统在守边界。

---

## 1.8 如果模型可用，它怎么做

函数：

- `_fit_weak_label_model()`
- `_score_with_model()`

模型结构很轻量：

- numeric features
  - median impute
  - standardize
- categorical feature
  - `machine_family`
  - one-hot
- classifier
  - `LogisticRegression`
  - `class_weight="balanced"`

train/eval 不是 random split，而是：

- 按时间切
- 前 80% dates 做 train
- 后 20% dates 做 eval

所以它是一个 time-aware classifier，不是随机打乱的分类器。

最后对 current month latest snapshots 做：

- `predict_proba()`
- 产生 `risk_score`
- 再映射成 `risk_band`

风险带规则：

- `>= 0.70` -> `High`
- `>= 0.45` -> `Medium`
- else -> `Low`

---

## 1.9 如果模型不可用，它怎么 fallback

函数：

- `_score_with_fallback()`

fallback 不是一句“经验分数”，而是明确公式：

```text
risk_score =
    0.35 * normalized(days_since_last_maintenance)
  + 0.20 * normalized(recent_events_count_30d)
  + 0.15 * normalized(weighted_kwh_per_good_unit_30d)
  + 0.15 * normalized(nonproductive_share_30d)
  + 0.15 * (1 - normalized(pm_ratio_all_time))
```

最白话解释：

- 很久没维护 -> 风险升
- 最近 30 天维护事件很多 -> 风险升
- 最近单位产量能耗高 -> 风险升
- 最近非生产占比高 -> 风险升
- 全历史 PM ratio 低 -> 风险升

这是一张：

- transparent evidence score
- relative ranking score

不是：

- 正式故障概率
- 剩余寿命预测

---

## 1.10 最终输出为什么是一张 current-state risk table

函数：

- `_build_latest_month_slice()`
- `_build_risk_table()`

它不是拿所有历史 snapshot 都展示出来，而是：

- 先取 selected month 里的所有 snapshots
- 对每台 machine 只保留 latest one

所以你最后看到的是：

- 当前 anchor month 下
- 每台机器一张最新快照
- 再按 risk_score 排序

因此这张表的真正含义是：

> “如果今天站在这个月末的当前状态回看，哪些机器更值得先关注？”

不是：

> “历史上哪台机器最危险？”

也不是：

> “未来哪台机器一定最先故障？”

---

## 1.11 这个模块最容易讲错的 6 句话

不要说：

- `selected month 就是 training month`
- `risk score = 正式故障概率`
- `label = 系统自己编出来`
- `fallback evidence score = 假模型`
- `High risk = 马上会坏`
- `这是 production predictive maintenance engine`

应该说：

- `selected month 只锚定 current-state risk view`
- `weak labels 只在真实 future window 可观察时才附着`
- `模型可用时用 weak-label classifier，不可用时诚实退回 evidence score`
- `risk score 适合排序和相对比较，不是故障日期承诺`

---

## 1.12 30 秒 talk track

> 这个模块先把 canonical history 聚成 machine-day snapshots，再结合真实 maintenance events 构造 weak labels。只有当未来维护窗口真的可观察、样本量也够时，它才会训练一个轻量 time-aware classifier；如果条件不够，就退回到透明 evidence score。最后系统只取当前 anchor month 中每台机器最新的一张 snapshot，生成 current-state risk table。所以这页是在做风险排序，不是在承诺故障日期。

---

## 2. `🎯 Operational Decision Support`

## 2.1 它到底在回答什么问题

这个模块回答的是：

- 当前月下
- 哪些 machine 值得先 review
- 为什么先 review 它们
- 如果我要看某台 machine，系统能不能给我更细的 score decomposition、maintenance context 和 preview evidence

它不是在回答：

- 应该怎样排产
- 应该把哪张工单排到哪台机
- 这是一个自动 dispatch solver

一句话：

> 它是 deterministic machine prioritization，不是 scheduling engine。

---

## 2.2 它的后端 backbone 是什么

入口：

- `modules/optimization_module.py`
  - `render_optimization_module()`

核心 reader：

- `core/canonical_optimization_reader.py`

所有主 summary 的 backbone 都是：

- `fact_machine_hour`

没有：

- legacy fallback
- synthetic fallback
- scheduling solver

如果当前月没数据，就 honest block。

---

## 2.3 它的 workflow 总图

`select month`
→ `read selected-month fact_machine_hour`
→ `aggregate machine-level summary`
→ `compute opportunity score`
→ `build Opportunity Worklist`
→ `apply support toolbar filters`
→ `pick one machine for drilldown`
→ `show score decomposition + maintenance context`
→ `if preview available: show Model-Backed Intervention Preview`

---

## 2.4 第一步：machine-level monthly aggregation

函数：

- `build_machine_summary()`

对每台 machine 聚合 selected month 的 canonical rows，得到：

- `eligible_rows`
- `total_energy_kwh`
- `total_good_qty`
- `total_scrap_qty`
- `total_setup_minutes`
- `total_production_minutes`
- `total_planned_stop_minutes`
- `total_unplanned_stop_minutes`
- `total_idle_minutes`
- `avg_kwh_per_good_unit`
- `avg_hours_since_last_maintenance`
- `scrap_rate`
- `productive_hours`
- `nonproductive_hours`
- `utilization_proxy`

这里最重要的几个概念：

### `eligible_rows`

表示：

- 这台 machine 有多少 row 真的能支撑 energy-intensity summary

### `avg_kwh_per_good_unit`

表示：

- 在安全可用的 row 上
- `safe_energy_kwh / safe_good_qty`

### `utilization_proxy`

表示：

- `production_minutes / tracked_minutes`

### `nonproductive_hours`

表示：

- setup + planned stop + unplanned stop + idle

所以这模块不是在看单一 KPI，而是在把 machine 的月度运行状态聚成一套可解释 summary。

---

## 2.5 第二步：算 `Opportunity Score`

函数：

- `_apply_opportunity_scoring()`

公式是：

```text
opportunity_score =
    0.40 * energy_intensity_component
  + 0.30 * nonproductive_component
  + 0.15 * maintenance_recency_component
  + 0.15 * scrap_component
```

其中：

- `energy_intensity_component`
  - 是 `avg_kwh_per_good_unit` 的 normalized 值
  - 越高代表单位产量能耗越差

- `nonproductive_component`
  - 是 `nonproductive_share`
  - 越高代表 setup / stop / idle 占比越高

- `maintenance_recency_component`
  - 是 `avg_hours_since_last_maintenance` 的 normalized 值
  - 越高代表平均离上次维护越久

- `scrap_component`
  - 是 `scrap_rate`
  - 越高代表报废占比越高

然后给每台机：

- `High / Medium / Low`

阈值：

- `>= 0.55` -> `High`
- `>= 0.30` -> `Medium`
- else -> `Low`

同时还会抽一个最大 component 作为：

- `Top Driver`

也就是：

- `High kWh per good unit`
- `High non-productive share`
- `Long time since last maintenance`
- `Elevated scrap rate`

---

## 2.6 第三步：`Opportunity Worklist` 是怎么来的

函数：

- `_build_opportunity_worklist()`

它不是另一个复杂模型，只是把已经算好的 machine summary 按分数排序后，整理成一个 reviewer-friendly table。

表里重点字段：

- `Machine`
- `Family`
- `Priority`
- `Opportunity Score`
- `Top Driver`
- `Recommended Action`
- `Eligible Rows`
- `Total Good Qty`
- `Weighted kWh / Good Unit`

### `Recommended Action` 从哪来

函数：

- `_recommended_action()`

逻辑很简单：

- 如果 top driver 是 maintenance
  - 建议先查 maintenance recency
- 如果 top driver 是 non-productive
  - 建议看 setup/stop mix
- 如果 top driver 是 scrap
  - 建议先查 scrap-heavy runs
- 否则
  - 建议看 high energy intensity

所以：

> `Recommended Action` 不是 solver 输出，而是把 `Top Driver` 翻译成 operator next step。

---

## 2.7 第四步：`Support Toolbar` 做了什么

函数：

- `_render_opportunity_filters()`

这三个控件只影响当前 worklist / drill-down：

- `Machine family`
- `Minimum eligible rows`
- `Minimum total good qty`

它们不做：

- solver logic
- family normalization
- cross-family optimization

所以如果 worklist 空了，不是系统没机器，而通常是：

- 你把 support filter 设太严了

---

## 2.8 第五步：`Selected Machine Review`

函数：

- `_render_machine_drilldown()`

选中一台 machine 后，系统会显示：

- machine summary cards
- `Top Driver`
- `Recommended Action`
- `Maintenance Evidence Context`
- `Model-Backed Intervention Preview`
- `Score Decomposition`
- `Supportive Context`

这部分的角色不是“又算一遍分”，而是：

- 把该 machine 为什么排到前面，拆解给你看

### `Score Decomposition`

它直接把四个 component 拉出来看：

- Energy intensity
- Non-productive share
- Maintenance recency
- Scrap rate

所以这页的核心不是“神奇分数”，而是：

> 这个分数是由哪几种 machine-level 异常合成出来的。

---

## 2.9 `Model-Backed Intervention Preview` 跟这页是什么关系

它不是 Operational Decision Support 自己发明出来的 optimizer。

它只是：

- 复用 shared intervention-preview layer
- 给 selected machine 一个 model-backed scenario preview

也就是说：

- `Operational Decision Support` 负责回答：
  - 哪台先看
  - 为什么
- `Model-Backed Intervention Preview` 负责补一层：
  - 如果我在这台 machine 的 one comparable row 上施加安全模板，会发生什么 model-side comparison

所以 preview 是：

- evidence layer

不是：

- worklist score 的组成部分

---

## 2.10 这个模块最容易讲错的 6 句话

不要说：

- `这页在自动优化排程`
- `Opportunity Score 是 ML model 输出`
- `Recommended Action 是系统自动执行建议`
- `Support Toolbar 改变 backend logic`
- `Top machine = 一定最差的机器`
- `Preview = realized saving`

应该说：

- `这是 deterministic prioritization support`
- `Opportunity Score 是 rule-based explanatory score`
- `Recommended Action 是把 top driver 翻译成 operator next review step`
- `Preview 是额外 evidence，不是执行计划`

---

## 2.11 30 秒 talk track

> 这页先用 selected month 的 canonical machine-hour rows 聚成 machine-level summary，再把单位产量能耗、非生产占比、维护时距和 scrap rate 合成一个 deterministic opportunity score。工作清单告诉你哪台 machine 值得先 review，而 selected-machine drilldown 再解释为什么它排在前面。它是 phase-1 rule-based prioritization，不是 scheduling solver。

---

## 3. `Model Review Queue`

## 3.1 它到底在回答什么问题

这个模块回答的是：

- 当前 selected month 里
- active saved model 真正能评分的 machine 候选有哪些
- 哪些 machine 比“可比 peer baseline”更差
- 哪些 machine 最值得先做 model-side review

它不是在回答：

- 应该怎样调 machine
- 哪个 intervention 一定有效
- 模型已经能直接驱动执行

一句话：

> 它是 current-month inference coverage + review priority queue，不是 execution queue。

---

## 3.2 它的 workflow 总图

`select month`
→ `read selected-month fact_machine_hour`
→ `build canonical ML input rows`
→ `mark blocked vs eligible rows`
→ `keep latest eligible row per machine`
→ `run active saved predictor`
→ `block non-model outputs`
→ `build comparable baseline per machine`
→ `compute severity gap`
→ `compute review_priority_score`
→ `check whether Scenario Lab is available`
→ `build Model Review Queue`

---

## 3.3 第一步：build canonical ML input rows

函数：

- `build_month_input_dataframe()`
- `_build_input_row()`

每一条 machine-hour row 会被整理成 inference input。

核心字段包括：

- `machine_id`
- `datetime`
- `material_code`
- `team_leader`
- `task_name`
- `task_difficulty`
- `production_qty`
- `team_size`
- `hours_since_last_maintenance`
- `last_maintenance_type`
- `maintenance_intensity_30d`
- `cumulative_maintenance_count`
- `hour_of_day`
- `is_weekend`

### safe adapter rules

有些字段不是原样就齐，所以 reader 会做保守适配：

- `team_size`
  - 先用 canonical `team_size`
  - 没有就用 `manpower`
  - 再没有才用 preprocessor default

- `task_difficulty`
  - 从 `task_name` 推导
  - unmapped 就 block

- `last_maintenance_type`
  - 缺失就 `unknown`

### hard block rules

以下情况直接不能 inference：

- missing machine id
- missing timestamp
- `good_qty <= 0`
- missing `hours_since_last_maintenance`
- `task_name` 无法映射成 supported task family

这些 row 不会被偷偷补假值继续预测。

---

## 3.4 第二步：build prediction candidates

函数：

- `build_prediction_candidates()`

逻辑很窄：

- 只保留 `eligible_for_inference == 1`
- 对每台 machine 只取最新的一条 eligible row

所以：

- `Model Review Queue` 不是用所有 row 排名
- 而是每台机器一个 current-month representative row

这点非常重要。

它的本质是：

> one current candidate row per machine

不是：

> whole-month average prediction per machine

---

## 3.5 第三步：run active saved predictor

函数：

- `build_prediction_dataframe()`

这里会调用 active `MLPredictor.predict_efficiency()`。

安全规则非常严格：

- 只有 `prediction["source"] == "model"` 才算可用
- 如果返回 `fallback` 或非 model source，就 block

也就是说：

- 这页不允许 simulated prediction 混进主结果

所以它的核心边界是：

> 宁可 blocked，也不展示 fallback simulation 当正式 inference。

---

## 3.6 第四步：构造 comparable baseline

函数：

- `build_model_review_queue()`
- `_resolve_comparable_baseline()`

这是理解 review queue 的关键。

它不是拿 predicted_efficiency 单独排序，而是先给每台 machine 找一个可比 baseline。

baseline 选择顺序：

1. `Family + task-difficulty peer median`
2. `Task-difficulty peer median`
3. `Selected-month median fallback`

也就是说：

- 优先找同 family + 同难度的 peer
- 不够时退到同难度 peer
- 还不够时退到当前月全体中位数

它不是：

- 理论最优基线
- 历史最佳值
- aggressive savings target

它是：

- conservative comparable baseline

---

## 3.7 第五步：算 `review_priority_score`

核心逻辑：

### 1. severity gap

```text
severity_gap = max(predicted_efficiency - comparable_baseline, 0)
```

意思：

- 只有当 machine 比 baseline 更差时，gap 才大于 0
- 如果 machine 没比 baseline 差，就不会被推高 priority

### 2. estimated excess kWh

```text
estimated_excess_kwh = severity_gap * production_qty
```

意思：

- 不是只看单位差距
- 还看当前 comparable row 的 volume

### 3. support path weight

路径权重：

- `Direct canonical row` = `1.0`
- `Adapted row` = `0.85`
- `Defaulted row` = `0.65`

意思：

- 证据越直，权重越高
- 适配越多，priority 会被适当打折

### 4. final review priority

```text
review_priority_score = estimated_excess_kwh * confidence * support_weight
```

所以它真正衡量的是：

- 比 peer baseline 差多少
- 在当前 row volume 下差了多少 kWh
- 模型 confidence 高不高
- support path 强不强

这比只按 predicted_efficiency 排序严谨得多。

---

## 3.8 第六步：为什么 queue 里还会出现 Scenario Lab 信息

函数：

- `_build_preview_summary()`
- `_recommended_review_note()`

queue 在构建时，会顺手看：

- 这条 row 能不能生成 Scenario Lab
- 如果能，best supported scenario 是什么

所以 queue 里会附带：

- `preview_available`
- `best_supported_scenario`
- `recommended_review_note`

但注意：

- preview 不是 queue 排名主公式的一部分
- 它只是补充这个 candidate 有没有后续 scenario evidence

---

## 3.9 `recommended_review_note` 是怎么来的

它会综合：

- `top_driver`
- `support_path`
- `severity_gap`
- `preview_available`

例如：

- 如果 severity gap <= 0
  - 会说 monitor only

- 如果 support_path 不是 direct
  - 会提醒先确认 adapted/defaulted inputs

- 如果 Scenario Lab 可用
  - 会把 best supported scenario 加进说明

所以这条 note 的作用是：

> 帮 presenter / reviewer 把 queue item 直接翻译成下一步 review conversation。

---

## 3.10 这个模块最容易讲错的 6 句话

不要说：

- `review queue 就是高风险机器清单`
- `priority score 只看 predicted_efficiency`
- `baseline 是理论最优值`
- `support path 不影响 ranking`
- `blocked rows 说明模型坏了`
- `preview available 就等于 intervention 一定有效`

应该说：

- `review queue 是 model-backed review ranking`
- `priority 是 gap × volume × confidence × support weight`
- `baseline 是 conservative peer median contract`
- `preview availability 只是附加 evidence`

---

## 3.11 30 秒 talk track

> 这页先把 selected month 的 canonical rows 转成模型输入，再为每台机器保留一条最新可推理 row。只有 active saved model 真正返回 model-source prediction 的 row 才会进入主队列。然后系统给每台机找一个 comparable peer baseline，算出它比 baseline 差多少，再把这个 gap 乘上当前 row volume、confidence 和 support path weight，形成 review priority score。所以这页是在回答“哪台机器最值得先做 model-side review”，不是在给执行建议。

---

## 4. `Scenario Lab`

## 4.1 它到底在回答什么问题

它回答的是：

- 对某一条 real comparable seed row
- 如果套用一个非常窄的 intervention template
- active saved model 会给出怎样的 baseline vs scenario comparison

它不是：

- whole-month simulator
- realized-saving calculator
- auto optimizer
- scheduling engine

一句话：

> 它是 one comparable row 的 scenario evidence，不是执行方案。

---

## 4.2 它的 workflow 总图

`select one machine / candidate`
→ `find latest eligible canonical seed row`
→ `build baseline prediction`
→ `build narrow scenario templates`
→ `run active saved model on each supported template`
→ `compare delta vs baseline`
→ `pick best supported scenario`
→ `display full supported + unsupported table`

---

## 4.3 第一步：选 seed row

函数：

- `build_machine_intervention_preview()`

它先在当前 candidate set 里找：

- 当前 machine 有没有 eligible seed row

如果没有：

- honest block

如果有：

- 取该 machine 最新的一条 eligible canonical row

这条 row 就是：

- `seed_row`

所以 Scenario Lab 永远是 anchored on：

- one real canonical machine-hour row

---

## 4.4 第二步：先做 baseline

函数：

- `_resolve_baseline()`

baseline 有两种来源：

### A. 如果外面已经给了 baseline_row

直接复用：

- `predicted_efficiency`
- `confidence`
- `top_driver`

### B. 如果没有

就对 seed_row 本身跑一次：

- `run_intervention_prediction(seed_row, {}, predictor)`

但仍有硬规则：

- 如果 predictor 不是 `source == model`
  - baseline 直接 block

所以 baseline 不是手工编的，也不是平均值，而是：

- active saved model 对 real seed row 的 baseline prediction

---

## 4.5 第三步：构造 scenario templates

当前 template 只有 3 个：

1. `Maintenance Refresh`
2. `Crew Support +1`
3. `Combined Support`

### `Maintenance Refresh`

函数：

- `_build_maintenance_refresh_spec()`

逻辑：

- 看 seed row 的 `hours_since_last_maintenance`
- 试着把它往下调
  - reduction = `max(12, 25% of current value)`
- 得到一个更“新维护”的 scenario

如果 seed row 连 maintenance-recency 都没有：

- 这个 template 就 unsupported

### `Crew Support +1`

函数：

- `_build_crew_support_spec()`

逻辑：

- 看 `team_size`
- 如果有正数，就做 `team_size + 1`

如果 team size 没有正值：

- unsupported

### `Combined Support`

函数：

- `_build_combined_support_spec()`

逻辑：

- 同时合并 maintenance refresh + crew support

如果前两个任一个 blocked：

- combined 也 blocked

所以 Scenario Lab 不是自由拖 slider，而是固定模板。

---

## 4.6 第四步：run scenario prediction

函数：

- `run_intervention_prediction()`

每个 scenario 都会：

- 拿 seed row 复制一份
- 用 overrides 覆盖几个字段
- 再喂给 active `MLPredictor.predict_efficiency()`

但有两个硬门槛：

### 门槛 1：seed row 必须有完整 required fields

缺任何一个支持字段都 block，例如：

- `machine_id`
- `team_leader`
- `material_code`
- `hours_since_last_maintenance`
- `task_difficulty`
- `production_qty`
- `team_size`
- `hour_of_day`
- `month`
- `last_maintenance_type`

### 门槛 2：predictor 必须返回 `source == model`

否则 scenario block

所以 Scenario Lab 不是想跑就能跑，它是 guarded preview。

---

## 4.7 第五步：怎么算 delta 和 best supported scenario

### delta vs baseline

公式：

```text
delta_vs_baseline = scenario_predicted_efficiency - baseline_efficiency
```

解释：

- 负数
  - scenario 比 baseline 更省
- 正数
  - scenario 比 baseline 更差

### estimated_kwh_change

公式：

```text
estimated_kwh_change = delta_vs_baseline * seed_production_qty
```

解释：

- 这是按当前 seed row comparable volume 算的 kWh change
- 不是月度总 savings

### best supported scenario

函数：

- `_best_supported_scenario()`

逻辑：

- 只在 `supported` scenarios 里选
- 以最小 `delta_vs_baseline` 为优先
- 再用 `predicted_efficiency` 做 tie-break

所以 best scenario 的意思是：

- 在当前很窄 template set 里
- 哪个 scenario 的预测结果最优

不是：

- global optimum

---

## 4.8 为什么 unsupported rows 也要显示出来

函数：

- `build_intervention_preview_table()`

设计上它不会把 unsupported template 静默隐藏，而是显式保留：

- `Status`
- `Blocked Reason`

这样做的意义是：

- 证明系统没 fabricate scenario
- 也证明 template scope 真的是窄且受约束

所以 blocked case 不是 embarrassment，而是 honesty proof。

---

## 4.9 Scenario Lab 和 Optimization preview 是什么关系

underlying logic 相同：

- 都复用 `core/intervention_preview.py`

但页面层级不同：

### 在 `🎯 Operational Decision Support`

- preview 是 selected-machine drilldown 里的一块 evidence layer
- 重点仍是 worklist 和 machine review

### 在 `🤖 Efficiency Prediction & Governance`

- `Scenario Lab` 直接把 preview 当主内容之一
- 更偏向 model evidence 和 reviewer explanation

所以你可以这样理解：

- `Operational Decision Support`
  - 先讲哪台 machine 值得看
  - 再补 preview
- `Scenario Lab`
  - 直接讲 preview 逻辑本身

---

## 4.10 这个模块最容易讲错的 8 句话

不要说：

- `best scenario = 全局最优方案`
- `delta = 月度总节省`
- `baseline = 真实当前耗能`
- `preview = 执行建议`
- `preview = realized saving`
- `unsupported = 系统坏了`
- `template 可任意扩展`
- `只要有模型就一定有 preview`

应该说：

- `preview anchored on one real comparable seed row`
- `delta 是相对 baseline 的局部比较`
- `estimated_kwh_change 是 seed volume 下的估算`
- `unsupported template 代表当前 seed row 不支持该安全模板`

---

## 4.11 30 秒 talk track

> Scenario Lab 会先选当前 machine 的一条真实 canonical seed row，然后用 active saved model 先做 baseline prediction，再对三个很窄的 template intervention 做 scenario prediction。只有当 seed row 字段完整、而且 predictor 真正返回 model-source 结果时，这些 scenario 才会被支持。最后系统比较 delta vs baseline，并保留所有 supported 和 unsupported template。它给的是可解释 scenario evidence，不是执行计划，也不是 realized savings。

---

## 5. 这四个模块之间的关系，一次讲清楚

你可以按下面这张逻辑图去记：

### `Predictive Maintenance Prototype`

回答：

- 现在哪些 machine 更值得关注 maintenance risk

### `🎯 Operational Decision Support`

回答：

- 现在哪些 machine 更值得先 review operationally

### `Model Review Queue`

回答：

- 现在哪些 machine 更值得先做 model-side review

### `Scenario Lab`

回答：

- 如果对某个 one-row case 套一个安全模板，model evidence 会怎样变化

所以它们不是重复模块，而是四个不同问题：

- maintenance risk
- operational priority
- model review priority
- scenario evidence

---

## 6. presenter 版最短口径

如果你时间很紧，可以这样各用一句：

### Predictive Maintenance Prototype

> 这页做的是 current-state risk ranking：先从真实 machine-day snapshots 和 maintenance events 构造 weak labels，条件够就用 weak-label classifier，不够就退回 transparent evidence score。

### Operational Decision Support

> 这页做的是 deterministic machine prioritization：把单位产量能耗、非生产占比、维护时距和 scrap rate 合成 opportunity score，告诉 operator 哪台 machine 值得先看。

### Model Review Queue

> 这页做的是 model-backed review ranking：它不只是看 predicted value，而是看 machine 相对 peer baseline 差多少，再乘上 volume、confidence 和 support weight。

### Scenario Lab

> 这页做的是 one-row scenario evidence：它在一个真实 comparable seed row 上比较 baseline 和少量安全模板，不代表执行方案，也不代表 realized savings。

---

## 7. 最后再给你一个“千万别混”的对照表

| 模块 | 真正在做什么 | 不要讲成什么 |
| --- | --- | --- |
| Predictive Maintenance Prototype | current-state risk ranking | 故障日期预测器 |
| Operational Decision Support | rule-based machine prioritization | scheduling solver |
| Model Review Queue | model-side review priority | 执行队列 |
| Scenario Lab | one-row model preview | realized saving / executed plan |

---

## 8. 如果你下一步要继续学，推荐顺序

建议你按这个顺序再读 app：

1. `🎯 Operational Decision Support`
2. `Model Review Queue`
3. `Scenario Lab`
4. 最后再回看 `Predictive Maintenance Prototype`

原因：

- `Operational Decision Support` 最贴近 operator 直觉
- `Model Review Queue` 是它的 model-review 对应面
- `Scenario Lab` 是最容易被误讲的一块
- maintenance prototype 则是独立 experimental branch

这样学，脑中结构会最稳。
