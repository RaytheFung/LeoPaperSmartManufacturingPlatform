# Experimental Intelligence Lab 端到端操作报告

## 1. 文档目的

这份文档的目标不是讲底层代码，而是让你以操作者视角，尽快完成三件事：

1. 第一次打开 `🧪 Experimental Intelligence Lab` 时，能马上知道自己看到的每一块信息代表什么。
2. 能独立操作两个子模块：
   - `Constraint-Aware Scheduling Prototype`
   - `Predictive Maintenance Prototype`
3. 能在演示、汇报或自测时，准确说出每一次操作后系统在传达什么信息，而不是只“看到了一个表”。

如果你只想先快速上手，可以先看第 `3` 节和第 `8` 节。  
如果你想真正读懂页面，再从第 `4` 节开始按顺序看。

---

## 2. 先建立正确心智模型

### 2.1 这个模块到底是什么

`🧪 Experimental Intelligence Lab` 是一个 **实验性 bonus route**。

它的定位不是：

- 不是正式 production module
- 不是已经落地的排程引擎
- 不是正式 predictive maintenance engine
- 不是一个会回写数据库的执行页面

它的定位是：

- 用现有 canonical 数据骨架做一个未来智能模块的安全实验页
- 用真实历史数据做支撑
- 用清楚的 provenance 告诉你，哪里是真实数据，哪里是基于真实数据构造的 prototype 输入
- 用只读方式做“可解释、可演示、可讨论”的实验结果

### 2.2 这个模块最重要的边界

你在使用和解释这个页面时，必须一直记住下面四句话：

1. 它是实验页，不是答辩中 defended core platform 的核心页面。
2. 它读取真实 canonical 数据和维护记录，但不会写 `manufacturing_data.db`。
3. 它会用 `real-seeded synthetic queue`，但这个 synthetic 只用于排程原型的未来待处理任务输入，不会混进正式历史数据。
4. 预测性维护原型使用真实 maintenance history 构造 weak labels，但它仍然是 prototype，不是正式维护建议引擎。

---

## 3. 第一次打开页面时，你应该怎么理解你看到的东西

下面这部分，完全站在“第一次进入页面的用户”视角来写。

### 3.1 页面标题和 warning 代表什么

页面标题是：

- `🧪 Experimental Intelligence Lab`

页面最上面的 warning 大意是：

- 这是实验 bonus 功能
- 不属于当前 defended production scope
- 不会写 DB
- 不会提升新 artifact
- 不宣称 solver
- 不宣称 production predictive maintenance

**你应该怎么理解：**

- 这不是让你“执行生产决策”的页面
- 这是让你“观察一个未来智能模块原型如何利用现有真实数据”的页面
- 所以你看到的是一个诚实、可解释、只读的实验环境

### 3.2 `Anchor month for current-state view` 代表什么

这是整个页面最关键的新设计。

它不是：

- “只用这一个月训练”
- “只看这一个月的所有逻辑”
- “两个子模块都只吃这一个月的数据”

它真正代表的是：

- 这个月是当前视角的锚点
- 当前机器池、当前风险切片、当前月成本代理等，是围绕这个月来看的
- 但页面背后用到的历史支持、历史训练、maintenance event window，可以比这个月更宽

**最实用理解方式：**

- 把它理解成“我现在站在哪一个月看当前状态”
- 不要把它理解成“模型只学了这一个月”

### 3.3 顶部四张 scope / provenance 卡片分别在说什么

#### A. `Current-State Anchor`

它告诉你：

- 你当前选中的 anchor month 是什么
- 当前机器池和当前切片是从哪个时间范围读出来的

你应该把它理解为：

- “我现在看的当前状态，是哪一个月的当前状态”

#### B. `Historical Support / Training Scope`

它告诉你：

- scheduling 的历史 support 并不只看当前月
- predictive maintenance 的 snapshot / weak-label 构造也不只看当前月
- 历史窗口一般会一直延伸到 anchor month 为止

你应该把它理解为：

