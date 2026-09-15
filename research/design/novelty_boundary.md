# RCHAM 创新边界（Phase 0.5 冻结版）

> **2026-09-15：DORMANT / ARCHIVED。**下列创新边界与 gap 判断为历史记录，未建立足以继续实现的贡献证据。项目决策见 [当前状态](../PROJECT_STATUS.md)，实验解释见 [结项复核](../reports/research_closeout.md)；未确认覆盖不等于证明没人做过。

## 先把两个问题分开

### First-time unexpected query

历史 `M` 从未被证明重要，第一次被未来 query `q1` 使用。此时 promotion 还没有发生，RCHAM 不能提前帮助 `q1`。这一阶段依赖：

```text
compressed routing representation + cold/raw fallback
```

它解决的是“第一次能不能找到”。Landmark Attention、H²MT、HeteroCache 已经分别覆盖 landmark/raw block、coarse-to-fine hierarchy、drift-triggered tier retrieval；因此 first-time retrieval 不是 RCHAM 的新颖点。

### Recurrent / related future query

`q1` 读回 `M` 后，系统评估证据是否真的改变了答案或降低了 loss。如果 utility 为正，才允许：

```text
M: compressed/cold → higher precision/hotter tier/more accessible
```

这只能改善后续 `q2/q3/...` 在 memory pressure 下的存活、召回成本和回答质量。它不是“解决 future-query-unknown”，而是“在价值已经暴露后重新分配资源”。

## 已知不能单独主张的新颖点

局部/sliding-window attention、压缩 memory、summary/memory tokens、层级表示、粗到细路由、landmark/raw-block fallback、KV 分层、访问次数强化、时间衰减、agent memory consolidation、reversible compression 和 query-agnostic KV eviction 都已有公开工作。

## 最近邻和影响

1. **Landmark Attention**：内部 query → landmark → raw block；官方代码公开。RCHAM 必须把 first-time cold fallback 作为基线，而不是贡献。
2. **H²MT**：arXiv preprint 已有 offline semantic hierarchy、bottom-up embeddings 和 coarse-to-fine routing；没有确认的 version-of-record 或官方代码。本项目不能把层级树本身写成创新。
3. **HeteroCache**：ACL 2026 Long Paper 和官方代码已覆盖 heterogeneous KV budget、hierarchical storage、attention drift 监测和 asynchronous retrieval。未从正式描述确认 post-use utility promotion/demotion；这是需要精读/复现确认的最近内部系统。
4. **R³Mem**：Findings ACL 2025 已覆盖 reversible hierarchical retention/reconstruction，但属于外部 memory network，不能直接等同内部 KV 生命周期。
5. **KVzip**：NeurIPS 2025 Oral 已覆盖 query-agnostic reconstruction-based importance；它是在淘汰前估计重要性，不是 `q1` 使用后的 counterfactual utility。
6. **MemoryBank / RecMem / SF-AMS**：外部 agent memory 已覆盖时间遗忘、recurrence consolidation 和 utility-driven survival。它们压缩了“promotion + decay”作为一般记忆思想的创新空间，但没有证明内部 Transformer/KV 闭环。

## Phase 0.5 后的最小 novelty statement

> 在固定 memory/retrieval budget 和未来 query 未知的时间序列中，第一次需求由 cold/raw fallback 处理；在该次读取之后，用可记录的 post-use utility 更新记忆等级，并在真实 memory pressure 下比较后续 query 的 retention、evidence recall、answer accuracy 和访问成本。研究对象是内部 KV/attention 生命周期中的反馈式资源再分配，而不是压缩、层级或召回本身。

更严格的机制假设是：

> 在相同预算下，`post-use utility-conditioned promotion` 是否比 static、recency、retrieval-count 和 cold-fallback-only 更能提升后续重复/相关 query 的 future-useful retention，同时不造成过高 churn？

## 当前闭环判定

在已锁定的 primary sources 中，没有确认一个完整实现同时具备：

```text
first cold retrieval
→ post-use utility
→ promote precision/tier
→ later reuse
→ decay/demotion
```

这是“未确认完整重合”，不是“没人做过”的证明。若后续精读 HeteroCache、SF-AMS 或新的 KV policy 发现完整闭环，应立刻收窄或放弃该 novelty statement。

## No-go 条件

- 如果内部 Transformer 方法已经完整实现上述闭环，停止使用“新架构”措辞，转为复现或差异化分析。
- 如果 utility 只能利用未来问题/gold answer，不能在读取后观测，研究降级为 oracle 上界分析。
- 如果 utility promotion 只提升 `q1`（第一次需求）而没有后续 query，不能声称 promotion 有价值。
- 如果相同预算下没有稳定后续 retention 优势，不能用更大模型、更高存储或更宽候选集掩盖结论。

## Phase 0-B 审计后的必要收窄

EVICPRESS 已经覆盖 context-level 的在线质量复核、压缩/驱逐/设备重分配和真实 I/O；AdaptCache、IMPRESS、Strata 已覆盖预测或历史效用的系统级 tier。因而不能再把“观察后资源重分配”写成未解决问题。

当前最多只能保留下面的窄问题：

> **当 q1 通过 cold/raw fallback 读取历史后，能否把 q1 的质量变化归因到 exact internal KV token/block/evidence identity，并在相同 quality/bytes/I/O budget 下，于 q2/q3 前改变该 identity 的 precision 或 hardware residency，再对长期不用的 identity 执行可验证 demotion？**

这条陈述仍有较高 engineering-integration risk。context-level quality drift、attention drift、retrieval count 和离线 future-utility prediction 都不能直接证明 exact attribution。RMM 的自然文本/独立 streaming 对照还提示：即使 post-use signal 存在，也可能退化为普通 attention，不能预设部署收益。

因此本文件的状态从“provisional research gap”改为 **narrow, unconfirmed interface gap**：只有在下一阶段先确认这一具体 failure mode，并用统一生命周期协议测出独立收益，才有资格讨论算法或论文贡献。
