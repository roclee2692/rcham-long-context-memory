# RCHAM Research Closeout — 最终复核与停止决定

日期：2026-09-15。复核对象：`c9b8b19f42298a158485090a2d93da36aa3a58d9`。

## 最终决定

**终止 RCHAM 作为当前新架构研究方向的继续投入；停止 post-use task-utility 路线；不再修复 benchmark 或启动后续实现。**

停止的依据是：缺少可信的增量收益证据，既有工作的重叠风险较高，已用完约定的一次修正投入。无需证明一个世界范围的否定命题，才能决定停止一个项目。

科学结论必须同时更正：**Phase 1R 没有完成对真实 frozen answer model 的 task utility 与忠实 RMM signal 的有效对照，不能写成“真实 LLM 上该假设已被证伪”。**旧报告确实有可重算的模拟器负结果，但实验定义与所声称的问题仍存在实质差异。这是此前 AI 实现与报告的问题，不能用来把用户的架构设想判成普遍错误。

正式状态：

```text
RCHAM broad architecture:
TERMINATED AS CURRENT NOVELTY DIRECTION

Post-use task-utility route:
CLOSED — INSUFFICIENT VALIDATED BENEFIT

Phase 1R implementation:
NEGATIVE SIMULATOR RESULT; MATERIAL VALIDITY LIMITATIONS

General claim about real-LLM task utility:
NOT ESTABLISHED / NOT ADEQUATELY TESTED

Next action:
ARCHIVE ONLY; NO FURTHER EXPERIMENT OR ARCHITECTURE IMPLEMENTATION
```

不采用未加限定的 `REJECTED BY PHASE 1R` 标签，以免未来把项目停止决定误读为真实模型上的科学定论。

## 本次做了什么

- 阅读生成器、scorer、controller、评分与 gate 代码，并进行独立只读交叉审阅。
- 只从现存 108 episodes / 648 policy traces 重新汇总指标，核对原 manifest 的 SHA-256。未导入或调用原实验模块，未运行测试、generator、模型或 controller。
- 重新核对 RMM preprint v1 的公式与实际比较对象；没有重新进行全领域文献检索，因此不声称穷尽已有方法。
- 归档原始 synthetic traces、episodes、manifest 和原指标的压缩副本；原文件保留。
- 所有新的统计都是**旧数据的审计**，不是 Phase 1R 第二次修正或新的正式实验。

原始 trace SHA-256：

```text
f96c08034211363dd12ca14055bef215e8377da578e006fd1e270791dacd6930
```

证据入口：[审计脚本](../closeout/audit_existing_phase1r.py)、[统计 JSON](../closeout/phase1r_audit_summary.json)、[逐单元 CSV](../closeout/phase1r_audit_cells.csv)、[汇总 CSV](../closeout/phase1r_audit_aggregates.csv)、[归档清单](../closeout/evidence/manifest.json)。

## 关键复核发现

### 1. Task Utility 仍是词面覆盖评分，不是真实答案模型的 NLL

`answer_model.py:28–58` 取 gold answer 中每个词，检查它是否在 context 的词集合里；出现就给 log-sigmoid(3)，不出现给 log-sigmoid(-3)。`question` 从未参与计算，也没有归一化的下一个答案 token 分布或生成答案过程。

由于 `log(sigmoid(3)) - log(sigmoid(-3)) = 3`，当前实现精确等价于：

```text
utility(block) = 3 × 删除该块后不再出现的 gold-answer token 次数
```

它确实做了逐块删除后的重新评分，较 `1/n` 有区别；但这是**词面覆盖的消融**，并不满足“真实 frozen answer model 的 task-level NLL”要求。108/108 单元中的 utility 都是 3 的整数倍，与该公式一致。它不能处理语义等价、关系方向、矛盾和状态优先级，也不能表达移除错误信息后答案反而改善的负 utility。

### 2. RMM-like 仍退化成手工 attention 常量

`policies.py:120–123` 仍使用 `attention_weight × answer_correct`。新的 correctness 是计算出来的，但判据只要求完整 context 比全部遮蔽多命中至少一个答案词；并非注释所说的“全部词正确”，更不是 teacher-forced prediction correctness。