- “当前视角在某个月，但证据和训练支持来自更长的真实历史”

#### C. `Scheduling Queue Provenance`

它告诉你：

- 排程页里的 future queue 是 `Real-seeded synthetic queue`
- 也就是：待排任务不是 live ERP 订单，但它是从真实月份里的 material / task / quantity 分布里种出来的

你应该把它理解为：

- “未来队列是模拟出来的，但模拟依据不是乱编，而是从真实月份统计特征出发”

#### D. `Maintenance Prototype Mode`

它告诉你：

- 当前维护原型可能运行在两种模式之一：
  - `Weak-label model`
  - `Fallback evidence score`

你应该把它理解为：

- “这个原型不一定每次都能用模型”
- “如果真实标签不够，它会诚实退回到 evidence-based fallback”

---

## 4. 整个模块的推荐端到端操作顺序

如果你是第一次上手，建议严格按这个顺序来。

### Step 1. 进入模块，先不要急着点任何高级选项

先做三件事：

1. 看 warning，确认这是实验页不是正式执行页
2. 看 `Anchor month for current-state view`
3. 看顶部四张卡片，确认：
   - 当前锚点月份
   - 历史支持/训练范围
   - 排程队列来源
   - 维护模式定义

### Step 2. 第一轮固定用 `June 2025`

第一次建议把 anchor month 直接选成：

- `June 2025`

原因很简单：

- 当前实验模块的 read-only smoke 就是围绕 `June 2025` 验证过的
- 你更容易看到完整的排程与风险结果

### Step 3. 先看 Scheduling，再看 Predictive Maintenance

推荐顺序：

1. 先打开 `Constraint-Aware Scheduling Prototype`
2. 看懂：
   - 当前队列来自哪里
   - 当前机器池来自哪里
   - score 是怎么比较 optimized vs naive 的
3. 再切到 `Predictive Maintenance Prototype`
4. 看懂：
   - 当前 risk table 只是 anchor month 的 current-state view
   - 但 training / weak-label scope 来自更宽历史

这样更容易建立“当前状态 vs 历史支持”的正确心智。

---

## 5. 子模块一：Constraint-Aware Scheduling Prototype 怎么用

## 5.1 这个子模块的核心问题是什么

它在回答：

- 如果我拿当前 anchor month 的机器池做一个未来任务排程实验
- 再结合历史 material/task 支持证据
- 再结合维护风险
- 再结合 active saved model 能不能给出 energy estimate

那么：

- 哪种排法比 naive baseline 更好
- 哪些任务能排
- 哪些任务排不上
- 为什么排不上

它不是在回答：

- 真实 ERP 订单应该怎么生产
- 最终工厂一定怎么排
- 这个结果已经能直接下发车间

### 5.2 你进入这个 tab 后，先看什么

先看 tab 开头那段说明。

它传达的关键信息是：

- 当前机器池是 anchor month 的
- 待排队列默认来自真实月份分布种出来的 synthetic queue
- 排分时会用历史 support 和 maintenance evidence
- 这不是 live MES/ERP queue
- 也不是 production scheduling engine

**你应该马上形成的理解是：**

- 这是一个“真实数据支撑下的排程实验页”
- 不是真实订单执行页

### 5.3 这个 tab 的推荐操作顺序

#### 第一轮操作：保持默认设置

第一次不要切 manual queue，先保留默认值：

- `Queue size = 6`
- `Max jobs / machine = 2`
- 不勾选 `Use manual demo queue instead of the default real-seeded queue`

这样做的好处是：

- 你先看系统默认的“真实优先”路径
- 先理解页面的 intended message
- 不会一上来就被手动构造数据打乱理解

#### 第二轮操作：只改一个控制项

当你看懂默认输出后，再单独尝试：

- 把 `Queue size` 从 `6` 改成 `5` 或 `8`
- 或把 `Max jobs / machine` 从 `2` 改成 `1` 或 `3`

你要观察的是：

- 可分配任务数有没有变化
- optimized vs naive 的差异是否变化
- blocked / excluded reasons 是否变化

