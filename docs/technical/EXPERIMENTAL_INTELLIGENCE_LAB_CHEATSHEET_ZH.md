# Experimental Intelligence Lab 中文速查表

## 1. 一句话定位

`🧪 Experimental Intelligence Lab`
→ `实验性 bonus route`
→ `读取真实 canonical 数据和真实 maintenance history`
→ `做只读、可解释的未来智能原型验证`
→ `不是 production 决策页`

---

## 2. 先死记这 3 句

1. `Anchor month` 是 `当前状态锚点`，不是 `完整训练边界`。
2. `Real-seeded synthetic queue` 只是在补 `未来待排任务输入`，不是在伪造整页数据。
3. 这个页面的价值是 `展示可解释 prototype`，不是 `替你下正式决策`。

---

## 3. 整页怎么理解

```text
真实 canonical 数据
  + 真实 maintenance history
    ↓
Experimental Intelligence Lab
    ↓
Anchor month for current-state view
    ↓
分成两个子模块

Scheduling Prototype
→ 回答：未来任务怎么排更合理

Predictive Maintenance Prototype
→ 回答：当前哪些机器更值得优先关注
```

---

## 4. 顶部四张卡片的意思

`Current-State Anchor`
：你现在站在哪一个月看“当前状态”。

`Historical Support / Training Scope`
：虽然当前视角锚在某个月，但支撑证据和训练范围来自更宽历史。

`Scheduling Queue Provenance`
：排程输入里的 future queue 从哪里来。默认是 `real-seeded synthetic queue`。

`Maintenance Prototype Mode`
：维护原型当前是 `Weak-label model` 还是 `Fallback evidence score`。

---

## 5. Scheduling 一页看懂

### 核心逻辑

```text
Anchor month
→ 当前 machine pool

真实月份分布
→ real-seeded synthetic queue

historical support
 + maintenance evidence
 + energy estimate
→ feasible candidates
→ optimized schedule
→ 和 naive baseline 比较
→ 告诉你为什么这样排 / 为什么排不上
```

### 你先看什么

1. 保持默认值：
   `Queue size = 6`
   `Max jobs / machine = 2`
   `manual queue = off`
2. 先看：
   `Queue Rows`
   `Assigned Jobs`
   `Optimized Composite Score`
   `Naive Composite Score`
3. 再看：
   `Naive Baseline Comparison`
   `Score Breakdown`
   `Blocked / Excluded Reasons`

### 每块最该怎么读

`Default Real-Seeded Queue`
：看系统拿什么任务来做排程实验。

`Naive Baseline Comparison`
：看 optimized 是否比 naive 更低分、更合理。

`Score Breakdown`
：看总分为什么高或低。

```text
Predicted energy cost 高
→ 更耗能

Transition penalty 高
→ 材料切换成本高

Maintenance penalty 高
→ 维护风险高

Support penalty 高
→ 历史 support 弱
```

`Blocked / Excluded Reasons`
：看 job 排不上是被什么规则挡住，不是系统随机失败。

### 你最后该讲出的结论

- 当前机器池下，系统能排出一套可解释的 prototype schedule。
- 历史 support 越强、维护风险越低、模型可用性越高，越容易被排进去。
- optimized 比 naive 更低分，说明原型至少能做出有解释的改进。
- job 被 block 往往是约束在发挥作用，不代表系统坏掉。

---

## 6. Maintenance 一页看懂

### 核心逻辑

```text
Anchor month
→ current-state risk view

更宽历史 machine-day snapshots
 + 真实 maintenance events
→ weak-label construction

标签够
→ Weak-label model

标签不够
→ Fallback evidence score

最后输出
→ at-risk machine table
→ explain why this machine ranks high
```

### 你先看什么

1. 先保持：
   `Future maintenance horizon = 14`
2. 先看：
   `Historical Training / Label Scope`
3. 再看：
   `Current-State Risk View`
   `Current-State At-Risk Machine Table`
4. 最后看：
   `Selected Machine Evidence`
   `Top Evidence Factors`
   `Recent Work-Order Context`
5. 然后把 horizon 改成 `7` 再看一次变化。

### 每块最该怎么读

`Historical Training / Label Scope`
：先确认训练依据够不够，以及当前是 model 还是 fallback。

`Prototype Mode`
：`Weak-label model` 表示能训练；`Fallback evidence score` 表示系统诚实退回证据打分。

`Risk Score`
：适合做排序和相对比较，不要讲成正式故障概率。

`Observed Maintenance <= Horizon`
：这是审计字段，表示在当前 horizon 内是否真实观察到维护事件，不等于“系统命令你去修”。

`Top Evidence Factors`
：解释这台机器为什么排前，不是最终因果证明。

### 你最后该讲出的结论

- 当前 anchor month 下，系统能给出一张 current-state risk view。
- 风险表背后不是只看当前月，而是用了更宽历史来构造 machine-day 特征。
- 数据条件够时用 weak-label model，不够时退回 evidence score。
- 高风险机器通常能从维护间隔、近期维护频率、能效强度、非生产占比、PM ratio 等方向解释。

---

## 7. 最快 5 分钟上手

```text
1 分钟
打开模块
→ 选 June 2025
→ 看 warning
→ 看顶部四张卡片

2 分钟
进 Scheduling
→ 保持默认设置
→ 看 Queue Rows / Assigned Jobs / Optimized / Naive

3 分钟
看 Baseline Comparison
→ 看 Score Breakdown
→ 看 Blocked / Excluded Reasons

4 分钟
切到 Maintenance
→ horizon = 14
→ 看 Historical Training / Label Scope
→ 看 Current-State Risk View

5 分钟
看 At-Risk Machine Table
→ 看 Selected Machine Evidence
→ 看 Top Evidence Factors
→ horizon 改成 7 再看变化
```

---

## 8. 演示时的最短讲法

### 整页介绍

> 这是一个实验性智能模块实验室，用当前 canonical 数据骨架和真实 maintenance evidence 做只读原型验证，不属于正式 production scope。

### 讲 Scheduling

> 这里不是直接排真实 ERP 工单，而是用真实月份分布种出一个 future queue，再结合历史 support、维护证据和能耗估计，做一个可解释的约束排程原型。

### 讲 Maintenance

> 这里的 selected month 只锚定 current-state risk view，不代表只用一个月训练。系统会用更宽历史构造 weak labels；如果条件不够，就退回 evidence score。

---

## 9. 最常见误解

`误解 1`
：`Anchor month = 训练只用这一个月`

`正确理解`
：它只是当前状态观察锚点。

`误解 2`
：`synthetic queue = 整页是假数据`

`正确理解`
：只有 future pending queue 是 real-seeded synthetic，机器、support、maintenance evidence 仍然是真实的。

`误解 3`
：`Risk score = 正式坏机概率`

`正确理解`
：它是 prototype 风险排序分数，用于解释和相对比较。

---

## 10. 最后记忆锚点

```text
Anchor month
→ 当前状态锚点

Scheduling
→ 解释“怎么排更合理”

Maintenance
→ 解释“谁更值得优先关注”

整页价值
→ 用真实历史证据支撑可解释 prototype
→ 不是 production command center
```
