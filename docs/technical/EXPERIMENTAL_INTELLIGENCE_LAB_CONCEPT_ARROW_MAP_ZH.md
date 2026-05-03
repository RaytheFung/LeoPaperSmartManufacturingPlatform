# Experimental Intelligence Lab 概念箭头图 + 组件注释

## 1. 一句话先抓住它

`🧪 Experimental Intelligence Lab`
→ `实验性 bonus route`
→ `读取真实 canonical 数据与真实 maintenance history`
→ `在只读前提下做未来智能模块原型验证`
→ `输出可解释、可演示、可讨论的 prototype 结果`
→ `不是 production 决策页面`

---

## 2. 总体概念箭头图

```text
真实 canonical 数据
  + 真实 maintenance history
  + active artifact / energy estimate
    ↓
Experimental Intelligence Lab
    ↓
Anchor month for current-state view
    ↓
把“当前状态观察锚点”固定下来
    ↓
分成两个实验子模块

[A] Constraint-Aware Scheduling Prototype
    ↓
real-seeded synthetic future queue
    + anchor month machine pool
    + historical support
    + maintenance evidence
    + model-backed energy estimate (if available)
    ↓
feasible candidates
    ↓
optimized schedule vs naive baseline
    ↓
score breakdown + blocked reasons
    ↓
告诉你“为什么这样排 / 为什么排不上”

[B] Predictive Maintenance Prototype
    ↓
anchor month current-state risk slice
    + broader historical machine-day snapshots
    + weak-label construction from real maintenance events
    ↓
Weak-label model
    或
Fallback evidence score
    ↓
current at-risk machine table
    ↓
selected machine evidence + top evidence factors + recent work-order context
    ↓
告诉你“为什么这台机器值得优先关注”
```

---

## 3. 先记住 4 个总边界

```text
Experimental Lab
→ 是实验页
→ 不是 defended core platform 页面
→ 读取真实数据
→ 不写 manufacturing_data.db
→ 可以使用 synthetic queue 补未来任务输入缺口
→ 不把 synthetic 混进正式历史数据
→ predictive maintenance 用 weak labels / fallback
→ 不宣称正式 maintenance recommendation engine
```

### 注释

`是实验页`
：你是在观察“未来智能模块怎么利用现有真实数据”，不是在做正式生产操作。

`不写 DB`
：所以它是安全的 demo / discussion surface，不会回写业务结果。

`synthetic queue 只补未来输入`
：它解决的是“系统没有 live ERP/MES future order book”这个现实缺口，不是把整页变成假数据。

`prototype，不是 production`
：所有结果都应解释为“有证据支撑的实验输出”，而不是正式指令。

---

## 4. 顶部四张卡片怎么串起来理解

```text
Current-State Anchor
    ↓
你现在站在哪一个月看“当前状态”

Historical Support / Training Scope
    ↓
虽然当前视角锚在某个月
但支持证据 / 训练窗口来自更长历史

Scheduling Queue Provenance
    ↓
排程输入里的 future queue 从哪里来
默认是 real-seeded synthetic queue

Maintenance Prototype Mode
    ↓
当前 maintenance 原型是
Weak-label model
还是
Fallback evidence score
```

### 最重要的心智模型

```text
Anchor month
≠ 完整训练边界

Anchor month
= 当前状态观察锚点
```

如果你只记一句，就记这个。

---

## 5. Scheduling Prototype 概念箭头图

```text
Anchor month
    ↓
current machine pool
    +
selected-month cost proxy

真实月份分布
    ↓
real-seeded synthetic queue
    或
manual stress-test queue

historical canonical support
    +
maintenance evidence
    +
energy estimate / model availability
    ↓
Feasible Assignment Candidates
    ↓
按约束与加权分数筛选
    ↓
Optimized Schedule
    ↓
和 Naive Baseline 比较
    ↓
Score Breakdown
    +
Blocked / Excluded Reasons
    ↓
结论：
哪些 job 能排
哪些 job 不能排
为什么 optimized 比 naive 更合理
```

### 组件注释

`Current-State Anchor`
：说明这次排程实验站在哪个 anchor month 的当前机器池上运行。

`Historical Support Window`
：说明 compatibility 不是拍脑袋，而是累计读取到 anchor month 为止的真实 canonical history。

`Queue Provenance`
：区分你当前看的是默认 real-seeded queue，还是手工 stress-test queue。