#### 第三轮操作：最后才用 manual queue

只有当你想做 stress test 时，才展开：

- `Stress-test mode: Manual demo queue`

然后勾选：

- `Use manual demo queue instead of the default real-seeded queue`

这个功能适合做什么：

- 验证某种 material / task 组合会不会更难排
- 人工构造极端数量或紧急度
- 演示“系统如何响应不同输入”

这个功能不适合做什么：

- 不适合拿它当正式生产输入
- 不适合把结果说成真实工单排产结果

### 5.4 scheduling tab 里每一块信息代表什么

#### A. `Current-State Anchor`

表示：

- 当前机器池和 selected-month cost proxy 从哪个 anchor month 来

你得到的信息：

- “这次排程实验站在哪一个月的当前状态上做”

#### B. `Historical Support Window`

表示：

- compatibility 不是只看 anchor month
- 它会累计读取到 anchor month 为止的 canonical history

你得到的信息：

- “机器能不能做这个任务，不是凭空猜，而是看历史上有没有 support”

#### C. `Queue Provenance`

表示：

- 你现在看到的 queue 到底是默认 real-seeded 还是 manual stress-test

你得到的信息：

- “我现在是在看默认真实优先模式，还是看手工干预测试模式”

#### D. `Machine Pool Scope`

表示：

- 这次实验可被考虑的 machine pool 有多少台机器

你得到的信息：

- “当前 anchor month 下，系统实际拿多少机器来参与候选”

#### E. `Queue Rows`

表示：

- 当前 demo horizon 里有多少条待排任务

你得到的信息：

- “这次排程实验规模有多大”

#### F. `Assigned Jobs`

表示：

- 最终 optimized schedule 里排进去多少条

你得到的信息：

- “这个实验约束下，到底有多少任务成功分配”

#### G. `Optimized Composite Score`

表示：

- 优化排程方案的总分

你得到的信息：

- 这是 prototype objective
- 数值越低越好

#### H. `Naive Composite Score`

表示：

- 一个简单 baseline 的总分

你得到的信息：

- “优化方案相对于一个不聪明的 baseline 是否更好”

### 5.5 scheduling tab 里每个表该怎么看

#### 1. `Default Real-Seeded Queue` / `Manual Stress-Test Queue`

这是输入表。

你应该重点看：

- `preferred_machine_family`
- `material_code`
- `task_name`
- `task_difficulty`
- `quantity`
- `urgency_label`

你得到的信息：

- 系统到底拿什么任务去做排程实验

如果是默认 real-seeded queue，你应该理解为：

- 这是从真实月份统计模式中“种”出来的未来任务

如果是 manual queue，你应该理解为：

- 这是人为构造出来的 stress-test 输入

#### 2. `Naive Baseline Comparison`

这里是“优化方案 vs 朴素方案”的直接对比。

典型字段包括：

- `Assigned jobs`
- `Composite score`
- `Predicted energy cost`
- `Material transition penalty`

你应该怎么读：

- 先看 `Composite score`
- 再看 energy cost 和 material transition penalty

你得到的信息：

- 优化方案有没有更省
- 更省的来源主要在哪里

#### 3. `Score Breakdown`

这里把总分拆开。

你会看到：

- `Predicted energy cost`
- `Transition penalty`
- `Maintenance penalty`
- `Support penalty`
- `Urgency penalty`
- `Model unavailable penalty`
- `Composite total`

你应该怎么读：

- 如果 `Predicted energy cost` 高，说明模型估计该排法更耗能
- 如果 `Transition penalty` 高，说明材料切换代价大
- 如果 `Maintenance penalty` 高，说明机器维护风险高
- 如果 `Support penalty` 高，说明历史 support 不强
- 如果 `Model unavailable penalty` 高，说明系统没法对某些候选诚实使用 active model

你得到的信息：

- 系统为什么更偏向某个排法，而不是只给你一个黑箱总分

#### 4. `Constraint Summary`

