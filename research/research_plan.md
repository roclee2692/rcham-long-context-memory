# Phase 1 Pilot 研究计划

日期：2026-09-14

## 研究问题

不让压缩器看到未来问题时，长文本经过压缩后：

1. 压缩表示能否直接回答事实问题？
2. 压缩表示能否找到正确原文块？
3. 找回原文后，模型能否正确回答？

这三个问题必须分开。摘要不能直接回答，不代表它不能有效路由。

## 假设

- H1：在同一压缩预算下，不同信息类型有不同的保留极限；数字、否定、状态变化可能比普通叙述更容易丢失。
- H2：层级压缩在相同压缩比例下未必优于独立分块压缩；它必须通过实验获得支持。
- H3：压缩表示可能不能直接回答，却能找到含证据的原文；B 成功和 A 失败是有意义的结果。
- H4：如果 C 失败，需要用证据召回率区分路由错误和阅读器错误。

## Baselines

1. Raw Context：原文直接回答，上界参照。
2. One-shot Summary：全文一次摘要，不看问题。
3. Independent Chunk Summary：固定大小块分别摘要，不看问题。
4. Hierarchical Compression：块摘要逐层合并，不看问题。

Pilot 中 B/C 使用块级摘要做简单 lexical overlap 路由。它不是 Phase 2 的复杂层级检索，只用于回答“摘要能否指向正确原文”。

## 数据

确定性生成约 8K–10K proxy tokens 的长文档，包含 60 个可验证事实和 8 个问题，覆盖：普通事实、数字、时间、实体关系、状态更新、否定、跨块关系。事实答案使用唯一字符串，ground truth 由生成器保存，不由模型产生。

## 指标

- `compression_ratio`：压缩表示 proxy tokens / 原文 proxy tokens
- `A_direct_qa_accuracy`：只给压缩表示时的答案准确率
- `B_evidence_recall`：压缩路由选出的原文块是否包含必要事实
- `C_retrieved_qa_accuracy`：读回候选原文后的回答准确率
- `fact_retention_rate`：事实答案字符串是否仍出现在压缩表示
- `hallucination_rate`：输出中出现原文不存在的结构化答案 token 的比例
- `contradiction_rate`：回答了已知事实但用了另一个已知答案 token 的比例
- proxy token 数、压缩调用次数、延迟、原始输出路径

Pilot 的 proxy token 不是模型 tokenizer 的精确 token 数；扩大实验前应接入实际 tokenizer 并固定版本。

## 风险与反证

- 压缩 prompt 看到了问题：直接判为 pipeline 失败，不采用结果。
- 模型输出含解释：评分器只认唯一答案 token，同时保留原文供人工检查。
- 摘要中包含正确 token 但上下文关系错：保留为错误，不只看字符串召回。
- 主题模板过于简单：增加未见实体和值、跨块证据和改写问题。
- 本地模型的系统 prompt 或思考输出污染评分：记录原始输出，清洗规则固定并报告。
- A/C 都高但压缩比例接近 1：不能称为有效压缩。

## 阶段闸门

Pilot 完成后停止扩大规模，先检查 ground truth、泄漏、评分器和失败样本，再决定是否进入正式 Phase 1。当前不进入 Phase 2 或 Transformer 改造。
