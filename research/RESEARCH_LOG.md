# Research Log

## 2026-09-14 · PHASE1-PILOT-001

- Hypothesis：自然语言压缩在未来问题未知时，可能不能直接回答全部问题，但仍能保留部分事实或帮助定位原文。
- Configuration：本地 `ornith-agent:latest`；temperature 0；固定合成 seed；One-shot、Independent Chunk、Hierarchical 三种不看问题的压缩；Raw Context 参照。
- Result：原文 100% 直接 QA；one-shot 3.8% 压缩、25% 直接 QA；chunk 11.7% 压缩、75% 直接 QA；hierarchy 2.2% 压缩、12.5% 直接 QA。chunk lexical route 在 7 个可评估问题上 B evidence recall 85.7%，读回后的 grounded C QA 85.7%。压缩耗时 432.9 秒，回答耗时 224.4 秒。
- Interpretation：partially supported。压缩表示可以保留一部分事实，也可能帮助路由；当前结果不支持“层级结构本身提高 recall”。层级 B/C 因复用 chunk router 未作为独立结果报告。
- Next step：停止在 Phase 1 Pilot 闸门；若继续，先扩展真实化数据、实际 tokenizer 和带 child pointers 的独立层级路由。

失败结果必须保留在 `results/raw/`，不覆盖历史输出。

## 2026-09-14 · RCHAM-PLAN-V0.2

- Hypothesis：未来 query 未知时，单纯压缩/召回不是新的研究问题；真正待验证的是，召回后由 counterfactual utility 证明有用的记忆是否应该升格，长期不用是否降级。
- Configuration：Phase 0 文献与代码证据审计；不下载新权重，不调用收费 API，不运行 CUDA/Transformer 训练。候选工作矩阵、证据账本、复现警告、架构边界和 Phase 1 控制器协议已写入 `research/literature/`、`research/design/` 和 `research/experiments/phase1_protocol.md`。
- Result：在已核对的一手来源中，Landmark Attention 覆盖内部 raw-block 路由，H²MT 覆盖语义层级 coarse-to-fine，HeteroCache 覆盖动态 KV 分层/按需读取，R³Mem/RecMem/MemoryBank 覆盖外部记忆保留与巩固；尚未在本轮主来源中确认一个完整实现同时具备 post-use utility promotion、decay 和内部 Transformer/KV 生命周期。
- Interpretation：暂定 `provisional research gap`，不能写成“没有人做过”。压缩、层级、召回、衰减和访问强化均已存在；可检验的最小差异是 utility 定义、更新时机和相同预算下的控制器比较。
- Next step：Phase 0 到此停止，等待人工检查最近邻工作和创新边界后，再决定是否执行 Phase 1 控制器模拟。不得直接进入大模型训练或 Phase 2。

## 2026-09-15 · RCHAM-PHASE0.5-SEMANTICS-001

- Hypothesis：promotion 不能帮助从未被证明重要的 q1；只有 q1 之后的 post-use utility 才可能改善 q2/q3 的 retention 和访问成本。
- Configuration：正式出版版本优先；核对 Native Sparse Attention、RecMem、HeteroCache 的 ACL metadata/DOI/code，并锁定 Landmark Attention、H²MT、R³Mem、KVzip、MemoryBank、SF-AMS。没有运行模型。
- Result：Native Sparse Attention 的 ACL 2025 Long Paper DOI 为 `10.18653/v1/2025.acl-long.1126` 且标注 Best Paper；RecMem 为 Findings ACL 2026 DOI `10.18653/v1/2026.findings-acl.1619` 并有官方仓库；HeteroCache 为 ACL 2026 Long Paper DOI `10.18653/v1/2026.acl-long.1999` 并有官方仓库。H²MT 和 SF-AMS 仍按 preprint 记录；R³Mem 未找到作者官方代码。未确认完整的内部 `cold retrieval → post-use utility → promote → later reuse → decay` 闭环。
- Interpretation：研究核心改写为“第一次冷召回”与“后续重复使用保留”两个阶段；最小 novelty statement 只针对内部 KV/attention 生命周期中的 post-use utility 资源再分配。
- Next step：Phase 0.5 完成并停止。Phase 1 协议加入 Cold-Raw-Fallback Only 与 Perfect-Routing + No-Promotion，并强制 q1 后 memory pressure 和 q2/q3；等待确认后再实现。

## 2026-09-14 · PHASE0-CODE-AUDIT-001

- Hypothesis：已有压缩/长上下文方法可以在同一 benchmark 上直接做公平比较。
- Configuration：浅克隆 AutoCompressor、ICAE、Activation Beacon、Landmark Attention 官方代码；记录仓库 commit 和原生运行依赖。
- Result：代码静态编译通过；当前机器缺少 PyTorch、Transformers、Triton、FlashAttention 和 CUDA，也没有对应 checkpoint，因此没有伪造性能结果。
- Interpretation：Phase 0 的代码入口已确认，但真实运行被硬件和 checkpoint 闸门阻塞。
- Next step：获得 NVIDIA CUDA 环境和方法对应权重后，运行统一 harness；在此之前只保留代码审计结论。

