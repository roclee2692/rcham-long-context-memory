# Phase 0：文献与现成实现验证

日期：2026-09-14

Phase 0 的目的不是重新证明“压缩可以存在”，而是把已有方法放到同一套可复现协议中，确认它们在当前硬件上能否真实运行，以及论文结论哪些可以直接比较。

当前状态：完成官方代码浅克隆和运行条件审计；尚未下载任何模型权重，尚未产生方法性能结果。

## 方法边界

计划直接验证：

- AutoCompressor
- ICAE
- Activation Beacon
- Landmark Attention

Infini-attention 和 Compressive Transformer 先作为机制和失败模式参考。它们的官方或作者代码通常需要重新训练、特定基座模型或 CUDA 环境，不能把一个非官方 CPU 实现当成论文复现。

## 共同 benchmark

沿用 Phase 1 的确定性 benchmark：约 7,113 个 proxy tokens、60 条事实、8 个问题，包含数字、时间、状态、否定、关系和多证据问题。正式 Phase 0 扩展时需要增加真实文档和改写问题。

每个方法都必须记录：

1. 事实回答准确率和证据召回率
2. 压缩表示大小
3. 访问或激活的历史块数量
4. prefill/decode latency
5. 峰值内存和 KV cache 大小
6. 模型、checkpoint、tokenizer、代码 commit 和运行参数

自然语言摘要的 token 压缩率、soft prompt 的 slot 压缩率、KV activation 的 cache 压缩率不是同一个单位。报告中会分开列出，不能直接拼成一个“谁压缩率最高”的排行榜。

## 当前阻塞

本机没有 PyTorch、Transformers、Triton、FlashAttention 或 CUDA；只有 Apple GPU 和现有 Ollama 模型。官方入口依赖 CUDA/专用 checkpoint，因此当前只能完成代码审计，不能诚实地声称已经运行了四种方法。

需要继续真实运行时，最小可行路线是准备带 NVIDIA CUDA 的机器，并分别获得对应 checkpoint。任何超过 5GB 的模型下载或远程 GPU 运行都要单独记录成本和环境。

详细入口、版本和阻塞见 `method_matrix.md` 与 `environment_gate.md`。

论文可信度、训练依赖、评测泄漏和独立复现风险见 `paper_forensics_report.md`。该报告使用 paper-forensics Skill 的 G0–G4 证据等级；它不会把不可复现直接称为造假。
