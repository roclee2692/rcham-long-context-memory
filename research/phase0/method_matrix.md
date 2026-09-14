# Phase 0 方法矩阵

审计日期：2026-09-14

| 方法 | 官方实现 | 当前记录的 commit | 原生对象 | 官方入口/依赖 | 当前机器状态 |
|---|---|---|---|---|---|
| AutoCompressor | `princeton-nlp/AutoCompressors` | `80352a4233c4a70504c75bf95c5f3e6d2533a863` | summary vectors / soft prompts | Llama/OPT checkpoint；PyTorch 2.1；Transformers 4.34；FlashAttention；CUDA；README 的示例使用 `AutoCompressor-Llama-2-7b-6k` | blocked：无 torch/CUDA/权重 |
| ICAE | `getao/icae` | `469a46886a92dd5e76b2d12a8bac0fb7ed7d4cdd` | memory slots | Mistral-7B 或 Llama-2-7B ICAE checkpoint；Transformers >=4.36.2；CUDA 代码路径 | blocked：无 torch/Transformers/权重 |
| Activation Beacon | `FlagOpen/FlagEmbedding`, `research/Long_LLM/activation_beacon` | `fd1a2bdf69488ffebe0327999d4400d8c8058a0b` | per-layer K/V beacon activations | beacon checkpoint；PyTorch CUDA 12.1；FlashAttention 2；Transformers/DeepSpeed/Accelerate；示例 `beacon-qwen-2-7b-instruct` | blocked：无 torch/CUDA/权重 |
| Landmark Attention | `epfml/landmark-attention` | `d963e504fa2424687c6cbd412b54f1626e832292` | landmark block representations + raw block access | LLaMA fine-tuning/checkpoint；PyTorch；Triton/FlashAttention CUDA；官方 Triton 内核要求 `q.is_cuda` | blocked：无 torch/CUDA/权重 |
| Infini-attention | paper + HF reproduction notes | not vendored as a result | compressive memory inside attention | requires training/continual pretraining to reproduce reported long-context results | reference only |
| Compressive Transformer | paper; small community PyTorch implementation exists | reference only | compressed recurrent memory | implementation and training protocol differ from LLM methods above | reference only |

## 官方入口摘录

AutoCompressor 的 README 明确要求 bfloat16 + CUDA + FlashAttention，并从 `princeton-nlp/AutoCompressor-Llama-2-7b-6k` 加载模型。ICAE 的 README 给出 Mistral-7B/Llama-2-7B 模型下载和 `fine_tuned_inference_script.sh`。Activation Beacon 示例要求 `model.cuda()` 和 `flash_attention_2`。Landmark 的 fused kernel 对输入执行 CUDA 断言，并且官方 LLaMA 示例需要 7B 权重。

这些条件决定了：在当前 Apple GPU 上用 Ollama 代替 checkpoint，不能称为这些方法的运行结果。

## 不能直接比较的项目

- 论文中的 LongBench、passkey、book summarization 和本项目的 60-fact benchmark 不是同一任务。
- 论文 checkpoint 通常经过压缩目标训练；未经训练的基础模型接入同一结构不构成公平复现。
- AutoCompressor/ICAE 的表示是模型输入侧的 soft representation，Activation Beacon/Landmark 主要操作每层 activation/KV；压缩率分母不同。
- latency 必须固定硬件、batch、prompt length、生成长度和 kernel；Python 原型时间不能代替 fused GPU kernel。

因此未来若获得 CUDA 环境，第一张表才会是“相同 benchmark 上的可运行结果”，第二张表才是“论文原始结果摘要”，两者不能混写。本轮 Phase 0 不执行这些运行，只记录代码入口和复现闸门；RCHAM 的机制边界见 `../design/novelty_boundary.md`。
