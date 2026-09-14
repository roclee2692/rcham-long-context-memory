# Phase 0-B：Lifecycle Gap Falsification

日期：2026-09-15  
状态：完成文献审计；按要求停止，不设计 controller、不训练模型、不启动 GPU 实验。

## 结论先行

本轮不能再使用宽泛的说法“post-use resource reallocation 没有人做过”。**EVICPRESS 已经在 context-level serving system 上做了在线质量复核、压缩/驱逐/设备重分配，并计入 GPU/CPU/SSD 成本。** AdaptCache、IMPRESS、Strata 也覆盖了预测或历史效用驱动的分层缓存。

更窄、也更准确的结论是：在核对的一手来源中，尚未确认一个方法在 **内部 Transformer/KV 的 token/block 级别** 同时完成：

```text
q1 前不知道未来 query
→ q1 对已被压低精度/移出热层的证据做 cold/raw fallback
→ 观测“正是哪个内部 KV/evidence item 使 q1 变好”
→ 在 q2/q3 前改变该 item 的精度、保留级别或 GPU/CPU/SSD 层级
→ 长期不用时显式 demotion/decay
```

这仍然可能只是一个高风险的工程组合。它只有在证据身份、因果 utility、相同预算和真实 I/O 成本都被严格固定后，才值得称作研究问题。

完整字段化证据见 [`research/literature/lifecycle_gap_matrix.csv`](../literature/lifecycle_gap_matrix.csv)。

## 审计口径

- `t0` 写入：future q 隐藏。
- `t1` 压缩/驱逐/降级：只允许方法在该时刻已有的信息。
- `t2`：第一次意外 query `q1` 到达。
- `t3`：冷/raw 读取、重算或路由后的精确访问。
- `t4`：q1 完成后，方法能否看到实际 utility。
- `t5`：新历史造成真实 memory pressure。
- `t6`：相关但不等同于 q1 的 q2/q3 再次访问。
- `t7`：长期不用或 topic shift 后的 demotion/decay。

“utility”在本报告中只指回答或预测质量对具体 evidence 的可归因变化；attention、访问次数、离线预测和 context-level quality 都单独标记，不能偷换成同一概念。

## 逐方法 t0–t7 核验

### 1. HeteroCache

