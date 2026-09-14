# Phase 1：自然语言压缩与证据保留 Pilot

本目录是 `Hierarchical Reconstructive Attention` 研究的独立 Phase 1 实验区。当前只研究一件事：**文本压缩后，关键事实能否仍被直接回答，或至少能帮助找到原文。**

本阶段不实现层级检索树、局部 Transformer、快照重建、知识图谱、CUDA/Triton 或大模型训练。

## 当前状态

已完成小规模 Pilot，报告见 `reports/phase1_pilot_report.md`：

```text
确定性自然语言长文档
→ 不看问题的 One-shot / Chunk / Hierarchical 压缩
→ A：仅看压缩表示回答
→ B：压缩表示为 query 找候选原文
→ C：读取候选原文后回答
→ 自动指标、原始输出和失败案例
```

模型使用本机已有的 `ornith-agent:latest`；没有下载模型，没有收费 API。

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
- `RESEARCH_LOG.md`：每次实验记录

## 复现

从仓库根目录运行：

```bash
python3 research/src/datasets/generate_pilot.py
python3 research/experiments/phase1/run_pilot.py
python3 research/src/evaluation/score_pilot.py
```

第二条命令会调用本地 Ollama。它只适合小规模 Pilot；正式扩大前必须先检查评分、摘要是否泄漏问题、原始输出和失败样本。

## 结论边界

当前结果是 `partially supported`：独立分块摘要在约 11.7% 的大小下直接回答 75% 的 pilot 问题；简单词法路由在 7 个可评估问题上召回并读回正确证据 85.7%。层级摘要只有 12.5% 的直接事实保留，层级 B/C 尚未独立测试。所有结论以 `reports/phase1_pilot_report.md` 为准。