这是规则说明表。

它告诉你这次实验用了哪些明确约束：

- 一条 job 只能占一个 machine slot
- machine 必须先匹配 family，再看历史 support
- 维护 blackout 何时触发
- material transition penalty 怎样计入
- urgency 是怎样代理出来的
- 每台机器最多放几条 job

你得到的信息：

- “系统是按什么规则在筛和排”

#### 5. `Feasible Assignment Candidates`

这是候选可行分配表。

你应该重点看：

- `machine_id`
- `support_tier`
- `maintenance_status`
- `model_supported`
- `estimated_energy_cost`
- `total_score`

你得到的信息：

- 每个 job 在哪些 machine 上是“可以考虑的”
- 每种可行分配为什么分数不同

#### 6. `Optimized Schedule`

这是最终建议排法。

你应该把它理解成：

- 当前 prototype objective 下的最优近似方案

你得到的信息：

- 最终每个 job 被分配到了哪台机器
- 分配顺序是什么
- 它背后的 support / maintenance / model 状态如何

#### 7. `Reference & Audit: Naive schedule details`

这是参考用，不是主结论。

你得到的信息：

- 如果不用优化，而是走简单 baseline，会排成什么样

#### 8. `Blocked / Excluded Reasons`

这是非常重要的诊断表。

常见含义包括：

- `incompatible_machine_family`
  - 机器 family 根本不匹配
- `maintenance_blackout`
  - 机器被维护黑名单规则挡住
- `max_jobs_per_machine_reached`
  - 这台机器已经达到本次实验允许的 job 上限

你得到的信息：

- 哪些问题是“本来就不该排”
- 哪些问题是“规则太紧”
- 哪些问题是“机器池或输入设定限制”

### 5.6 scheduling tab 中你会收到什么 message，它们分别是什么意思

#### 顶部 caption

内容大意：

- 由于当前平台没有 live ERP/MES future order book，所以默认使用 real-seeded synthetic pending queue
- 但 machine、energy、support、maintenance evidence 仍然是真实的

你应该理解为：

- synthetic 只是在补“未来待排任务输入”这个缺口
- 不是在把整页变成假数据

#### 中间 info

内容大意：

- compatibility/support tiers 来自 anchor month 之前的历史 canonical evidence
- maintenance penalties 来自真实 maintenance evidence

你应该理解为：

- 这个排程不是手工拍脑袋
- 它有真实历史支持和维护证据

#### 底部 info

内容大意：

- 这是 deterministic、constraint-aware、transparent weighted score 的 prototype
- 不是 live scheduling engine
- 也不是 shop-floor feasibility proof

你应该理解为：

- “它适合讨论、比较、展示，不适合直接执行”

### 5.7 作为用户，你可以从 scheduling tab 得到什么结论

你最终应该输出的是这类结论：

- 在当前 anchor month 的机器池下，系统能生成一个真实分布种出来的未来任务队列
- 历史 material/task support 越强、维护风险越低、模型可用性越高的机器，更容易被排进去
- optimized schedule 相对 naive baseline 更低分，说明这个 prototype 至少能做出有解释的改进
- 如果很多任务被 block，不代表系统坏了，往往代表约束、family 匹配或维护状态在发挥作用

---

## 6. 子模块二：Predictive Maintenance Prototype 怎么用

## 6.1 这个子模块的核心问题是什么

它在回答：

- 在 anchor month 的 current-state view 下
- 哪些机器现在看起来更值得关注
- 这个判断是基于真实 maintenance history 构造出来的 weak-label model
- 还是因为标签条件不够，所以退回到 fallback evidence score

它不是在回答：

- 机器何时一定会坏
- 应该立即下发哪张工单
- 这是正式 predictive maintenance product

### 6.2 进入 tab 后，先看什么

先看顶部说明和 info。

它传达的关键信息是：

- 当前选中的 month 只锚定 current-state risk view
- 历史 machine-day training scope 更宽
- 只有当真实 future maintenance window 足够可观察时，才会附上 weak labels

