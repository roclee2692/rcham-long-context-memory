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

## 2026-09-14 · PHASE0-CODE-AUDIT-001

- Hypothesis：已有压缩/长上下文方法可以在同一 benchmark 上直接做公平比较。
- Configuration：浅克隆 AutoCompressor、ICAE、Activation Beacon、Landmark Attention 官方代码；记录仓库 commit 和原生运行依赖。
- Result：代码静态编译通过；当前机器缺少 PyTorch、Transformers、Triton、FlashAttention 和 CUDA，也没有对应 checkpoint，因此没有伪造性能结果。
- Interpretation：Phase 0 的代码入口已确认，但真实运行被硬件和 checkpoint 闸门阻塞。
- Next step：获得 NVIDIA CUDA 环境和方法对应权重后，运行统一 harness；在此之前只保留代码审计结论。
