# RCHAM：检索反馈式层级注意力记忆

> **状态：研究方向已关闭（2026-09-15）**
>
> RCHAM 不再作为新的端到端 Attention / KV-memory 架构继续推进。Architecture-wide prior-art audit 表明大多数组件已有成熟或高度接近的工作；剩余核心假设——“q1 中观察到的 task-level post-use utility 能更好预测 q2/q3 前应保留的历史 KV”——在 Phase 1R 的可区分性修正实验中得到 **NO-GO**。
>
> 详细收尾见 [`reports/rcham_closeout_2026-09-15.md`](reports/rcham_closeout_2026-09-15.md)。除非出现新的、直接面向 future reuse 的可观测信号并重新完成 prior-art audit，否则不得把该方向作为 Phase 2 继续扩展。

## 最终研究结论

本项目最终确认的核心边界是：

```text
Past utility != future usefulness
```

在 future query 未知时：

- 最近访问、访问频率和传统 Attention 不能可靠确定未来语义重要性；
- 即使一段历史在 q1 中确实帮助了当前答案，也不能推出它在 q2/q3 中仍值得占用稀缺 KV 资源；
- 传统 Cache 的时间局部性（Temporal Locality）和空间局部性（Spatial Locality）在该问题中可能存在，但不足以解决“未知未来语义查询下的信息重要性预测”；
- 因此不能继续用 hierarchy、decay、promotion/demotion、GPU/CPU/SSD tiering 去补救一个未经支持的预测信号。

这不是“层级记忆永远不可行”的证明，而是一个项目级停止结论：**现有证据不足以支持继续投入完整实现。**

## 研究路径

项目经历了以下阶段：

1. **Phase -1 / Pilot**：自然语言压缩和层级路由预实验；发现层级结构本身不自动提高 recall。
2. **Phase 0 / 0.5**：文献、官方代码和论文真实性审计；将宽泛 RCHAM novelty 缩小到 post-use lifecycle 接口。
3. **Architecture-wide Prior-Art Audit**：确认 compression、hierarchy、fallback、utility、tiering、promotion/demotion 等大组件均已有强先例。
4. **Lifecycle Gap Falsification**：把候选问题进一步缩到“q1 后 task attribution 是否能改善 future internal-KV lifecycle”。
5. **Phase 1 Minimal Principle Test**：初始结果表面 NO-GO，随后审计发现 RMM-like 与 Task Utility 实际做出完全相同的 eviction 决策，因此判定为 **NON-IDENTIFIABLE**。
6. **Phase 1R Discriminative Principle Test**：修正 benchmark，使两种策略产生真实 retained-set / eviction disagreement；最终 Task Utility 在分歧单元中明显落后于 RMM-like，正式得到 **NO-GO**。

## Phase 1R 最终结果

在 108 个 episode-budget 单元中：

- score vectors different：108/108
- retained-set disagreement：24/108 = 22.2%
- eviction decision disagreement：60/108
- 平均 Pearson：0.2596
- 平均 Spearman：0.2000

在真正发生 retained-set 分歧的 24 个单元中：

| Policy | Future retention | q2 accuracy | q3 accuracy |
|---|---:|---:|---:|
| RMM-like | **0.833** | **1.000** | **1.000** |
| Task Utility | 0.083 | 0.000 | 0.000 |

Task Utility conditional win rate：

- future-retention：0/24
- q2/q3 accuracy：0/24

全部 108 个单元：

| Policy | Future retention | q2 accuracy | q3 accuracy |
|---|---:|---:|---:|
| RMM-like | **0.556** | **0.556** | **0.667** |
| Task Utility | 0.389 | 0.333 | 0.444 |

因此，继续实现完整 RCHAM 不再合理。

## 保留的资产

项目虽然停止，但以下资产应保留：

- `literature/`：文献矩阵、证据账本、复现警告；
- `design/`：架构历史、创新边界和失败假设；
- `experiments/`：等预算 policy harness 和 benchmark 代码；
- `results/`：raw traces、metrics、manifest；
- `reports/`：所有阶段报告，包括失败结果；
- `RESEARCH_LOG.md`：完整研究过程。

最重要的可复用方法论是：

> **在比较两个机制的下游效果前，先证明 benchmark 能让它们真正做出不同决策。**

## 不应继续做的事情

- 不再设计新的 RCHAM controller；
- 不训练 Transformer 来“再试一次”；
- 不增加 hierarchy / decay / hardware tier 来挽救当前假设；
- 不把 synthetic NO-GO 外推成“所有真实 LLM 上 task utility 永远无效”；
- 不把未来新想法直接称为 RCHAM Phase 2。

若以后重新研究 long-context / KV memory，应从新的公开 failure mode 和新的 prior-art audit 开始，作为新项目处理。
