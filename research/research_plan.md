# RCHAM 研究计划 v0.2

日期：2026-09-14

本计划取代“先证明压缩和召回是否可能”的旧主线。那些能力已有大量工作证明；本项目现在研究 **Retrieval-Conditioned Hierarchical Attention Memory（RCHAM，检索反馈式层级注意力记忆）**：写入时不知道未来问题，记忆可以先被压缩或降级；当一次召回被证明对回答有用时，再提高该记忆的保留精度和可访问性；长期不用则降级。

## 研究边界

压缩、局部 attention、层级表示、粗到细检索、原文回退、衰减、按访问次数加权和 KV 分层都不是本项目单独的创新声明。Phase 0 先用主论文和代码确认最近邻工作，尤其核对 Landmark Attention、H²MT、HeteroCache、R³Mem 和 RecMem 是否已经覆盖目标机制的组合。

当前机器没有 CUDA/PyTorch 和这些方法的权重，因此 Phase 0 只做证据审计和可证伪实验协议；不运行官方 GPU 方法，不下载大模型，不修改 Transformer。

## 核心问题与假设

**Q1：**在未来 query 未知时，按“后来被证明有用”来提升记忆等级，是否比静态、最近性或单纯召回次数更能保留未来重要事实？

**Q2：**多分辨率表示加原文指针，是否能减少不可逆遗忘，而不把所有历史重新放回 attention？

**Q3：**促升与衰减能否在固定内存预算下稳定运行，避免正反馈、记忆抖动和热点垄断？

- H1：在相同存储和检索预算下，utility-conditioned promotion 的 future-useful retention 高于 static、recency 和 retrieval-count。
- H2：高层 routing representation 加 child/raw pointer 能降低压缩错误造成的不可逆遗忘。
- H3：utility promotion + decay + cooldown 能保持稳定 tier occupancy 和较低 churn；没有衰减时会出现正反馈或容量挤占。
- H4：把控制器接入真实 Transformer/KV 后，质量—内存—延迟的综合曲线可能改善，但 Phase 0/1 不预设它成立。

## 阶段

### Phase 0：文献、代码和创新边界审计（当前阶段）

输出见 `research/literature/`、`research/design/` 和 `research/experiments/phase1_protocol.md`。每项结论都要区分“论文报告”“代码存在”“独立复现”“本机实测”。若发现已有工作完整覆盖 utility feedback + hierarchical internal KV lifecycle，则停止原创机制路线，改为复现、分析或明确差异。

### Phase 1：机制控制器模拟（下一阶段，需 Phase 0 闸门通过）

只使用冻结的 embedding/hidden representation 和独立 memory controller，不训练大模型。写入路径绝不能看到未来 query；读取路径记录候选、是否使用证据及 counterfactual utility，再执行 promote/demote。比较 static、recency、retrieval-count、utility、utility+decay 和 oracle 六组。

### Phase 2：小型真实模型验证

仅在 Phase 1 产生稳定、预算匹配的 utility 优势后，接入约 50M–300M decoder-only Transformer，先做局部 attention + 分层 KV 控制器，记录 loss、长上下文 QA、KV bytes、FLOPs 和 latency。不得把 controller simulation 的结果写成 Transformer 结果。

### Phase 3：正式架构和 benchmark

只有在 Phase 2 通过后，才讨论训练目标、硬件 kernel、LongBench/RULER/BABILong、消融和论文。完整计划不承诺 O(n)；复杂度必须按实际路由、读取和层级维护成本重新推导。

## 历史结果的定位

旧的自然语言压缩 Pilot 保留为 Phase -1/历史证据，报告在 `research/reports/phase1_pilot_report.md`。它说明摘要可能具备路由价值，但不能证明 RCHAM 的 utility feedback、促升、衰减或内部 attention 集成。

## 研究纪律和停止条件

固定 seed、模型/数据/依赖版本、prompt、硬件和原始输出；统计从 raw traces 自动重算。未来 query 不得泄漏到写入或压缩过程。若出现高重合论文、utility 信号实际不可观测、控制成本超过收益、促升导致严重 churn，或结果依赖不公平预算，必须报告失败并停止扩展。
