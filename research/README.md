# RCHAM：检索反馈式层级注意力记忆

> **最终状态（2026-09-15）：CLOSED。**停止 RCHAM 新架构及 post-use task utility 路线的继续投入。Phase 1R 未充分测试真实模型的命题；终止依据是缺少可靠正证据，而非普遍反证。
> [最终复核报告](reports/research_closeout.md) · [Rejected hypotheses](closeout/rejected_hypotheses.md) · [Reusable infrastructure](closeout/reusable_infrastructure.md) · [Open questions，仅存档](closeout/open_questions.md)。
> 下文保留早期阶段说明，不再授权后续实验；所有复现命令仅作历史资料。

本目录是 RCHAM 研究的独立实验区。**Phase 0.5 已完成，Phase 1A Oracle Controller Pilot 已完成并停止在闸门处。**研究问题已经从“压缩能不能做”收敛为：第一次需求由 cold/raw fallback 处理；记忆被召回且被证明有用后，是否应该提升它的保存精度和 attention 可访问性；长期不用则降级。

本阶段不实现层级检索树、局部 Transformer、快照重建、知识图谱、CUDA/Triton 或大模型训练。

## 当前状态

旧的自然语言压缩 Pilot 已完成，作为 Phase -1 历史证据保留在 `reports/phase1_pilot_report.md`：

```text
确定性自然语言长文档
→ 不看问题的 One-shot / Chunk / Hierarchical 压缩
→ A：仅看压缩表示回答
→ B：压缩表示为 query 找候选原文
→ C：读取候选原文后回答
→ 自动指标、原始输出和失败案例
```

当前没有运行 GPU 方法、没有下载新模型、没有调用收费 API。Phase 1A 只模拟三级 tier 生命周期，结果和停止判断见 `reports/phase1a_pilot_report.md`；环境限制和已审计的官方仓库见 `phase0/environment_gate.md`；语义冻结报告见 `reports/phase0_5_review.md`。

## 目录

- `configs/`：冻结的 Pilot 参数
- `data/`：生成的原文、事实清单和问题；生成器与压缩代码分离
- `src/datasets/`：确定性自然语言 benchmark 生成器
- `src/compression/`：本地模型压缩调用
- `src/evaluation/`：自动评分和图表生成
- `experiments/phase1/`：Pilot 入口
- `results/raw/`：模型的原始摘要和回答
- `results/metrics/`：自动生成的指标
- `results/figures/`：Compression Ratio 图表
- `reports/`：阶段报告
- `literature/`：主论文证据、最近工作矩阵和复现警告
- `design/`：RCHAM v0.2 架构、创新边界和假设
- `experiments/phase1_protocol.md`：下一阶段控制器模拟协议（当前不执行）
- `experiments/phase1a/`：已完成的 oracle controller 时间序列 pilot、测试、raw traces 和指标
- `RESEARCH_LOG.md`：每次实验记录

## 复现

从仓库根目录运行：

```bash
python3 research/src/datasets/generate_pilot.py
python3 research/experiments/phase1/run_pilot.py
python3 research/src/evaluation/score_pilot.py
```

上述命令用于复现历史 Pilot；它不等同于当前 RCHAM Phase 1。当前阶段先读 `research_plan.md` 和 `literature/`，不得跳过 Phase 0 闸门直接训练 Transformer。

## 结论边界

历史 Pilot 的结论是 `partially supported`，不能外推为 RCHAM 成立。当前 Phase 0 的结论和证据等级以 `literature/paper_evidence_ledger.md` 与 `design/novelty_boundary.md` 为准。
