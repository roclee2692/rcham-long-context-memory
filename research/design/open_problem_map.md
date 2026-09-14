# Open Problem Map: Architecture-wide Prior-Art Audit

日期：2026-09-15
用途：记录现有候选架构哪些部分应视为基线、哪些部分拥挤、哪些接口仍可被严格证伪。
本文件不是 controller 设计，也不是 novelty 宣称。

## 一、已基本解决的组件

这些方向可以直接作为基线或系统部件，不能单独作为 RCHAM 的新颖点：

- sliding/local/sparse attention 的基本模式（Longformer、BigBird、StreamingLLM、NSA）；
- dense history 的 KV/context compression（Compressive Transformer、AutoCompressor、ICAE、Activation Beacon）；
- raw block/KV fallback（Landmark Attention、HeteroCache）；
- past attention、recency、frequency、heavy-hitter eviction（H²O、StreamingLLM、SnapKV 等）；
- LRU/LFU/ARC、working-set、reuse-distance 和 Belady oracle 等传统 replacement 基线；
- GPU/CPU/NVMe paging、offload、prefetch 和分块管理（FlexGen、ZeRO-Inference、PagedAttention/vLLM）；
- 基础长上下文和长记忆评测（LongBench、RULER、LongMemEval、BABILong、SCBench）。

“已解决”只表示机制已经有成熟证据，不表示所有 workload 都无失败。

## 二、活跃且拥挤的方向

以下方向仍在快速发展，但已有很多互相接近的方法：

- query-agnostic KV eviction/compression；
- landmark、semantic hierarchy 和 coarse-to-fine routing；
- head/layer/episode-specific dynamic budget；
- attention drift、delayed proxy 和 online compaction；
- predicted future utility / reuse probability；
- external semantic/episodic memory、recurrence consolidation、decay；
- heterogeneous GPU/CPU/SSD KV storage。

如果后续工作只替换一个打分函数，必须证明它在相同 memory、retrieval、I/O 和 quality budget 下改变了失败模式，否则更像 engineering tuning。

## 三、接口图

```text
write M
  │  future query/answer hidden
  ▼
query-agnostic compression + routing key + child/raw pointer
  │
  ├── q1 arrives: cold/raw fallback, route miss cost, evidence recall
  │
  ▼
observe post-use evidence (or a deployable proxy)
  │
  ├── demonstrated utility / predicted reuse / attention proxy
  ▼
admission + precision + tier residency + pointer/version update
  │
  ▼
memory pressure and I/O scheduling
  │
  ├── q2/q3 related reuse: retention, evidence recall, answer quality
  └── no reuse: demotion, decay, regret, churn
```

## 四、六个关键接口的当前状态

### 1. 时间和信息边界

**已有覆盖：** Landmark、KVzip、HeteroCache 在 q1 到达时可以路由或取回；RMM 在固定 lag 后观察近未来使用；KVP 在离线训练中学习 future utility。

**缺口：** 没有统一协议把“写入时不知道 q1”“q1 的 cold miss”“q1 之后才出现 utility”“q2/q3 的重复使用”“长期不用后的 decay”放进同一内部 KV 时间线。任何后续实验必须保留这条因果顺序。

### 2. 表示、指针和版本

**已有覆盖：** Landmark 提供代表到 raw block；H²MT 提供树上的 coarse-to-fine route；R³Mem/KVzip 提供重建或回取思路。

**缺口：** content representation、routing representation、child pointer、raw/KV pointer、位置编码、层/头版本和失效处理没有共享契约。高层命中不等于底层证据仍能正确拼回当前 attention。

### 3. Utility 的可观测性

**已有覆盖：** H²O/attention、retrieval count、KVP/reuse prediction、RMM/post-use correctness、传统 cache 的 trace prediction。

**缺口：** 这些信号测量的对象不同。attention 可能是代理，retrieval 不等于 useful，gold counterfactual 不能在部署时直接使用。要先区分 oracle upper bound 与 deployable proxy，再谈 promotion。

### 4. 生命周期和资源分配

**已有覆盖：** ARC 解决 recency/frequency replacement；MemoryBank/RecMem 解决外部 memory 的强化和衰减；HeteroCache/EpiCache 解决部分异构预算。

