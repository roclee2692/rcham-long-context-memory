# Phase 0 环境闸门

检查日期：2026-09-14

## 已确认

- macOS 26.6.2 arm64，Apple M5，10 logical CPUs，16 GiB unified memory
- Python 3.14.7
- `torch`：未安装
- `transformers`：未安装
- `accelerate`：未安装
- `triton`：未安装
- `flash_attn`：未安装
- CUDA/NVIDIA GPU：不可用
- Ollama：已有 `ornith-agent:latest`，约 7.6GB；它不是上述论文方法的 checkpoint

## 已获取的代码

官方仓库浅克隆到本地临时目录 `work/phase0_vendor/`，总大小约 100MB，未下载模型权重：

- AutoCompressor：约 408KB
- ICAE：约 12MB
- Landmark Attention：约 1.1MB
- FlagEmbedding/Activation Beacon：约 88MB

这些 vendor 目录属于工作区临时审计材料，不作为研究结果提交；其 commit 已记录在 `method_matrix.md`。

## 运行闸门结论

当前不能执行忠实的四方法性能实验。原因是缺少 CUDA 运行时、深度学习依赖和专用 checkpoint；仅安装 Python 包也不能解决模型与 GPU 条件。

下一步需要二选一：

1. 提供或授权使用一台 NVIDIA CUDA 机器，并按方法下载对应 checkpoint；或
2. 明确接受“只做代码级 API smoke test，不报告性能”，继续完善统一 benchmark harness。

在获得 CUDA 和 checkpoint 前，不会把 CPU 模拟、Ollama 摘要或随机小模型结果写成 AutoCompressor、ICAE、Activation Beacon 或 Landmark Attention 的实验结果。
