# Paper integrity and reproducibility audit: long-context compression methods

审计日期：2026-09-14
领域：Computer Science / AI / ML
审计模式：Standard audit（公开论文、官方代码、公开复现记录和本机入口审计）

## Bottom line

- Integrity risk：Low for the public records checked
- Highest evidence grade：G1, confidence medium
- No G3/G4 finding：没有发现公开证据能支持 fabrication、falsification 或 plagiarism 的结论
- One-sentence conclusion：这些论文和代码是真实存在且技术路线彼此一致，但论文数字高度依赖专用 checkpoint、训练数据、硬件 kernel 和评测协议；不能把论文数字当作未经条件转换的可复现事实。

这里的 G1 主要表示可复现性和评测设计问题，不是对作者意图的判断。Infini-attention 的独立复现失败也只能说明跨实现可复现性存在风险，不能推出原论文造假。

## What I checked

- AutoCompressor EMNLP 2023 论文入口与官方 `princeton-nlp/AutoCompressors` 仓库；官方仓库 commit：`80352a4233c4a70504c75bf95c5f3e6d2533a863`
- ICAE ICLR 2024 论文与 `getao/icae` 官方仓库；commit：`469a46886a92dd5e76b2d12a8bac0fb7ed7d4cdd`
- Activation Beacon ICLR 2025 论文与 `FlagOpen/FlagEmbedding/research/Long_LLM/activation_beacon`；commit：`fd1a2bdf69488ffebe0327999d4400d8c8058a0b`
- Landmark Attention NeurIPS 2023 论文与 `epfml/landmark-attention`；commit：`d963e504fa2424687c6cbd412b54f1626e832292`
- Infini-attention 原论文与 Hugging Face 独立复现记录
- 本机环境、依赖声明、入口脚本和模型下载路径
- 官方代码的 Python 静态编译；没有下载权重，没有执行未经授权的大模型实验

主要一手链接：