`Machine Pool Scope`
：告诉你这次实验实际可用的候选机器有多少台。

`Queue Rows`
：这次实验 horizon 里总共有多少待排任务。

`Assigned Jobs`
：最终 optimized schedule 成功塞进去了多少 job。

`Optimized Composite Score`
：prototype objective，总体越低越好。

`Naive Composite Score`
：透明 baseline，用来说明优化是否真的带来更优结果。

`Default Real-Seeded Queue / Manual Stress-Test Queue`
：这是输入表。重点看 `preferred_machine_family`、`material_code`、`task_name`、`quantity`、`urgency_label`。

`Naive Baseline Comparison`
：先看 `Composite score`，再看 energy cost 和 transition penalty，判断 optimized 相比 naive 好在哪里。

`Score Breakdown`
：把黑箱总分拆开。你真正要读的是：

```text
Predicted energy cost 高
→ 该排法更耗能

Transition penalty 高
→ 材料切换成本高

Maintenance penalty 高
→ 机器维护风险高

Support penalty 高
→ 历史 support 不强

Model unavailable penalty 高
→ 某些候选无法诚实调用 active model
```

`Constraint Summary`
：规则说明表。它告诉你系统究竟按什么规则筛和排。

`Feasible Assignment Candidates`
：候选可行分配表。重点看 `machine_id`、`support_tier`、`maintenance_status`、`model_supported`、`estimated_energy_cost`、`total_score`。

`Optimized Schedule`
：当前 prototype objective 下的最优近似方案，不是车间正式下发排程。

`Blocked / Excluded Reasons`
：诊断表，不是坏消息表。它在告诉你“排不上”是因为规则、机器池、family 匹配或维护状态，而不是系统随机失败。

---

## 6. Scheduling Prototype 的操作顺序图

```text
第一次进入 scheduling tab
    ↓
先保持默认
Queue size = 6
Max jobs / machine = 2
manual queue = off
    ↓
先看默认真实优先路径长什么样
    ↓
看 Queue Rows / Assigned Jobs / Optimized Score / Naive Score
    ↓
建立“系统默认排出了什么”这个基线
    ↓
再看 Naive Baseline Comparison
    ↓
知道 optimized 比 naive 好在哪里
    ↓
再看 Score Breakdown
    ↓
知道为什么更好
    ↓
最后看 Blocked / Excluded Reasons
    ↓
知道为什么有些任务排不上
    ↓
第二轮才改 Queue size 或 Max jobs / machine
    ↓
观察约束强弱改变后的结果变化
    ↓
最后才开 manual stress-test
    ↓
用来做极端输入测试
```

### 你每一步真正学到什么

`改 Queue size`
：你在改实验 horizon 大小。

`改 Max jobs / machine`
：你在改约束强弱。

`打开 manual queue`
：你切换到 stress-test，不再是默认真实优先路径。

---

## 7. Predictive Maintenance Prototype 概念箭头图

```text
Anchor month
    ↓
current-state risk view

broader machine-day history
    +
real maintenance event history
    ↓
weak-label construction
    ↓
如果标签足够
    ↓
Weak-label model

如果标签不足
    ↓
Fallback evidence score

然后统一输出
    ↓
Current-State At-Risk Machine Table
    ↓
Selected Machine Evidence
    +
Top Evidence Factors
    +
Recent Work-Order Context
    ↓
结论：
当前月下哪些机器更值得优先关注
以及这种排序为什么成立
```

### 组件注释

`Historical Training / Label Scope`
：这部分最关键。它告诉你“训练依据够不够”和“当前到底是模型模式还是 fallback 模式”。

`Historical Snapshot Window`
：machine-day 特征来自多宽的历史窗口，不是只看 anchor month。

`Weak-Label Observation Scope`
：在当前 horizon 下，真实可观测未来窗口的 snapshot 有多少。

`Prototype Mode`
：可能是 `Weak-label model` 或 `Fallback evidence score`。前者表示能训练轻量分类器，后者表示系统诚实退回证据打分。

`Class Counts`
：正负样本数，用来判断弱标签数据是否够像样。

`Current-State Risk View`
：这不是历史总体风险，而是 anchor month 下的当前切片风险视图。

`Current-State At-Risk Machine Table`
：主风险表。它解决的是“现在优先看谁”，不是“谁一定会坏”。

`Risk Score`
：适合做排序和相对比较，不应讲成正式故障概率承诺。

`Risk Band`
：风险带，方便快速筛机器。

