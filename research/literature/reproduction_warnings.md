# Phase 0 复现警告

## 当前环境闸门

- macOS 26.6.2 arm64，Apple M5，10 logical CPUs，16 GiB unified memory。
- 当前环境没有 CUDA/NVIDIA、PyTorch、Transformers、Triton 或 FlashAttention。
- 官方仓库已经做静态入口审计并记录 commit，但没有下载 7B 权重，也没有声称获得 latency、显存或 LongBench 结果。
- 历史 Pilot 使用本机已有 Ollama 模型；Phase 0 不启动新模型。结束检查应保持 `ollama ps`、`pgrep -af llama-server` 为空，避免后台占用内存。

## 不能直接横向比较的东西

1. 论文中的 compression ratio 可能分别指 input token、soft memory slot、KV entry、retrieved block token 或 peak bytes；报告时必须拆列。
2. Activation Beacon 的 speed/KV 数字依赖训练过的压缩行为、模型、kernel 和硬件；不能拿 CPU/Apple 运行时间替代。
3. Landmark 的 block recall、ICAE 的重建 BLEU、Gist 的 prompt task score、H²MT 的 TTFT 并不是同一个指标。
4. 论文使用的 checkpoint、数据生成器、judge 和上下文长度不同。对比必须固定预算、问题、候选集合和答案键。

## 数据与评审风险

- 未来 query 泄漏进摘要或写入 prompt，会把“未知未来”假设破坏掉。
- 合成 QA 或 LLM judge 可能偏好格式；首要指标应是 ground-truth evidence recall、answer exact match 和 counterfactual utility。
- needle 任务容易让问题显得过于明显；Phase 1 必须加入状态变化、否定、条件、跨事件和延迟相关。

## 代码、权重和版本风险

- 官方仓库有代码不代表发布了对应 checkpoint 或完整训练脚本。
- 依赖版本、FlashAttention/Triton kernel、GPU 型号和 batch/sequence 配置都会影响 latency。
- 所有复现要记录 paper version、repo commit、model hash、tokenizer、CUDA/driver/PyTorch/Transformers 版本、seed、原始 stdout/stderr 和峰值显存。

## 不应过度解释的结果

- “检索到”不等于“检索有用”。RCHAM 必须用去掉该证据后的 answer flip 或 loss difference 估计 utility。
- “访问次数多”不等于“重要”。频繁误召回会制造正反馈，必须与 utility-conditioned baseline 分开。
- “层级树更少比较”不等于 recall 更高。路由成本、层级维护和错误传播必须单独统计。
- Independent reproduction 失败是方法敏感性证据，不是原论文造假证据。

## Phase 0.5 版本与代码核对

- Native Sparse Attention 的正式记录是 ACL 2025 Long Paper，DOI `10.18653/v1/2025.acl-long.1126`，ACL 页面标注 Best Paper。正式页面没有作者代码链接；GitHub 上的 NSA 实现不能自动标成官方实现。
- RecMem 的正式记录是 Findings ACL 2026，DOI `10.18653/v1/2026.findings-acl.1619`。作者仓库 `CaiusDai/RecMem` 已公开，README 给出 `uv.lock` 和评测入口，但依赖 OpenAI API 和外部数据路径，不能在当前环境直接复现。
- HeteroCache 的正式记录是 ACL 2026 Long Paper，DOI `10.18653/v1/2026.acl-long.1999`。ACL 页面明确链接 `ponytaill/HeteroCache`；README 的 head clustering、LongBench/InfiniteBench 和 latency 入口需要 CUDA、模型权重和真实 offload。
- H²MT 当前仍按 arXiv preprint 记录，DOI 是 `10.48550/arXiv.2605.24930`；本轮未找到正式出版版本或作者官方代码。
- R³Mem 的正式记录是 Findings ACL 2025，DOI `10.18653/v1/2025.findings-acl.235`；本轮未找到作者官方代码。
- SF-AMS 当前只有 arXiv `2607.22562`，没有确认的 version-of-record 或作者公开代码；只能作为最近的外部 utility/forgetting 证据。

## 语义冻结带来的新风险

`first-time recall` 与 `repeated-use retention` 不能合并成一个 recall 指标。一次只被查询一次的 memory 只能评估冷召回，不能证明 promotion 有价值。任何 Phase 1 结果都必须有 `q1` 后至少一个 memory-pressure interval，再出现 `q2/q3`。

`retrieval-count` 不是 utility。SF-AMS、MemoryBank 和 RecMem 说明“使用、重复或时间”可以影响外部记忆的生存，但这不能直接当作内部 KV 的 counterfactual usefulness。

Oracle utility 使用 gold answer 或 counterfactual loss，只能作为机制上界。它不能被描述成部署算法；deployable utility proxy 必须另立研究问题。

## 未确认候选

WhenLoss、MARCH、CueMem、Dynamic Hierarchical Sparse Attention 和若干 2026 learned KV policy 的公开主来源尚未在本轮全部固定。它们在获得一手论文、版本、代码和实验配置前，只能放在待核查列表，不能用来支持“已有完全重合”的结论。

## Phase 0-B 新增边界

- EVICPRESS 是重要的 broad counterexample：它在 context-level serving system 上做在线质量复核和 GPU/CPU/SSD 资源重分配，并测量 I/O/TTFT。但其质量指标是与 uncompressed prefill answer 的 context-level 相似度，不是某个内部 token/block 的 evidence recall 或 answer flip；cache miss 主要是 recomputation。不能把它直接记为“完整 internal KV lifecycle”。
- AdaptCache 的 utility 主要来自历史命中频率和离线质量-延迟曲线；这是 predicted/historical utility，不是 q1 完成后可归因的 actual utility。其 Poisson arrival 和系统级 tier 结果不能替代 q1/q2/q3 时间协议。
- IMPRESS、Strata 进一步证明 GPU/CPU/disk tier 和 repeated context I/O 已是成熟或活跃的 systems 组件；它们没有给出 post-use exact evidence attribution 与显式 inactivity decay。
- RMM 的 demonstrated utility 不能自动当作部署优势：其自然文本/独立 streaming multi-turn 对照显示 utility 可能退化为累计 attention。后续必须把人工构造的 endogenous-reuse 和自然 workload 分开报告。
- 因此本轮缺口只能写成粒度和因果接口缺口：`q1 cold/raw read → exact KV/evidence attribution → q2/q3 resource change → t7 demotion`。不能写成“观察后资源重分配从未被研究”。