- [AutoCompressor paper/repository](https://github.com/princeton-nlp/AutoCompressors)
- [ICAE paper/repository](https://github.com/getao/icae)
- [Activation Beacon paper](https://arxiv.org/abs/2401.03462) / [repository](https://github.com/FlagOpen/FlagEmbedding/tree/master/research/Long_LLM/activation_beacon)
- [Landmark Attention paper](https://arxiv.org/abs/2305.16300) / [repository](https://github.com/epfml/landmark-attention)
- [Infini-attention paper](https://arxiv.org/abs/2404.07143) / [independent reproduction record](https://github.com/huggingface/blog/blob/main/blog/infini-attention.md)

## Claim-to-evidence map

| Claim | Primary evidence | What it establishes | What it does not establish |
|---|---|---|---|
| AutoCompressor uses summary vectors and can recursively process segments | Official README and code | Public implementation and intended mechanism exist | That the released checkpoint works on our benchmark or Apple hardware |
| ICAE reports about 4x compression | ICLR paper, Sec. 3 | The paper reports 4x in its Llama setup | Lossless arbitrary-detail preservation; the paper also reports degradation as slots shrink |
| Activation Beacon compresses per-layer K/V activations and reports 2x speed / 8x KV reduction | Paper abstract and Sec. 4 | The claimed mechanism and reported measurement exist | Hardware-independent speed or zero-shot behavior without beacon training |
| Landmark Attention selects blocks through landmark scores | Paper abstract/Introduction and official code | Query-to-landmark block selection is the proposed mechanism | A complete multi-level hierarchy; the released implementation is block-level |
| Infini-attention scales with compressed memory | Original paper | The architecture and reported long-context tasks exist | Reliable reproduction under a different implementation or training recipe |

## Findings

### Finding 1 — G1 / medium: results are checkpoint- and training-dependent

Observation: ICAE pretrains on 1.6B Pile tokens, then uses a PLC instruction dataset; Activation Beacon trains compression behavior and samples compression ratios; Landmark fine-tunes a LLaMA model with landmark tokens. The released inference code therefore represents trained systems, not plug-in algorithms that can be applied to an arbitrary local model.

Why it matters: Comparing these methods against our Ollama model, or against an untrained implementation, would confound architecture with checkpoint training.

Benign explanation: This is normal for learned compression methods and is disclosed in the papers.

Decisive next evidence: Run each official checkpoint with its own required tokenizer and model class, then run a separately defined adapted track on one common base model.

### Finding 2 — G1 / medium: evaluation protocols are not interchangeable

Observation: Activation Beacon reports LongBench, NIAH and latency under Llama/Qwen-specific ratios; Landmark reports pass-phrase retrieval and language-modeling/fine-tuning settings; ICAE reports autoencoding and instruction-following comparisons. The denominators, context lengths, training data, and output judges differ.

Why it matters: A paper table such as “8x compression” cannot be copied as the same metric for ICAE slots, Activation Beacon KV activations and Landmark stored blocks.

Benign explanation: Each method measures the resource it actually compresses.

Decisive next evidence: Use one fixed benchmark and report separate representation units: input tokens, soft slots, KV entries, retrieved block tokens, peak bytes and wall-clock latency.

### Finding 3 — G1 / medium: synthetic or model-judged evaluation needs independent checks

Observation: Activation Beacon documents synthetic QA data produced with GPT-3.5 and says its Needle-in-a-Haystack accuracy is estimated by ChatGPT. ICAE’s PLC data uses GPT-4 to generate prompt-answer pairs and its evaluation includes model-based comparisons.

Why it matters: Generated labels and model judges can create leakage, judge preference, or answer-format effects. This does not invalidate the papers, but it means exact-match ground truth should be added for our benchmark.

Decisive next evidence: Use hand-checkable facts, fixed answer keys, multiple seeds, raw predictions, and a judge-free exact-match metric before using any LLM judge.

### Finding 4 — G1 / medium: independent Infini-attention reproduction is a real reproducibility warning

Observation: Hugging Face reports spending most of its effort debugging convergence and concludes that performance worsens as memory is compressed repeatedly; it does not present this as proof the original paper fabricated results.

Why it matters: Long-context memory methods may be unusually sensitive to optimizer, gating, initialization, segmentation and training schedule.

Benign explanation: The reproduction used a different model and training stack, and the authors explicitly describe it as an early reproduction record.

Decisive next evidence: Reproduce at the smallest model with identical initialization/optimizer/checkpoint protocol, then scale only after the baseline and modified model converge.

### Finding 5 — G0 for misconduct / medium: code and paper provenance are publicly consistent

Observation: Each checked method has a named paper, an official or author-linked repository, and code paths matching the claimed mechanism. Static compilation of the cloned code completed; no nonexistent citation or impossible arithmetic was found in this audit.

Limitations: Static compilation is not a performance reproduction. We did not audit every figure source, every seed, private training log, or raw benchmark prediction file.

## AI/ML-specific checks

- Test leakage: our Phase 1 compressor prompt is question-blind; a direct string search found no benchmark question text inside the 10 compression prompts.
- Seed selection: our pilot uses a fixed seed and preserves raw outputs; the papers’ full per-seed logs were not available in the public artifacts checked.
- Hardware parity: current Apple M5 cannot execute the CUDA/Triton paths; no latency comparison was claimed.
- Checkpoint identity: official repository commits are recorded, but no model weights were downloaded; no checkpoint hash can therefore be verified yet.
- Benchmark contamination: the current synthetic benchmark is newly generated and has no public pretraining corpus, but it is too small and templated to establish general long-context ability.
- Ablation integrity: paper-level ablation tables were not recomputed from raw predictions in this audit; treat them as reported claims until official prediction files and exact evaluation scripts are run.

## Missing evidence / limitations

The decisive missing artifacts are CUDA hardware access, exact model-weight hashes, full environment lockfiles, per-seed predictions, raw latency/memory logs, and the precise evaluation scripts/data splits used for every paper table. Their absence is a reproducibility limitation, not evidence of misconduct.

## Recommended next actions

1. Do not download 7B checkpoints on the current machine yet.
2. Obtain a CUDA environment and record `nvidia-smi`, driver, CUDA, PyTorch, Transformers, FlashAttention/Triton versions.
3. Run an official-checkpoint track first, one method at a time, on the fixed Phase 1 benchmark.
4. Add exact-match retrieval, evidence recall, per-question latency, peak memory and KV bytes; keep paper-native metrics in a separate table.
5. Only after those runs work, implement a common-base adapted track and compare the proposed coarse-to-fine hierarchy against flat block routing.