## 2026-09-15 · PHASE1A-ORACLE-CONTROLLER-001

- Hypothesis：q1 首次冷读取之后，只有在 q1 完成后才得到的 oracle utility 才能促升 M；在相同 Tier 1 预算和后续写入压力下，促升应改善 q2/q3 的后续保留并减少 cold fallback。它不能改善 q1，也不能预测从未被使用过的相关 block。
- Configuration：确定性 synthetic temporal episodes；seed `[7, 11, 19]`；Tier 1 capacity `[8, 16, 32]`；post-q1 pressure `[2x, 4x, 8x]`；delay `short/medium/long`；六种场景；六种 controller。精确 evidence IDs 作为共享 perfect-routing 输入；Tier 2 compressed index 和 Tier 3 raw archive 只做生命周期模拟。没有 Transformer、GPU、模型下载或收费 API。
- Result：486 episodes、2916 runs。Oracle utility 平均 useful-memory retention `0.500`，q2/q3 M survival `0.667/0.833`，total cold reads `2.167`；retrieval-count 为 `0.458`、`0.500/0.833`、`2.167`；cold-only 与 perfect-routing/no-promotion 为 `0.000`、`0/0`、`3.667`。utility 在 useless-distractor 场景避免了 retrieval-count 的访问次数误导，但在 related/competing 场景不能预知 q2 才首次出现的相关证据；decay/cooldown 当前参数反而降低 retention。
- Interpretation：`CONDITIONAL GO`，仅说明 post-use lifecycle controller 值得做更现实的下一轮验证；不支持“解决 future-query-unknown”，也不支持 latency、Transformer 或 GPU 优势。当前创新性仍受 prior-art 风险约束，不能据此宣称新颖架构。
- Next step：停止在 Phase 1A；不得进入 Phase 1B。下一轮若获准，应加入 imperfect routing、deployable utility proxy 和真实 memory sequence，并重复 prior-art gate 后再决定是否继续。

失败结果和 raw traces 保留在 `research/experiments/phase1a/results/`，没有覆盖早期自然语言压缩 Pilot。

## 2026-09-15 · ARCH-LANDSCAPE-AUDIT-001

- Hypothesis：候选 RCHAM 架构由许多已有组件组成；完整 prior-art audit 可能把“新架构”收窄为少数尚未统一的接口问题。
- Configuration：核对 20 个组件；使用正式会议/期刊页面、DOI、arXiv、作者仓库和可查独立复现；扩展到 ARC、Belady、working-set、reuse-distance、learning-augmented caching、tiered storage、SCBench 等传统系统证据。不启动模型、GPU、controller 或 Phase 1B。
- Result：local/sparse attention、历史/KV 压缩、raw fallback、传统 replacement/offload 和基础 benchmark 已成熟；query-agnostic compression、hierarchy/routing、utility、semantic memory、dynamic tiering 和 end-to-end integration 高度活跃且拥挤。公开 failure mode 包括重复压缩、immediate compaction、past-attention 与 future utility 混淆、首次未知 query、层级 route miss、I/O 主导和外部 memory 与内部 KV 错位。
- Interpretation：不能把“压缩 + 层级 + 召回 + 促升 + 分层存储”的拼装写成全新架构。当前唯一保留的窄问题是：内部 Transformer/KV 是否存在一个严格无未来泄漏的 `q1 cold fallback → observed utility → q2/q3 reuse → promotion/demotion/decay` 闭环，并且在相同质量、存储和 I/O 预算下有独立收益。该结论是 provisional，不能写成“没人做过”。
- Next step：停止。若未来重新提出实验，先重新核对 HeteroCache、RMM、KVP、KVzip 及新增工作，再固定 strongest baselines、生命周期 benchmark 和真实 I/O cost model。

审计矩阵、报告和开放问题图分别位于 `research/literature/architecture_landscape_matrix.csv`、`research/reports/architecture_landscape_audit.md`、`research/design/open_problem_map.md`。

## 2026-09-15 · PHASE0-B-LIFECYCLE-GAP-001

- Hypothesis：Architecture-wide Audit 中保留的“post-cold-read internal KV lifecycle”可能仍是缺口，但必须先排除 context-level utility/tiering、lagged eviction、predicted utility 和 raw-block fallback 已经分别覆盖它的情况。
- Configuration：统一 t0–t7 时间轴；主核对 HeteroCache、RMM/Eviction as Estimation、KVP/Learning to Evict、KVzip、Landmark Attention，并扩展 EVICPRESS、AdaptCache、IMPRESS、Strata。只使用正式出版页面、arXiv primary source、作者仓库和公开系统描述；没有训练、GPU 或实验。
- Result：Landmark 覆盖 q1 landmark→raw block；RMM 覆盖 token-level lagged demonstrated-utility retention；KVP 覆盖 offline predicted future utility；KVzip 覆盖 query-agnostic compression/reuse；HeteroCache 覆盖 internal heterogeneous tier 和 attention-drift retrieval；EVICPRESS 已在 context-level 服务系统实现 observed-quality reprofile→compression/eviction/device reallocation 并计入 GPU/CPU/SSD I/O；AdaptCache/IMPRESS/Strata 覆盖预测或系统级 tier。
- Interpretation：不能再声称“post-use resource reallocation 没人做过”。当前只能保留窄的、未确认完整重合的接口：`q1 cold/raw read → exact internal KV/evidence attribution → q2/q3 前 precision/residency/tier change → t7 demotion/decay`。最具体的 failure mode 是 context-level quality/drift 信号无法归因到具体 useful block；RMM 的自然/streaming workload 还显示 post-use utility 可能退化为普通 attention。
- Next step：停止。只有人工确认该 failure mode 值得研究后，才允许设计算法或实现最小 lifecycle benchmark。当前不进入 Phase 1，不训练模型，不启动 GPU。