正式来源：[ACL 2026 Long Paper](https://aclanthology.org/2026.acl-long.1999/)，DOI `10.18653/v1/2026.acl-long.1999`；[arXiv HTML](https://arxiv.org/html/2601.13684)；[作者代码](https://github.com/ponytaill/HeteroCache)。

| 时点 | 可见信息与动作 |
|---|---|
| t0 | 先用独立校准样本估计 head stability/similarity；实际 prompt 的未来用户 query 不可见。 |
| t1 | stable/volatile/anchor/pivot/satellite head 分类和预算基本固定；full、compressed top-l_i、CPU full KV 分层。没有 q1 后 promotion。 |
| t2 | 当前 decode token/query 可见。 |
| t3 | pivot head 监测到 attention drift 时，从 CPU 异步取回 satellite KV 并更新 GPU 表示。它是 drift-triggered refresh，不是“q1 证据缺失后从 raw archive 取回并验证”的协议。 |
| t4 | 没有 answer flip、counterfactual loss 或 exact evidence identity；attention drift 是代理信号。 |
| t5 | head taxonomy 和 ratio 不因 q1 的实际 utility 改变。 |
| t6 | 方法主要是连续 token decoding，不是同一 M 经 q1 后再经历 q2/q3 的重复生命周期。 |
| t7 | 没有显式 inactivity/topic-shift demotion 或 decay。 |

实际计入 PCIe CPU→GPU 传输和 decode latency；没有完整 q1/q2 evidence 生命周期。故为 **partial**。

### 2. RMM / Eviction as Estimation

来源：[arXiv 2607.24667](https://arxiv.org/html/2607.24667)。当前按 preprint 处理，未确认 version-of-record、作者代码或 checkpoint。

| 时点 | 可见信息与动作 |
|---|---|
| t0 | token 进入 provisional buffer，future query/answer 隐藏。 |
| t1 | 固定 lag `H` 内保留；lag 后用 correctness-weighted attention/teacher forcing 估计 demonstrated utility，再 commit 到 bounded cache。 |
| t2 | 没有保留的 raw/cold archive；被 commit/evict 的 token 不能靠该方法恢复。 |
| t3 | 没有 q1 cold/raw retrieval。 |
| t4 | 这是最接近“post-use” 的方法：看到近未来预测是否正确以及 token attention，但不是 q1 对 exact evidence 的 answer-level cold-read utility。 |
| t5 | bounded K 触发 commit/evict；没有 GPU/CPU/SSD tier。 |
| t6 | 人工构造 endogenous-reuse 任务有较强 retention；独立 KVPress streaming multi-turn 结果显示优势大幅减弱或消失。 |
| t7 | 没有独立的长期 inactivity decay；后续只会再次被普通淘汰。 |

没有物理 I/O 或 loading cost。它证明了“延迟一段时间再用实际预测信号作保留决策”值得测，却没有证明完整生命周期。

### 3. KVP / Learning to Evict

来源：[arXiv 2602.10238](https://arxiv.org/html/2602.10238)；[作者代码与权重](https://github.com/apple-aiml-research/ml-learning-to-evict)。arXiv 标注 accepted at ICML 2026。

| 时点 | 可见信息与动作 |
|---|---|
| t0 | 部署只看 K、V、位置；future query/answer 隐藏。训练阶段离线 trace 可包含未来 reuse，但不应与部署信息混同。 |
| t1 | per-head RL agent 预测 future utility，在固定预算下排序/驱逐；没有 provisional q1 后更新。 |
| t2 | 当前生成发生。 |
| t3 | 没有 raw fallback。 |
| t4 | 没有 actual post-use utility；它是 predicted future utility。 |
| t5 | 固定预算继续按静态 learned score 淘汰。 |
| t6 | 有 multi-turn/long-context 评测，但同一 policy 不会因为 q1 证明 M 有用而 promotion。 |
| t7 | 没有显式 decay/demotion。 |

代码和训练流程公开，但训练 trace、8 GPU 训练和模型适配是复现前提。KVP 与 RMM 的差别正好可用于判定“预测”是否等价于“使用后观察”：两者不是同一时间点。

### 4. KVzip

正式来源：[NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/f4eaa4b8f2d08edb3f0af990d56134ea-Abstract-Conference.html)，DOI `10.52202/085713-5585`；[arXiv HTML](https://arxiv.org/html/2505.23416)；[代码](https://github.com/snu-mllab/KVzip)。

| 时点 | 可见信息与动作 |
|---|---|
| t0 | context prefill 时尚不知道 eventual user query。 |
| t1 | context reconstruction 计算 query-agnostic 分数，一次性按 ratio/head pruning。 |
| t2 | q1 在压缩后到达。 |
| t3 | 论文和 README 没有给出被剪掉 KV 的 raw archive/cold fallback；`update_cache=True` 主要更新 query/generated token 的选择。 |
| t4 | 没有 answer-level 或 exact evidence-level post-use utility。 |
| t5 | ratio/score 继续固定。 |
| t6 | 支持多个不同 query 复用同一 compressed cache，但不会因 q1 结果升高 M 的精度或层级。 |
| t7 | 没有显式 decay。 |

它是 query-agnostic compression/reuse 的强基线，而不是 lifecycle feedback 方法。一次压缩成本和 FlashAttention 延迟被报告；没有 GPU/CPU/SSD tier I/O。

### 5. Landmark Attention

正式来源：[NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/hash/ab05dc8bf36a9f66edbff6992ec86f56-Abstract-Conference.html)，DOI `10.52202/075280-2378`；[arXiv HTML](https://arxiv.org/html/2305.16300)；[代码](https://github.com/epfml/landmark-attention)。

| 时点 | 可见信息与动作 |
|---|---|
| t0 | block 和 landmark 写入；future q 隐藏。 |
| t1 | landmark→raw block 数据结构固定，没有 promotion/eviction controller。 |
| t2 | q1 到达。 |
| t3 | q1 先打 landmark，再取回 top-k raw blocks；这是本组工作中最明确的 first-time cold/raw fallback。 |
| t4 | 不记录 answer utility，也不更新 block 的保留精度。 |
| t5 | 没有 q1-driven resource reallocation。 |
| t6 | 每个后续 query 都重新 route；曾经有用不会变成更热或更高精度。 |
| t7 | 没有 decay/demotion。 |

其 32K passkey/random-access 结果不能直接当作 q1→q2 生命周期结果；评测没有施加后续 pressure 和长期不用阶段。

### 6. EVICPRESS

来源：[arXiv 2512.14946](https://arxiv.org/html/2512.14946)。当前按 preprint、系统级 context KV 工作处理，未确认官方代码。

| 时点 | 可见信息与动作 |
|---|---|
| t0 | context KV 生成；离线 profiler 为每个 context 生成 synthetic questions，得到质量/TTFT profile。 |
| t1 | context 级 compression、GPU/CPU/SSD assignment 和 greedy multi-choice knapsack；不是 token/block identity。 |
| t2 | cache hit 时请求到达；cache miss 会 recompute/store，而不是从已被压掉的 raw token/block 取回。 |
| t3 | 已存在的 context cache 可从 tier 加载；没有“q1 exact evidence cold read”协议。 |
| t4 | 在线质量与 uncompressed prefill answer 比较；质量低于阈值时用更新 query set re-profile。这是 context-level observed quality drift，不是 exact internal evidence utility。 |
| t5 | compression/device/eviction 可被压力和 profile 改变。 |
| t6 | 重复 context reuse 和请求频率被评测；q2/q3 仍是 context-level request。 |
| t7 | 没有明确 inactivity/topic-shift decay；frequency/pressure 可能间接降低 residency。 |

它是本轮最重要的 broad counterexample：已经有“观察到线上质量后重分配资源 + 真实 I/O”。因此不能再把“观察后资源重分配”整体说成空白。剩下的是粒度、身份和 q1 cold/raw 语义。

### 7. AdaptCache

来源：[arXiv 2509.00105](https://arxiv.org/html/2509.00105)。按 preprint/SOSP 2025 BigMem workshop 工作处理，未确认官方代码。

| 时点 | 可见信息与动作 |
|---|---|
| t0 | offline profiler 用 dummy questions 和历史频率估计质量/压缩曲线；未来真实 q 隐藏。 |
| t1 | 以 marginal utility 选择 DRAM/SSD、压缩和 eviction。 |
| t2 | 请求到达。 |
| t3 | 从 DRAM/SSD load，miss 时 recompute；不是 raw evidence fallback。 |
| t4 | 没有 q1 answer flip 或 block-level actual utility；频率是历史/预测信号。 |
| t5 | 压力下重算 marginal utility 并改变 context placement。 |
| t6 | Poisson arrivals 模拟重复 context reuse。 |
| t7 | 没有独立 inactivity decay。 |

它进一步说明 tier allocation 和历史/预测效用已有系统实现，但不覆盖 post-cold-read internal KV identity。

### 8. IMPRESS

来源：[FAST 2025 页面](https://www.usenix.org/conference/fast25/presentation/chen-weijian-impress)，[PDF](https://www.usenix.org/system/files/fast25-chen-weijian-impress.pdf)。

| 时点 | 可见信息与动作 |
|---|---|
| t0 | prefix KV 写入并依据 attention-head similarity 打分。 |
| t1 | 重要 prefix 选择和 GPU/CPU/disk placement。 |
| t2 | 请求到达。 |
| t3 | 选择性从 tier 加载 prefix KV；没有 q1 后 evidence utility。 |
| t4 | 没有 answer-level post-use 观测。 |
| t5 | score-based tier management。 |
| t6 | 重复 prefix reuse 由缓存服务。 |
| t7 | 没有显式 decay/demotion。 |

这是成熟的 systems-side tier/fallback 证据，不是 internal post-use lifecycle 闭环。

### 9. Strata

来源：[arXiv 2508.18572](https://arxiv.org/html/2508.18572)。按 system preprint 处理，未确认官方代码。

| 时点 | 可见信息与动作 |
|---|---|
| t0 | prefix/context cache entry 写入；未来请求隐藏。 |
| t1 | hierarchy、radix-tree 和 scheduler 做 placement；不使用 q1 utility。 |
| t2 | 请求到达。 |
| t3 | cache hit/load 或 miss/recompute；不保证 raw evidence retrieval。 |
| t4 | 没有 answer-level utility feedback。 |
| t5 | scheduler 处理容量和请求压力。 |
| t6 | 重复 context reuse 是主要 workload。 |
| t7 | Strata 贡献中没有显式 inactivity/topic decay。 |

其 I/O/TTFT 价值很重要，但不能被解释成 post-use internal KV promotion。

## 覆盖矩阵的判定

| 环节 | Landmark | HeteroCache | RMM | KVP | KVzip | EVICPRESS/系统类 |
|---|---:|---:|---:|---:|---:|---:|
| q1 前 future hidden | 是 | 是（有离线 calibration） | 是 | 是（部署） | 是 | 部分（有 synthetic/profile information） |
| q1 cold/raw fallback | **是** | drift-triggered CPU refresh，语义不同 | 否 | 否 | 未证明 | context load/recompute，非 raw evidence |
| q1 后 actual utility | 否 | 否，只有 drift | **部分**，lagged correctness-weighted attention | 否，预测 | 否 | **部分**，context quality drift |
| 改变 exact internal KV precision/tier | 否 | 固定 head/tier，非 q1 utility | 只改变 token survival | 否 | 否 | context-level 改变，不是 exact block |
| q2/q3 related reuse under pressure | 否 | 非该 protocol | 构造任务有，独立自然文本弱 | 静态复用 | 多 query 静态复用 | context-level reuse |
| later demotion/decay | 否 | 否 | 无显式 | 否 | 否 | 无显式 inactivity decay |
| real I/O/loading | 部分 | **是** | 否 | 否 | 否 | **是** |

## 对四个问题的直接回答

### A. 是否已有完整覆盖？

**在本轮核对的一手来源中，没有确认完整覆盖。** 但这个回答必须带粒度限定：

- Landmark 已解决 q1 的 landmark→raw block 路由。
- RMM 已提供 token-level、lagged、demonstrated-utility retention 信号。
- HeteroCache 已提供 internal KV 的异构层和 attention-drift-triggered async retrieval。
- EVICPRESS 已提供 context-level observed-quality reprofile→compression/eviction/device reallocation，并测量 GPU/CPU/SSD。
- AdaptCache/IMPRESS/Strata 已提供预测或系统级 tier placement。

没有一篇被确认把这些变成同一条 **exact internal KV identity** 时间线，并在 q1 冷读取之后改变该 item 的精度/层级、测 q2/q3，再在 t7 明确降级。

### B. 若没有，最小缺失动作是什么？

不是“再做一个层级架构”。最小缺失动作是：

> **把 q1 冷读取后可观测的质量/utility 归因到具体的内部 KV block/token/evidence identity，并在 q2/q3 到来前据此改变该 item 的 precision/residency/tier；同时保留可检查的后续 demotion 规则。**

关键动词是“归因到 exact item”。EVICPRESS 的 context-level quality drift 和 HeteroCache 的 attention drift 都不能直接证明这一点。

### C. 这个缺失动作可能只是工程整合吗？

**可能，而且风险很高。** 如果只是把 Landmark 的 raw pointer、RMM 的 delayed score、HeteroCache 的 tier transfer、ARC/LRU 的 decay 接起来，没有新的因果保证、没有更低 I/O、没有稳定 q2/q3 advantage，那就是 engineering integration。只有当 exact attribution 在相同 quality/bytes/I/O budget 下改变公开 failure mode，研究价值才足够强。

### D. 有没有公开 benchmark 直接测？

没有找到一个同时固定以下条件的公开标准协议：未知 q1、首次 cold/raw fallback、post-use evidence attribution、memory pressure、相关 q2/q3、tier/I/O、长期 decay 和最终回答正确性。

已有工具只能覆盖切片：LongBench/RULER/LongMemEval/BABILong 测长上下文或长记忆；KVPress/SCBench 测压缩、检索和 loading；Landmark 测 block retrieval；EVICPRESS 用 LongBench 测 context-level quality/TTFT。它们不能直接判定本缺口。

## 最小 lifecycle benchmark（仅定义，不执行）

未来如果要验证，最小 episode 应固定为：

```text
t0  写入 M、related evidence、useless frequent distractor、obsolete block；q1/q2/q3 不进入写入或压缩 prompt
t1  压缩/驱逐/分层
t2  写入大量 history，制造 pressure
t3  q1 首次需要 M，必须发生 cold/raw fallback
t4  保存 q1 的 evidence IDs、answer/loss flip、读取 bytes/probes
t5  只在此之后允许更新 M 的精度/层级/驻留
t6  再写入压力，出现语义相关但措辞不同的 q2/q3
t7  插入长 inactivity/topic shift，再测 demotion/decay
```

必要对照不是新 controller 设计，而是边界：FullKV oracle、ColdRawFallbackOnly、Landmark-style route、RMM-style lagged signal、KVP-style prediction、KVzip-style query-agnostic compression、HeteroCache/EVICPRESS-style system tier baseline、No-promotion。指标应包括 q1 evidence recall、exact attribution fidelity、q2/q3 evidence recall、precision/tier/hardware residency、cold bytes/blocks、promotion regret、demotion/churn 和 controller/I/O cost。

## 发现的具体 failure mode

本轮已确认一个足以阻止直接进入算法设计的具体风险：

> **context-level quality reprofile 或 attention-drift 只能说明“整体表示变差/分布变了”，不能说明“哪个被冷读的内部 KV block 改变了 q1 的答案”。**

因此它们可能把错误的 block 升温，或把一个频繁被访问但无用的 distractor 固定在高精度层。RMM 提供了第二个失败信号：在人工构造的 endogenous-reuse 中 post-use retention 有效，但自然文本/独立 streaming multi-turn 上 demonstrated utility 退化为普通 attention，优势消失。后续任何算法必须先能区分这两个 failure mode。

## 停止条件

Phase 0-B 已完成。当前不启动 benchmark、不实现 controller、不训练模型、不启动 GPU。只有在人工确认这个具体 failure mode 值得继续后，才进入算法设计或最小生命周期 benchmark 实现。
