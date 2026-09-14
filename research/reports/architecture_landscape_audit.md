# Architecture-wide Prior-Art Audit

审计日期：2026-09-15
范围：RCHAM 候选架构的 20 个环节；内部 Transformer/KV、外部 agent memory、传统缓存系统和评测基准。
状态：**Phase 0 证据审计；不启动模型、GPU 或 controller 实验。**

## 结论先行

候选架构不是一块尚未有人做过的“新大陆”。局部/稀疏 attention、历史 KV 压缩、query-agnostic eviction、landmark/raw fallback、层级路由、动态 KV 分层、外部记忆巩固和传统 cache replacement 都已有正式工作或成熟系统。因而不能把“把这些模块放在一张图里”直接写成新 Transformer 架构。

仍然没有在本轮 primary-source 核对中确认一个完整、可复现的**内部 Transformer/KV 闭环**同时做到：

```text
写入时不知道未来 query
→ 第一次 q1 依靠压缩路由和 cold/raw fallback
→ 观察 q1 之后的实际 utility
→ 在相同预算下提升 M 的精度/层级/硬件 residency
→ memory pressure 下服务 q2/q3
→ 长期不用时衰减或降级
```

这不是“证明没人做过”。它只是当前证据下一个需要继续逐篇精读、并且能被证伪的接口问题。最接近的工作分别覆盖这个链条的不同边：Landmark Attention 覆盖 landmark 到 raw block，H²MT 覆盖层级 coarse-to-fine，HeteroCache 覆盖 drift-triggered heterogeneous KV，KVzip 覆盖 query-agnostic eviction，RMM 覆盖延迟观察 post-use evidence，KVP 覆盖预测 future utility，RecMem/MemoryBank/SF-AMS 覆盖外部记忆的 recurrence、decay 和 utility survival。

## 证据规则

- 正式会议/期刊页面和 DOI 是 version-of-record；arXiv 只作为版本入口或最新 preprint。
- `paper reports`、`official code exists`、`independent reproduction` 分开记录；有代码不等于结果已复现。
- 没有把第三方实现写成作者官方代码；没有从摘要推断完整机制。
- 2026 年 preprint 的结论按 ACTIVE/UNKNOWN 处理，除非已核对正式出版版本。
- 运行速度只在相同硬件、kernel、batch、I/O 和 workload 下比较；“压缩率”不等于“端到端延迟下降”。

完整逐组件账本见 [`architecture_landscape_matrix.csv`](../literature/architecture_landscape_matrix.csv)。重点版本、代码和复现警告见 [`paper_evidence_ledger.md`](../literature/paper_evidence_ledger.md) 与 [`reproduction_warnings.md`](../literature/reproduction_warnings.md)。

## 20 个组件的状态