你应该立刻形成的理解是：

- “当前风险表是当前月视角”
- “训练和标签逻辑不是只用当前月”

### 6.3 推荐操作顺序

#### 第一轮操作：先保留默认 horizon

第一次先保留：

- `Future maintenance horizon = 14`

这样你先看到系统默认想表达的 risk view。

#### 第二轮操作：再切换到 `7`

然后把 horizon 改成：

- `7`

观察：

- `Prototype Mode` 有没有变化
- `Class Counts` 有没有变化
- 当前风险表排序有没有变化
- 某台机器的 `Observed Maintenance <= Horizon` 有没有变化

这一步能帮助你理解：

- horizon 改变后，弱标签构造条件和当前观测结果会跟着变化

### 6.4 maintenance tab 里每一块信息代表什么

#### A. `Historical Training / Label Scope`

这是全 tab 最关键的第一部分。

它在回答：

- 历史 snapshot 窗口有多宽
- 真正能构造 weak labels 的 observation scope 有多少
- 当前是模型模式还是 fallback 模式
- 正负样本数量各多少

你得到的信息：

- “这个原型的训练证据够不够”
- “当前结论是模型支持的，还是证据打分支持的”

#### B. `Historical Snapshot Window`

表示：

- machine-day features 来自多宽的历史窗口

你得到的信息：

- “当前训练特征不是只看当前月”

#### C. `Weak-Label Observation Scope`

表示：

- 在当前 horizon 下，有多少 snapshot 真的拥有可观察未来窗口

你得到的信息：

- “这次 weak-label training 的真实可用样本有多少”

#### D. `Prototype Mode`

你会看到两种可能：

- `Weak-label model`
- `Fallback evidence score`

你应该怎么理解：

- `Weak-label model`：说明当前数据足够支持一个真正的轻量时间感知分类器
- `Fallback evidence score`：说明当前标签太 sparse 或太浅，系统诚实退回解释型 evidence 打分

#### E. `Class Counts`

表示：

- 正样本 / 负样本数量

你得到的信息：

- 当前训练数据是否平衡到足够“像样”

#### F. `Current-State Risk View`

这是第二个关键部分。

它在回答：

- 当前 risk table 站在哪个 anchor month 看
- 最新 snapshot 日期是什么
- 当前月总共评分了多少机器
- 当前 horizon 是多少天

你得到的信息：

- “我现在看的不是历史总体风险，而是 anchor month 的 current-state slice”

### 6.5 risk table 每一列该怎么看

你会在 `Current-State At-Risk Machine Table` 里看到这些列：

#### `Machine`

表示机器编号。  
你用它来定位具体设备。

#### `Snapshot Date`

表示该机器被评分时对应的 latest snapshot 日期。  
它不是整个训练窗口的日期，而是当前 risk view 里的当前切片日期。

#### `Prototype Mode`

表示当前这张风险表的分数来源是：

- `Weak-label model`
- 或 `Fallback evidence score`

#### `Risk Score`

表示风险分数。  
你可以把它理解为“当前值得优先关注的程度”。

注意：

- 它适合做排序和相对比较
- 不要把它讲成正式故障概率承诺

#### `Risk Band`

表示一个更容易阅读的风险等级带。

你得到的信息：

- 方便你快速筛高风险机器

#### `Days Since Last Maintenance`

表示距离最近维护已经过去多少天。

你得到的信息：

- 如果这个值很高，说明机器长时间没维护，风险解释上通常更敏感

#### `Events (30d)`

表示最近 30 天内维护事件数量。

你得到的信息：

- 如果近期事件很多，可能意味着设备最近维护活动频繁

#### `PM Ratio (All Time)`

表示全历史里 preventive maintenance 的占比。

你得到的信息：

- 占比偏低时，常常代表 preventive maintenance 的长期占比弱

#### `Weighted kWh / Good Unit (30d)`

表示过去 30 天的加权能效强度。

你得到的信息：

- 如果这个值升高，说明最近产出单位对应的能耗强度更高