**缺口：** admission、promotion、demotion、precision 和 GPU/CPU/SSD residency 还没有在同一 objective 下联合计价。特别是“提高精度”与“搬回 HBM”并不等价，且可能有不同 I/O 和计算成本。

### 5. 真实系统成本

**已有覆盖：** SCBench 将 generation、compression、retrieval、loading 分开；FlexGen、PagedAttention、Tutti 等提供硬件路径。

**缺口：** 缺少跨方法、跨硬件可复算的 cost model，把 index probes、decompression、kernel launch、PCIe/NVMe bytes、queueing 和重算全部纳入。理论复杂度或 cache bytes 不能代替这个模型。

### 6. 统一生命周期 benchmark

**已有覆盖：** LongBench/RULER 测长上下文能力，LongMemEval 测多种长期记忆能力，SCBench 测 cache 生命周期，BABILong 测分布式事实。

**缺口：** 目前没有一个标准协议同时固定：未知 q1、第一次 cold fallback、post-use utility、真实 pressure、相关但不同的 q2/q3、tier/I/O、evidence recall 和最终回答。这个 benchmark 接口比再造一个摘要器更值得先审计。

## 五、公开 failure regimes 映射

| 风险 | 已有证据 | 不能忽略的含义 |
|---|---|---|
| 首次稀有事实被压掉 | Landmark/Practical Compaction 的 fallback 设定 | promotion 不能帮助 q1；必须保留 cold/raw path。 |
| 重复压缩误差累积 | Infini-Attention 独立复现 | 一次成功不等于多次压缩稳定。 |
| utility 退化为 attention | RMM 在自然文本/第三方 KVPress 上的报告 | oracle post-use 可能没有部署优势。 |
| 立即 compaction 伤害下一步 | Practical Online KV Cache Compaction | 更新时机本身要作为变量。 |
| 过去访问次数误导 | H²O、传统频率策略的已知局限 | retrieved != useful；要加入 useless distractor。 |
| route/stale pointer miss | Landmark/H²MT/HeteroCache 设计边界 | 层级结构不自动提高 recall。 |
| I/O 吃掉收益 | SCBench、FlexGen、HeteroCache | 必须报告 bytes/probes/cold reads/queueing。 |
| 外部 memory 结论错投到内部 KV | RecMem/MemoryBank/R³Mem 与内部 KV 的边界 | 外部文本记忆准确不等于 per-layer KV 正确。 |

## 六、什么才会构成真实的后续贡献

以下只是判定条件，不是新 controller 方案：

1. 明确一个此前没有统一的**因果时间契约**，并在 q1 之前不泄漏 future query/answer；
2. 把 route representation、raw evidence、pointer/version 和 tier residency 的状态转换写成可检查的不变量；
3. 用相同 memory、quality 和 I/O 预算，证明 post-use signal 对 q2/q3 有独立收益，而不是把 q1 或更多 raw storage 的收益误算成 promotion；
4. 同时报告 oracle utility 和部署可获得的 proxy，说明 oracle 与实际系统之间的差距；
5. 在生命周期 benchmark 上包含 failure regimes，并可由 raw trace 自动复算，而不是只报告平均 compression ratio；
6. 与 H²O、ARC、KVzip、Landmark、HeteroCache、RMM/KVP 这类最强近邻在同一硬件和 workload 上比较。

如果这些条件不满足，结果应被描述为复现、系统整合或工程优化，而不是新的注意力架构。

## 七、暂不做的事情

- 不继续设计 RCHAM controller 的新公式；
- 不训练 Transformer，不下载大型 checkpoint，不启动 GPU；
- 不把“没有在本轮确认”写成“全世界没有”；
- 不把外部 agent memory、传统 cache 和内部 KV 的结果混为一类；
- 不把论文报告的 compression ratio、单次 latency 或单一 NIAH 分数相加为端到端结论。

本图的结论是：宽泛的 RCHAM 架构已经高度由既有组件覆盖；若未来继续，只应围绕上述接口、证据链和失败区间提出窄而可证伪的问题。
