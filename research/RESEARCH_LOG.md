# Research Log

## 2026-09-14 · PHASE1-PILOT-001

- Hypothesis：自然语言压缩在未来问题未知时，可能不能直接回答全部问题，但仍能保留部分事实或帮助定位原文。
- Configuration：本地 `ornith-agent:latest`；temperature 0；固定合成 seed；One-shot、Independent Chunk、Hierarchical 三种不看问题的压缩；Raw Context 参照。
- Result：原文 100% 直接 QA；one-shot 3.8% 压缩、25% 直接 QA；chunk 11.7% 压缩、75% 直接 QA；hierarchy 2.2% 压缩、12.5% 直接 QA。chunk lexical route 在 7 个可评估问题上 B evidence recall 85.7%，读回后的 grounded C QA 85.7%。压缩耗时 432.9 秒，回答耗时 224.4 秒。
- Interpretation：partially supported。压缩表示可以保留一部分事实，也可能帮助路由；当前结果不支持“层级结构本身提高 recall”。层级 B/C 因复用 chunk router 未作为独立结果报告。
- Next step：停止在 Phase 1 Pilot 闸门；若继续，先扩展真实化数据、实际 tokenizer 和带 child pointers 的独立层级路由。

失败结果必须保留在 `results/raw/`，不覆盖历史输出。