从现存 traces 核实：**108/108 个 q1 的 correctness 都为 True，108/108 的 RMM 分数与生成器手写 attention 完全相同。**

[RMM v1 原文 §4–5](https://arxiv.org/html/2607.24667v1) 的 DU 是固定滞后窗口内，将每个位置的实际 attention 乘以该位置 teacher-forcing 下预测是否正确后求和；其 buffer 与 commit 规则也参与方法定义。当前没有这些 token 级测量与 buffer，仅在 q1 后做一次 block 分数更新。因此只能称 `handcrafted_attention_proxy`，不能据此判定论文中的 RMM 已胜过真实 task-level utility。

### 3. 三个 seed 没有产生独立任务变化

`generate_data.py` 的 seed 仅改变 `write_nonce`；payload、query、候选、attention、顺序均相同，policy 不读 nonce。去除 nonce 后，36 个 scenario-capacity-pressure 组合各自的三个 seed 完全一致。

因此 108 单元是 36 个决策相关序列的重复，且仍只有九种固定语义模板。旧的 24 个负例来自两个模板 × 两种容量 × 两种压力 × 三个无行为影响的 seed，**不是 24 次独立失败证据**。

### 4. “answer accuracy”是 evidence ID 可用率，retention 口径也有错误

`policies.py:87–98` 仅检查指定 evidence ID 是否都在 hot；它没有让模型基于该 policy 保留的上下文生成答案。另行记录的 `model_answer_correct` 在完整 archive 上计算，不进入主要 accuracy。`archive_answer_accuracy` 直接固定为 1。

`hot_ids_before` 实际只含**当前问题的 gold evidence**。旧 retention 将它与全部未来 evidence 取交集，遗漏了仍在缓存、但当前问题未使用的未来有用块。`retained_useless_blocks` 同样只看 gold 子集，因此旧表中的零值不能证明没有 useless cache occupancy。`eviction_regret=1-retention` 不是独立测得的逐次驱逐后悔值。

本审计保留旧数值，另从 query trace 的完整 `hot_ids` 重算真实集合保留率；所有 accuracy 均更名为 **q2/q3 指定证据全部可用 proxy**。没有把该 proxy 重新包装成模型答题表现。

### 5. 分歧门槛通过，但不是已验证的稀缺容量排序对照

q1 最多四个候选，而 admission slots 为 4 或 8；108/108 单元中候选不多于 admission slots。故报告的 Top-K Jaccard=1 是把全部候选都选进去的结果。

实际 admission 又过滤 `score > 0`：RMM-like 的手工权重全为正，全部候选可入；Task Utility 会拒绝没有独占答案词的块。再写入的新块分数是零。主要区别因此是**零分拒收与正分保留**，没有在足够多的高分候选争夺不足槽位时验证排序质量。

共享 capacity 和候选机会确实实现了，普通 baseline 也不再是零分；但 `Recency` 没把 write 更新成 last-access，新块的分数为零，仍不能直接视为标准 LRU 基线。

### 6. Gate 与相关系数的报告存在额外错误

旧 gate 使用 q2/q3 的 evidence 命中子集并合并两个时刻，得到 24/108。按每个时刻完整 cache 判定，实际有 **60/108（55.6%）** 单元分歧，gate 仍达到 20%，但“真实分歧子集”应为 60。

旧相关系数函数将常量向量的相关性写成 1；本审计标记为未定义。只有 48/108 单元可定义 Pearson/Spearman，均值分别为 0.074489 / 0.000000。另有 48 单元存在严格排名反转；旧代码只检查按 ID 排序后的一个反转方向，漏计为 12。这里只按已存在分数重算，没有重跑 scorer。

## 重算结果及正确解释

下表的“完整缓存保留率”使用 q2/q3 query trace 中实际 hot set 与 future evidence union 的交集；“答题 proxy”仍使用原来指定 evidence IDs 全部可用的规则。

| 子集 | 单元数 | RMM-like 完整缓存保留率 | Task 完整缓存保留率 | RMM-like 答题 proxy | Task 答题 proxy | Task 胜 / 负 / 平 |
|---|---:|---:|---:|---:|---:|---|
| 全部 | 108 | 0.685185 | 0.500000 | 0.611111 | 0.388889 | 0 / 24 / 84 |
| 旧 gate 子集 | 24 | 1.000000 | 0.166667 | 1.000000 | 0.000000 | 0 / 24 / 0 |
| 完整 cache 真正分歧子集 | 60 | 0.933333 | 0.600000 | 0.800000 | 0.400000 | 0 / 24 / 36 |

本表三种指标（旧 retention、完整-cache retention、答题 proxy）的配对胜负一致。旧报告的 0/24 数字可以复算，但它遗漏了 36 个存在缓存分歧且结果相同的单元。正确描述是 **60 个分歧单元里 0 胜、24 负、36 平**，不应描述成 24 个独立随机情形都证明该原理失败。

没有计算显著性或置信区间，因为这些 seed 不是独立数据重复。表中差值只是当前模拟器规则的描述性结果。

## 三个失败场景究竟说明什么

- **cross_event**：B 本身也含 ALPHA，删 A 不降低 q1 词面分数；q2 却按 A 和 C 的 ID 是否存在计分。这里混合了“信息在别处仍存在”和“必须保留指定来源 ID”两种标准。不能归咎于真实 task-level utility。
- **redundant_evidence**：删任何一份副本，另一份都可提供同样答案，单块 leave-one-out 均为零；同时删两份则丢答案。这说明单块边际贡献不等于一个集合的总价值，不能推断所有 counterfactual 或集合保留方法都无效。q1 utility=0 也不等于该块未来无用。
- **obsolete_information**：q1 的正确旧值与未来应使用的新值不同，说明当前贡献不保证未来贡献；这个场景里两种 policy 并未产生结果分歧，因此它不是“Task 比 RMM 差”的直接证据。

`q1 有用 ≠ 必然未来有用` 是合理边界；`q1 有用无法提供任何未来预测信号` 则没有被证明。在重复任务里过去使用仍可能与未来相关。完全相同的过去可以接不同未来，任何只看过去的策略都无法保证对任意未来最优；这也不要求本项目转向预测器开发。

## 为什么仍然停止

继续完整架构需要比当前更强的正证据。修复 scorer、RMM、seed、容量竞争和评分的研究契约将构成新的实验证据链，不是对已有结论的微小补充。用户已经限定一次修正，本次不再补救。

**终止是资源配置与研究立项决定；不是宣布该领域不再有价值。**完整 RCHAM 没有被实现或测试，不能说其端到端性能已失败；也没有可靠证据证明值得继续实现它。

此前将“7 tests passed”和“可重算的 negative toy result”解读成研究验证完成，属于报告过度。测试能证明代码按某些定义运行，不能证明这些定义测到了用户所问的问题。

## 收尾、复用与暂存问题

- [Rejected hypotheses](../closeout/rejected_hypotheses.md)：记录每项主张的动机、证据、停止理由与禁止外推。
- [Reusable infrastructure](../closeout/reusable_infrastructure.md)：区分可直接复用的档案/工具与需要重新验证的实验语义。
- [Open questions](../closeout/open_questions.md)：仅存档，不自动转成 RCHAM Phase 2，也不声称新颖。
- [原始证据](../closeout/evidence/manifest.json)：原文件不删除，压缩副本可纳入 Git，使结论不只依赖对话粘贴。

任何以后重启必须是明确立项的新项目，有新的理论或公开 failure evidence、经核实的最近工作以及独立可靠的测量契约。本轮不提出可直接投入的新 controller 或新的 Attention 架构。

## Git 核验

本地 Phase 1R commit 完整存在。首次在线只读核验时，origin/main 为 `b4548d418e0fba3c17db58bd8a822701abccfb80`，比 `c9b8b19` 落后五个 commit。因而此前的本地 commit 记录不能当作远端已发布证明。最终同步结果另记于提交交付说明；远端状态以实际查询为准。

结项过程中，远端新增 `cede1bf5d29fc0524ac0ec82ebfb34fd4d1918f8`，包含一份基于对话报告、尚未看到本地源码的结项说明。本轮合并保留该 commit 和 `rcham_closeout_2026-09-15.md` 原文，并在入口与日志中标明本次直接证据复核的更正。没有用 force push 替换任何远端历史。

**STOP。未运行新实验，未修改实验实现，未启动 GPU、模型下载或收费 API。**