#### `Non-Productive Share (30d)`

表示近 30 天非生产性时间占比。

你得到的信息：

- 如果这个值更高，说明最近的停顿/非生产占比更高

#### `Observed Maintenance <= Horizon`

表示在当前 horizon 内，系统是否真实观察到 maintenance event。

你应该怎么理解：

- 这是一个审计字段
- 它说明“在这个 horizon 下，这条记录后面是否真实发生过维护事件”
- 不要把它理解成“系统建议一定要修”

### 6.6 `Selected Machine Evidence` 区域怎么用

风险表通常会默认取当前排在最前的一台机器作为 selected machine。

这里的卡片告诉你：

- 机器是谁
- 当前 risk score 是多少
- 当前 risk band 是什么
- 距离上次维护多久
- 最近 30 天维护事件数是多少

你得到的信息：

- “为什么它会排到前面”

### 6.7 `Top Evidence Factors` 怎么读

这里不是在给你“最终因果结论”，而是在给你“当前风险分数最值得看的证据方向”。

常见项包括：

- `Days since last maintenance`
- `Recent maintenance events (30d)`
- `Weighted kWh / Good Unit (30d)`
- `Non-productive share (30d)`
- `Low PM ratio (all time)`

你应该怎么读：

- 看 `Peer Percentile`
- percentile 越高，说明这个特征在当前 snapshot 群体里越突出

你得到的信息：

- “这台机器为什么在当前月被推到前面”

### 6.8 `Recent Work-Order Context` 怎么用

这里给的是最近维护工单上下文。

你得到的信息：

- 系统不是只给一个 risk score，还把最近维护历史摆出来给你对照

它适合做什么：

- 演示时证明这个页面不是纯黑箱
- 追问某台机器近期维护是否频繁

### 6.9 maintenance tab 中你会收到什么 message，它们分别是什么意思

#### 顶部 info

内容大意：

- selected month 只锚定 current-state risk view
- historical machine-day training 使用更广历史
- weak labels 只在真实 future window 可观察时才附着

你应该理解为：

- 这个页面已经明确把“当前切片”和“历史训练”分开了

#### 底部 info

内容大意：

- 这是基于 existing maintenance tables 和 weak labels 的 experimental predictive-maintenance prototype
- 不是 production maintenance recommendation engine

你应该理解为：

- 可以用于讨论“哪些机器值得注意”
- 不能表述成“系统已经给出正式维修命令”

### 6.10 作为用户，你可以从 maintenance tab 得到什么结论

你最终应该输出的是这类结论：

- 当前 anchor month 下，系统可以给出一张 current-state risk view
- 这张风险表背后并不是只看当前月，而是使用更宽历史构造 machine-day 特征
- 如果数据条件足够，它会给出 weak-label model；如果不够，它会诚实退回 fallback evidence score
- 高风险机器之所以排前，通常可以从 maintenance recency、近期维护频率、能效强度、非生产占比、PM ratio 等证据方向得到解释

---

## 7. 从用户角度看：每一次操作后你到底“得到了什么消息”

这里把“操作”和“系统在向你传达什么”直接对齐。

| 你的操作 | 系统向你传达的消息 |
|---|---|
| 进入模块 | 这是实验页，不是正式执行页 |
| 选择 `Anchor month for current-state view` | 你切换的是当前状态观察锚点，不是完整训练边界 |
| 看顶部四张卡片 | 系统在主动告诉你当前状态、历史支持、synthetic 队列来源、维护模式来源 |
| 保持默认 queue 不展开 manual | 系统鼓励你先看真实优先的默认使用方式 |
| 改 `Queue size` | 你在调整实验 horizon 的大小 |
| 改 `Max jobs / machine` | 你在调整排程约束强弱 |
| 展开 manual queue 并勾选 | 你进入 stress-test 模式，不再是默认真实优先路径 |
| 看 `Naive Baseline Comparison` | 系统在告诉你优化方案有没有比 baseline 更合理 |
| 看 `Score Breakdown` | 系统在告诉你“为什么这个方案更好/更差” |
| 看 `Blocked / Excluded Reasons` | 系统在告诉你任务排不上不是随机，而是被具体规则挡住 |
| 切到 maintenance tab | 你从“排程实验”转到“风险识别实验” |
| 改 `Future maintenance horizon` | 你在改变弱标签定义和当前观察窗口 |
| 看 `Historical Training / Label Scope` | 系统在告诉你训练依据到底够不够、真实不真实 |
| 看 `Current-State Risk View` | 系统在告诉你当前月值得优先关注哪些机器 |
| 看 `Top Evidence Factors` | 系统在告诉你当前高风险不是黑箱排序 |
| 看 `Recent Work-Order Context` | 系统在告诉你风险排序背后有真实维护上下文支撑 |