`Observed Maintenance <= Horizon`
：审计字段，表示这条记录后面在当前 horizon 内是否真实观察到了维护事件；不是“系统建议一定要修”。

`Selected Machine Evidence`
：解释榜首机器为什么会排前。

`Top Evidence Factors`
：解释方向，不是最终因果证明。重点看 `Peer Percentile`，越高说明该特征在同批机器里越突出。

`Recent Work-Order Context`
：把最近维护上下文摆出来，说明这个 risk view 不是纯黑箱。

---

## 8. Predictive Maintenance 的操作顺序图

```text
第一次进入 maintenance tab
    ↓
先保持 Future maintenance horizon = 14
    ↓
先看 Historical Training / Label Scope
    ↓
确认：
训练窗口多宽
标签是否足够
现在是 model 还是 fallback
    ↓
再看 Current-State Risk View
    ↓
确认：
当前月评分了多少机器
最新 snapshot 是哪天
    ↓
看 Current-State At-Risk Machine Table
    ↓
知道谁排在前面
    ↓
看 Selected Machine Evidence
    ↓
知道榜首机器的摘要原因
    ↓
看 Top Evidence Factors
    ↓
知道风险排序最突出的证据方向
    ↓
看 Recent Work-Order Context
    ↓
拿真实维护上下文对照
    ↓
最后把 horizon 从 14 改到 7
    ↓
观察 mode / class counts / risk ordering / observed maintenance 是否变化
```

### 你每一步真正学到什么

`先看 Historical Training / Label Scope`
：先分清训练依据与当前风险视图，避免误把当前月当成全量训练边界。

`改 horizon`
：你改的不只是展示窗口，也会影响 weak-label 定义与观测条件。

---

## 9. 两个子模块如何连成一条完整故事线

```text
同一个 anchor month
    ↓
Scheduling Prototype 回答
“如果站在当前月的机器池上，未来待排任务怎么做更合理的原型排法？”

Predictive Maintenance Prototype 回答
“如果站在当前月的风险切片上，哪些机器现在更值得优先关注？”

两者共通的底层逻辑
    ↓
当前状态 = anchor month
历史证据 = broader real history
输出性质 = explainable read-only prototype
```

### 最稳的总解释

```text
Scheduling
→ 决定“怎么排更合理”

Maintenance
→ 决定“哪台机器更该关注”

两者都不是正式执行引擎
→ 而是用真实历史证据支撑的实验性智能原型
```

---

## 10. 5 分钟上手路线图

```text
第 1 分钟
进入模块
→ 选 June 2025
→ 看 warning
→ 看顶部四张卡片

第 2 分钟
进 scheduling
→ 保持默认设置
→ 看 Queue Rows / Assigned Jobs / Optimized / Naive

第 3 分钟
看 Naive Baseline Comparison
→ 看 Score Breakdown
→ 看 Blocked / Excluded Reasons

第 4 分钟
切到 maintenance
→ 保持 horizon = 14
→ 看 Historical Training / Label Scope
→ 看 Current-State Risk View

第 5 分钟
看 At-Risk Machine Table
→ 看 Selected Machine Evidence
→ 看 Top Evidence Factors
→ 把 horizon 改成 7 再看变化
```

---

## 11. 演示时可以直接照着讲的版本

### 11.1 介绍整个页面

```text
这是一个实验性智能模块实验室。
它复用当前 canonical 数据骨架和真实 maintenance evidence，
在只读前提下验证两个未来智能方向：
一个是约束排程原型，
一个是预测性维护原型。
```

### 11.2 介绍 scheduling prototype

```text
这里不是拿真实 ERP 工单直接排产，
而是从真实月份分布种出一个 future queue，
再结合历史 support、维护证据和能耗估计，
做一个可解释的 constraint-aware scheduling prototype。
```

### 11.3 介绍 predictive maintenance prototype

```text
这里的 selected month 只锚定 current-state risk view，
不代表只用一个月训练。
系统会用更宽历史构造 machine-day snapshots 和 weak labels；
如果标签条件不够，就诚实退回 evidence score。
```

---

## 12. 最终记忆锚点

```text
Anchor month
→ 当前状态锚点
→ 不是完整训练边界

Real-seeded synthetic queue
→ 只补未来任务输入缺口
→ 不是假造整页数据

Prototype value
→ 不在于替你下正式决策
→ 在于用真实历史证据支撑一个可解释、可展示的未来智能模块原型
```