Phase 0-B 产物：`research/literature/lifecycle_gap_matrix.csv`、`research/reports/phase0_b_lifecycle_gap_falsification.md`，并同步更新 architecture landscape、evidence ledger、reproduction warnings、open problem map 和 novelty boundary。

## 2026-09-15 · PHASE1-MINIMAL-PRINCIPLE-001

- Hypothesis：q1 完成后得到的 task-level counterfactual utility，是否比 recency、frequency、attention 和 RMM-like demonstrated-attention 更能预测 q2/q3 前应该保留的 evidence。
- Configuration：确定性 synthetic episodes；3 seeds `[7, 11, 19]`、capacities `[8, 16]`、pressure `[2x, 4x]`、8 个场景、6 个 policy，共 96 episodes / 576 runs。q1 使用固定 evidence routing；task utility 只在 q1 完成后计算；`oracle_future_reuse` 仅作为不可部署上界。无 Transformer、GPU、offload 或 latency 实验。
- Result：task utility 的 future-useful retention `0.458`，q2/q3 hot answer accuracy `0.375/0.500`；attention、frequency、recency 在当前压力下均为 `0.000`；RMM-like 与 task utility 完全相同，future retention `0.458`、q2/q3 accuracy `0.375/0.500`。Oracle future-reuse 上界为 `0.823` retention、`1.000/1.000` accuracy。
- Interpretation：`NO-GO`。task utility 明显优于 attention/recency/frequency，但没有优于 RMM-like；因此不能证明 task-level counterfactual signal 有独立预测价值。注意前三个 baseline 在 2x/4x pressure 下饱和为零，这个饱和已作为限制保留，不能解释成普遍 superiority。
- Next step：停止。不得进入完整 RCHAM、层级/decay/hardware rescue、真实 benchmark 或 Transformer 实现；只有提出新的、经人工批准的可证伪假设后才能继续。

产物：`research/experiments/phase1_minimal/`、`research/reports/phase1_minimal_principle_test.md`。完整 raw trace 位于本地 `results/full/raw_traces.jsonl`，manifest 保存 SHA-256；sample trace、汇总 CSV 和测试代码纳入版本控制。

## 2026-09-15 · PHASE1R-DISCRIMINATIVE-PRINCIPLE-001

- Hypothesis：使用真实的 q1 counterfactual gold-answer log-probability difference 后，Task Utility 应能在相同 admission budget 下与 RMM-like demonstrated signal 产生可观察决策分歧，并可能更好预测 q2/q3 的 future-useful retention。
- Configuration：独立 `research/experiments/phase1r/`；固定 lexical answer scorer（无训练、无外部模型）；3 seeds `[7, 11, 19]`、capacities `[8, 16]`、pressure `[2x, 4x]`、9 个场景、6 个 policy。q1 后所有 policy 共享 `capacity//2` admission slots；RMM-like 使用 q1 attention × frozen-model correctness，并在报告中明确这是 RMM 的 block-level adaptation，不是 token-level fixed-lag 复现。
- Pre-flight：108 个 episode-budget 单元中，24 个（22.2%）出现 RMM/Task retained-set disagreement，超过 20% gate；eviction decision disagreement 为 60/108，score vector disagreement 为 108/108。
- Result：全部 episode 中 RMM-like future retention `0.556`，Task Utility `0.389`；真正分歧的 24 个单元中 RMM-like `0.833`、Task Utility `0.083`。Task Utility future-retention win rate `0/24`，combined q2/q3 accuracy win rate `0/24`。Recency、frequency、attention 在共享 q1 admission 后不再结构性饱和为零。
- Interpretation：`NO-GO`。这次修正确实使 policy 可区分，但当前 frozen lexical counterfactual signal 在分歧样本上不优于 RMM-like，反而更差；不能用 hierarchy、decay、hardware tier 或更大 benchmark 挽救本阶段结论。该结果也暴露了“gold-answer token support”与语义证据归因之间的限制。
- Next step：停止。不得进入完整 RCHAM、Transformer、GPU 或 Phase 1 后续扩展；保留 Phase 1R raw traces、pre-flight gate、测试和报告供复核。