| # | 组件 | 成熟度 | 最接近证据 | 当前边界 |
|---:|---|---|---|---|
| 1 | Local / Sliding / Sparse Attention | MATURE | [Longformer](https://arxiv.org/abs/2004.05150)、[BigBird](https://proceedings.neurips.cc/paper/2020/hash/c8512d142a2d849725f31a9a7a361ab9-Abstract.html)、[NSA ACL 2025](https://aclanthology.org/2025.acl-long.1126/) | 模式和硬件优化已有；跨窗口漏证据与生命周期接口仍未统一。 |
| 2 | Historical KV / context compression | MATURE | [Compressive Transformer](https://openreview.net/attachment?id=SylKikSYDH&name=original_pdf)、[Activation Beacon](https://proceedings.iclr.cc/paper_files/paper/2025/hash/fc797c61eb18f7b3ce9a74af0ef0d876-Abstract-Conference.html)、[KVzip](https://proceedings.neurips.cc/paper_files/paper/2025/hash/f4eaa4b8f2d08edb3f0af990d56134ea-Abstract-Conference.html) | “能压”已成立；压缩后稀有细节、重复压缩和精确回溯仍有失败。 |
| 3 | Query-agnostic compression | ACTIVE | [KVzip](https://arxiv.org/abs/2505.23416)、[Activation Beacon](https://arxiv.org/abs/2401.03462)、[Gist](https://proceedings.neurips.cc/paper_files/paper/2023/hash/3d77c6dcc7f143aa2154e7f4d5e22d68-Abstract.html) | 写入时不知道未来 query 已被明确研究；未来罕见事实和指令泄漏是风险。 |
| 4 | Multi-resolution / hierarchical representation | ACTIVE | [HMT](https://aclanthology.org/2025.naacl-long.410/)、[H²MT](https://arxiv.org/abs/2605.24930)、[NSA](https://aclanthology.org/2025.acl-long.1126/) | 多层表示和粗到细已出现；节点版本、child pointer、跨层 promotion 没有共同协议。 |
| 5 | Routing / coarse-to-fine retrieval | ACTIVE | [Landmark Attention](https://proceedings.neurips.cc/paper_files/paper/2023/hash/ab05dc8bf36a9f66edbff6992ec86f56-Abstract-Conference.html)、[H²MT](https://arxiv.org/abs/2605.24930) | Query 到达后路由已可行；miss 的质量/成本和 stale index 仍未标准化。 |
| 6 | Raw evidence / KV fallback | MATURE | [Landmark code](https://github.com/epfml/landmark-attention)、[HeteroCache](https://arxiv.org/abs/2601.13684) | raw/host block 回取是已有设计；真实 I/O、位置和 layer 语义成本需单独测。 |
| 7 | Reversible compression | ACTIVE | [R³Mem](https://aclanthology.org/2025.findings-acl.235/)、[KVzip](https://proceedings.neurips.cc/paper_files/paper/2025/hash/f4eaa4b8f2d08edb3f0af990d56134ea-Abstract-Conference.html) | “可重建/可回溯”已有；exact reversible 与 useful reconstructability 还没有统一指标。 |
| 8 | Past-attention / recency / frequency importance | MATURE | [H²O](https://proceedings.neurips.cc/paper_files/paper/2023/hash/6ceefa7b15572587b78ecfcebb2827f8-Abstract-Conference.html)、[StreamingLLM](https://hanlab.mit.edu/projects/streamingllm) | 访问历史代理已很成熟；它不等于未来语义 utility。 |
| 9 | Demonstrated post-use utility | ACTIVE | [RMM / Eviction as Estimation](https://arxiv.org/abs/2607.24667) | 延迟观察近未来正确性已有直接工作；自然文本中 utility 可能退化成 attention，且外部复现结果不强。 |
| 10 | Predicted future utility / reuse probability | ACTIVE | [KVP](https://arxiv.org/abs/2602.10238)、[learning-augmented caching](https://proceedings.mlr.press/v139/chledowski21a.html) | 训练时可见 future trace，部署时只能预测；分布漂移和 predictor error 未解决。 |
| 11 | Semantic / topic / episodic state | ACTIVE | [EpiCache](https://arxiv.org/abs/2509.17396)、[RecMem](https://aclanthology.org/2026.findings-acl.1619/)、[MemoryBank](https://ojs.aaai.org/index.php/AAAI/article/view/29946) | 外部/episode state 很活跃；如何精确映射回每层 KV 仍不清楚。 |
| 12 | Promotion / demotion / decay | ACTIVE | [MemoryBank](https://ojs.aaai.org/index.php/AAAI/article/view/29946)、[RecMem](https://aclanthology.org/2026.findings-acl.1619/)、[ARC](https://www.usenix.org/conference/fast-03/presentation/arc-self-tuning-low-overhead-replacement-cache) | 一般生命周期不是新发现；内部 KV 中 utility、admission、tier 和 decay 的闭环仍未统一。 |
| 13 | Dynamic cache tier allocation | ACTIVE | [HeteroCache](https://arxiv.org/abs/2601.13684)、[EpiCache](https://arxiv.org/abs/2509.17396) | 头/层/episode 级动态预算已有；质量、bytes、miss cost 和 I/O 的共同目标未统一。 |
| 14 | GPU / CPU / SSD hot-cold storage | MATURE | [FlexGen](https://arxiv.org/abs/2303.06865)、[PagedAttention](https://arxiv.org/abs/2309.06180)、[ZeRO-Inference](https://www.deepspeed.ai/2022/09/09/zero-inference.html) | 硬件层级、paging、offload、prefetch 是成熟系统问题；语义 utility 到 residency 的映射未解决。 |
| 15 | Attention-drift-triggered retrieval | ACTIVE | [HeteroCache](https://arxiv.org/abs/2601.13684)、[Practical Online KV Cache Compaction](https://arxiv.org/abs/2608.00902) | drift/proxy trigger 已有；trigger 校准和监控成本没有统一协议。 |
| 16 | First-time unexpected query handling | OPEN | [Landmark](https://proceedings.neurips.cc/paper_files/paper/2023/hash/ab05dc8bf36a9f66edbff6992ec86f56-Abstract-Conference.html)、[Practical Compaction](https://arxiv.org/abs/2608.00902) | 只能靠 compressed route + cold/raw fallback；有限预算下无法保证任意首次稀有事实，miss 成本仍是开放问题。 |
| 17 | Recurrent-use memory consolidation | ACTIVE | [RecMem](https://aclanthology.org/2026.findings-acl.1619/)、[MemoryBank](https://ojs.aaai.org/index.php/AAAI/article/view/29946)、[R³Mem](https://aclanthology.org/2025.findings-acl.235/) | recurrence/semantic consolidation 已在外部 memory 形成路线；内部 per-layer KV 的 bounded-cost 版本未验证。 |
| 18 | Controller overhead / I/O / real latency | ACTIVE | [SCBench](https://openreview.net/pdf/264842d66ae06cc7f27d1881a403f6d8816aca4d.pdf)、[HeteroCache](https://arxiv.org/abs/2601.13684) | 必须计入 generation、compression、routing、loading、PCIe/NVMe 和 queueing；很多 speedup 不是跨硬件结论。 |
| 19 | End-to-end Transformer integration | ACTIVE | [NSA](https://aclanthology.org/2025.acl-long.1126/)、[HMT](https://aclanthology.org/2025.naacl-long.410/)、[Activation Beacon](https://arxiv.org/abs/2401.03462)、[Infini-Attention](https://arxiv.org/abs/2404.07143) | 各自能接入 Transformer，但没有确认共同的 utility→tier→fallback→decay 内部闭环。 |
| 20 | Evaluation benchmarks and failure regimes | MATURE | [LongBench](https://aclanthology.org/2024.acl-long.172/)、[RULER](https://openreview.net/pdf?id=kIoBbc76Sy)、[LongMemEval](https://openreview.net/pdf?id=pZiyCaVuti)、[SCBench](https://openreview.net/pdf/264842d66ae06cc7f27d1881a403f6d8816aca4d.pdf) | 基准已经很丰富；仍缺少同时控制 q1、q2/q3、pressure、tier/I/O 和证据正确性的统一 protocol。 |

## 证据按研究层次归类

### 已经有很强证据的内部 attention / KV 组件

[H²O](https://proceedings.neurips.cc/paper_files/paper/2023/hash/6ceefa7b15572587b78ecfcebb2827f8-Abstract-Conference.html) 用 heavy hitters 加 recent tokens 做动态 KV 保留；[StreamingLLM](https://hanlab.mit.edu/projects/streamingllm) 说明 attention sink 加滑窗可以稳定长流；[Activation Beacon](https://proceedings.iclr.cc/paper_files/paper/2025/hash/fc797c61eb18f7b3ce9a74af0ef0d876-Abstract-Conference.html) 把 K/V 激活逐步压缩；[KVzip](https://proceedings.neurips.cc/paper_files/paper/2025/hash/f4eaa4b8f2d08edb3f0af990d56134ea-Abstract-Conference.html) 用 context reconstruction 做 query-agnostic eviction；[Landmark Attention](https://proceedings.neurips.cc/paper_files/paper/2023/hash/ab05dc8bf36a9f66edbff6992ec86f56-Abstract-Conference.html) 直接用小 landmark 选择后续 raw block。基本组件的可行性不再是主要研究空白。

### 已经有层级、语义和记忆生命周期，但边界不同

[HMT](https://aclanthology.org/2025.naacl-long.410/) 和 [H²MT](https://arxiv.org/abs/2605.24930) 把记忆组织成层级；[R³Mem](https://aclanthology.org/2025.findings-acl.235/) 研究可逆重建；[EpiCache](https://arxiv.org/abs/2509.17396) 做 episode clustering 和层级预算；[RecMem](https://aclanthology.org/2026.findings-acl.1619/) 让语义 recurrence 触发 consolidation；[MemoryBank](https://ojs.aaai.org/index.php/AAAI/article/view/29946) 具有 significance reinforcement 和 forgetting。这些结果不能直接移植成内部 KV 结论，但会阻止我们把“层级、语义状态、重复使用后巩固、衰减”分别写成新发现。

### 传统系统已经给出很强的控制器基线

[ARC](https://www.usenix.org/conference/fast-03/presentation/arc-self-tuning-low-overhead-replacement-cache) 说明自适应 recency/frequency replacement 是成熟基线；[Belady 的最优替换](https://doi.org/10.1147/sj.52.0078) 是 oracle 上界；working-set 与 reuse-distance 预测为学习型 eviction 提供经典参照；[robust learning-augmented caching](https://proceedings.mlr.press/v139/chledowski21a.html) 说明 learned prediction 应有 classical fallback。GPU/CPU/NVMe 的 [FlexGen](https://arxiv.org/abs/2303.06865)、[ZeRO-Inference](https://www.deepspeed.ai/2022/09/09/zero-inference.html)、[PagedAttention](https://arxiv.org/abs/2309.06180) 也说明“分层存储本身”不是研究空白。

## 公开 failure modes

1. **重复压缩会累积误差。** Hugging Face 对 [Infini-Attention](https://huggingface.co/blog/infini-attention) 的独立复现记录了收敛困难和重复压缩后长期记忆下降；论文数字不能直接当成跨实现保证。
2. **过去 attention 不等于未来 utility。** H²O、recency/frequency、heavy-hitter 策略在扫描、多轮、多 query 或罕见事实工作负载上可能保留错对象。
3. **第一次未知 query 没有 promotion 可用。** 若写入时丢掉了稀有事实，只有 raw archive/fallback 才可能补救；任何“回答后升权”都无法帮助 q1。
4. **RMM 的 utility 可能退化成 attention。** [Eviction as Estimation](https://arxiv.org/abs/2607.24667) 的摘要明确报告，在自然文本上 correctness 过高时，demonstrated utility 与 attention accumulation 接近，并在独立 KVPress/streaming 多轮比较中失去优势。
5. **立即压缩会伤害下一步生成。** [Practical Online KV Cache Compaction](https://arxiv.org/abs/2608.00902) 报告 delayed proxy 比 immediate compaction 更稳；这说明时间点本身是机制变量。
6. **指令与系统提示可能泄漏或被错误保留。** [KV compression pitfalls](https://arxiv.org/abs/2510.00231) 说明方法、压缩顺序和 eviction bias 会改变任务结果，不能只报平均 compression ratio。
7. **系统收益会被 I/O 和 controller 开销吃掉。** SCBench 之所以把 generation、compression、retrieval、loading 分开，就是因为单请求 benchmark 容易漏掉真实 cache lifecycle；HeteroCache 的 checklist 还提示主结果存在 single-run 限制。
8. **层级错误会向下传播。** 高层 route miss、陈旧 child pointer 或 stale index 会直接阻断低层 raw evidence，即使底层证据还在。

## 对 8 个问题的回答

### 1. 哪些组件已经基本成熟，不应单独再研究？

不应再把以下内容单独当作主要贡献：固定 sliding/local window；普通 sparse pattern；基本的 LRU/LFU/ARC；GPU/CPU/NVMe offload 与 paging；“压缩可以节省 KV”；“保存 raw block 可以 fallback”；LongBench/RULER 这类基础 benchmark 的单独使用。它们可以是基线、系统实现或必要组件。

### 2. 哪些仍活跃但高度拥挤？

query-agnostic KV compression、attention-derived eviction、hierarchical landmark/routing、head/layer/episode-specific budget、external semantic memory、predicted future utility、async CPU/SSD retrieval 都是高密度方向。新的工作必须先在同一 workload、同一预算和同一 I/O accounting 下击败强基线，不能只换命名。

### 3. 哪些有公开 failure mode？

重复压缩、立即 compaction、过去 attention 代理、未知首次 query、层级路由 miss、utility collapse、外部 memory 与内部 KV 的错位、I/O 主导延迟、single-run speedup 和 prompt leakage 都已有公开警告，见上节。它们是实验的必测 failure regime，而不是附录里可省略的边角情况。

### 4. 哪些真正是接口问题？

最清楚的接口缺口有六个：

1. **时间接口：** write-time unknown、q1 cold fallback、post-use observation、q2/q3 reuse、decay 的先后和允许信息必须严格定义。
2. **表示接口：** content representation、routing key、child pointer、raw/KV pointer、位置/版本和失效处理必须能互相校验。
3. **效用接口：** attention、retrieval count、counterfactual loss、answer correctness、confidence 和 reuse prediction 如何区分，何时付得起成本。
4. **生命周期接口：** admission、promotion、demotion、precision、GPU/CPU/SSD residency 是一个联合预算问题，不应被拆成互不比较的数字。
5. **硬件接口：** route probes、decompression、PCIe/NVMe 读取、kernel launch、queueing 是否能与 attention 重叠，必须能被复算。
6. **评测接口：** 同一 episode 必须包含未知 q1、真实 pressure、相关但不相同的 q2/q3，以及 evidence recall、answer accuracy、cold reads 和 bytes。

### 5. 把最好组件直接组合，能否得到几乎完整架构？

从工程拼装角度，近似可以得到：NSA/local attention + Activation Beacon/KVzip + Landmark/H²MT route + HeteroCache/Tutti storage + ARC/KVP/RMM controller + PagedAttention/FlexGen。可是这些组件不是即插即用：表示空间、训练目标、层/头语义、raw pointer、位置编码、同步时机和硬件接口不同；把论文数字相加会制造虚假的端到端预期。

### 6. 组合本身是研究价值还是 engineering integration？

如果只是把现有模块串起来、在一个新脚本中跑通，它主要是 engineering integration。只有当组合提出可检验的新接口契约、证明一项现有方法无法覆盖的因果性质，或在严格相同预算与真实 lifecycle 下稳定改变 failure regime，才可能形成研究贡献。当前不能提前作出这类贡献判断。

### 7. 如果不能，最关键缺失环节是什么？

不是又一种压缩器，也不是又一棵层级树。关键缺失环节是：**内部 Transformer/KV 中，第一次冷读之后如何以可观测 utility 重新分配表示精度和硬件 residency，并在后续 reuse、pressure、decay 和 I/O accounting 下证明收益。** RMM、KVP、Practical Compaction 和 HeteroCache 分别覆盖其中一部分，但没有被本轮证据确认成统一闭环。

### 8. 当前是否有足够清晰的新问题值得实验？

有，但只能是窄问题：在相同 representation、tier capacity、cold archive、query sequence、routing result 和 I/O budget 下，比较 cold-only、past-attention、predicted utility 与 demonstrated post-use utility 的后续 q2/q3 代价和证据保留。它是接口/复现问题，不是“RCHAM 整体新架构已经成立”。在继续实验前仍需对 HeteroCache、RMM、KVP、KVzip 及更新的内部 KV 工作再做一次版本和代码核对。

## 研究边界与下一闸门

本审计完成的是 prior-art normalization，不是 novelty certification。所有“未确认完整闭环”的表述都应保留证据范围和日期。下一步若重新提出实验，必须先更新本矩阵、明确 strongest baselines、固定 no-future-leakage 时间轴，并将真实 I/O/控制器成本纳入 protocol。当前按用户要求在此停止：不设计 controller，不训练 Transformer，不启动 GPU 实验。
