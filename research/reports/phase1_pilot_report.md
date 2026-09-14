# Phase 1 Pilot Report

日期：2026-09-14
实验编号：`PHASE1-PILOT-001`
结论：`partially supported`

## Environment

实验在 macOS 26.6.2 arm64、Apple M5、16 GiB unified memory 上运行。使用机器上已有的 Ollama 模型 `ornith-agent:latest`，temperature 为 0，seed 为 `20260914`，context 上限为 16,384。没有下载新模型，没有调用收费 API。实验完成后已停止模型推理进程，`ollama ps` 为空。

## Implemented

Pipeline 是：确定性数据生成 → 不看问题的压缩 → A 直接回答 → B 从摘要选原文块 → C 阅读选中的原文块后回答 → 自动评分。

实现了原文、全文一次摘要、独立分块摘要和层级摘要四种表示。每次压缩的 prompt、原始 response、延迟和 token 计数都保存在 `results/raw/`。早先发现的“答案可从题号猜出”的无效运行保存在 `results/raw/pilot_001_template_leak/`，没有覆盖或删除。

## Dataset

文档由固定 seed 生成，包含 60 条事实，原文约 7,113 个 proxy tokens，分为 6 个块；问题 8 个，覆盖普通事实、数字、时间、状态变化、跨块关系和多证据问题。答案是随机生成的唯一字符串，问题不包含答案字符串。Q8 需要两个原文块，当前单块 lexical router 不处理它，按预先约定标记为 skipped。

这是一套结构化自然语言 pilot，不是现实语料。proxy token 是固定的字符/字母数字计数，不是模型 tokenizer 的精确计数。

## Results

### A：只看表示直接回答

| 表示 | 压缩比例 | 表示中事实保留 | 直接 QA | 矛盾回答 |
|---|---:|---:|---:|---:|
| Raw context | 100.0% | 100.0% | 100.0% | 0.0% |
| One-shot summary | 3.8% | 25.0% | 25.0% | 25.0% |
| Independent chunk summary | 11.7% | 75.0% | 75.0% | 12.5% |
| Hierarchical summary | 2.2% | 12.5% | 12.5% | 37.5% |

这支持一个有限结论：分块摘要在约 8.6 倍压缩时仍保留了本 pilot 中 75% 的测试事实；一次性摘要和当前层级合并摘要损失更多。它没有证明层级结构本身改善召回，当前结果反而不支持这个说法。

### B/C：先路由，再读原文

当前只把 `chunk_summary` 的词法路由作为独立 B/C 结果。层级表示的 B/C 原始行保留在 raw 中，但它们复用了相同的 chunk-summary router，不能作为层级召回实验。

| 路由表示 | 可评估问题 | 原文证据召回 B | 读回原文后回答 C | 有证据支撑的 C |
|---|---:|---:|---:|---:|
| Independent chunk summary + lexical route | 7/8 | 85.7% | 85.7% | 85.7% |

Q8 被跳过，不计入 B/C 分母。Q4 是一个明确失败：路由选中了块 0、1，没有包含 `FACT-026`，所以即使模型输出了一个 state token，也不计为证据支撑的正确答案。

### 成本与延迟

压缩调用 10 次，总耗时约 432.9 秒；回答调用 46 次，总耗时约 224.4 秒。结果说明 Python pilot 的端到端延迟不能代表未来 CUDA/Transformer 实现的速度，也没有证明层级结构有 latency 优势。

## Failure Cases

1. One-shot summary 在数字、时间、状态、关系和多证据问题上大量丢失细节。
2. Hierarchical summary 最终只有 2.2% 的原文 proxy tokens，事实保留率为 12.5%，并出现 37.5% 的已知 token 矛盾回答。
3. Q4 的 lexical router 只按词重叠选块，无法利用 station 编号和 state 语义可靠定位事实。这是 routing failure，不是压缩内容是否存在的直接证据。
4. 层级 B/C 没有独立的 child-pointer 路由；当前 raw 行只是用同一个块摘要 router 做的诊断，不能支持“层级召回优于 flat retrieval”的结论。
5. 早期 pilot 暴露了答案模板泄漏，已经归档并标记为无效。修正后的数据使用随机答案令牌，并通过原始 prompt 检查压缩阶段没有问题文本。

## Preliminary Conclusion

`partially supported`。

本 pilot 支持“压缩表示可能同时承担有限的直接回答和原文路由功能”，但支持强度有限：只有 60 条模板化事实和 8 个问题；chunk summary 的 75% 直接保留与 85.7% 路由/读回结果不能外推到真实长文档。当前实验否定了“层级结构天然提高 recall”的未经验证假设；层级摘要在本配置下明显劣于独立分块摘要。

## Problems Found

- 数据是结构化模板，尚未覆盖真实叙事、改写、冲突证据和更密集的跨段关系。
- proxy token 不是模型 tokenizer，压缩比例只能作相对比较。
- 评分器按唯一答案 token 评分，适合本 pilot 的可验证事实，不等价于开放问答质量。
- B 使用简单 lexical overlap，不能代表成熟的层级检索系统。
- 层级摘要没有保留 child pointers，因此本阶段尚未验证“高层定位 → 低层展开”。

## Proposed Next Experiment

先扩大 Phase 1，而不是进入 Phase 2：增加独立生成的文档和问题，加入改写问题、否定、状态前后顺序、跨块双证据，并接入实际 tokenizer。对比相同压缩预算下的 one-shot、chunk 和 hierarchy；同时把 B/C 拆成真正独立的 flat lexical route、flat embedding route 和带显式 child pointers 的 hierarchy route。每个路由器都必须报告证据召回、访问块数和读回后的 grounded QA。

本报告完成后停止。没有进入 Transformer Attention、CUDA、动态窗口或大规模 Phase 1。