---

## 8. 最快上手版：5 分钟实操流程

如果你现在就要上手，我建议你这样做：

### 第 1 分钟

1. 打开 `🧪 Experimental Intelligence Lab`
2. 把 `Anchor month for current-state view` 设为 `June 2025`
3. 看 warning 和顶部四张卡片

你的目标：

- 先把“当前锚点”和“历史支持范围”分清楚

### 第 2 分钟

1. 停留在 `Constraint-Aware Scheduling Prototype`
2. 保持默认：
   - `Queue size = 6`
   - `Max jobs / machine = 2`
   - 不勾选 manual queue
3. 看 `Queue Rows`、`Assigned Jobs`、`Optimized Composite Score`、`Naive Composite Score`

你的目标：

- 先知道系统默认排出了一套什么结果

### 第 3 分钟

1. 看 `Naive Baseline Comparison`
2. 看 `Score Breakdown`
3. 看 `Blocked / Excluded Reasons`

你的目标：

- 先知道“更优”体现在哪里
- 再知道“排不上”的原因是什么

### 第 4 分钟

1. 切换到 `Predictive Maintenance Prototype`
2. 保持 `Future maintenance horizon = 14`
3. 先看 `Historical Training / Label Scope`
4. 再看 `Current-State Risk View`

你的目标：

- 把“训练范围”和“当前风险视图”分开理解

### 第 5 分钟

1. 看 `Current-State At-Risk Machine Table`
2. 看第一台 machine 的 `Selected Machine Evidence`
3. 看 `Top Evidence Factors`
4. 最后把 horizon 改成 `7` 再看一次变化

你的目标：

- 快速理解某台机器为什么被推到前面
- 看懂 horizon 改变会如何影响当前风险解释

---

## 9. 演示或汇报时最推荐的讲法

如果你需要对老师、评审或队友解释这个模块，我建议用下面这套说法。

### 9.1 一句话介绍整个页面

可以这样说：

> 这个页面是一个实验性智能模块实验室，用当前 canonical 数据骨架做只读原型验证。它把当前状态锚点、历史支持范围、synthetic queue 的使用边界，以及 weak-label maintenance 风险识别分开讲清楚。

### 9.2 介绍 scheduling prototype 时

可以这样说：

> 这里不是拿真实 ERP 工单直接排产，而是从真实月份的 material / task / quantity 分布生成一个 real-seeded synthetic queue，再结合历史 support、维护证据和当前 active model 的能耗估计，做一个可解释的约束排程原型。

### 9.3 介绍 predictive maintenance prototype 时

可以这样说：

> 这里的 selected month 只锚定当前风险视图，不代表只用一个月训练。系统会用更宽的历史 machine-day snapshots 和真实 maintenance events 构造 weak labels；如果条件不够，就退回到 evidence score，而不是假装模型一定可用。

---

## 10. 最后你应该记住的三句话

1. `Anchor month` 是当前状态锚点，不是完整训练边界。
2. `Real-seeded synthetic queue` 只是在补未来待排任务输入，不是在伪造整页数据。
3. 这个页面的价值不在“替你做正式决策”，而在“用真实历史证据支撑一个可解释、可展示的未来智能模块原型”。
