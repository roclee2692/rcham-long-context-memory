# Phase 0 复现警告

## 当前环境闸门

- macOS 26.6.2 arm64，Apple M5，10 logical CPUs，16 GiB unified memory。
- 当前环境没有 CUDA/NVIDIA、PyTorch、Transformers、Triton 或 FlashAttention。
- 官方仓库已经做静态入口审计并记录 commit，但没有下载 7B 权重，也没有声称获得 latency、显存或 LongBench 结果。
- 历史 Pilot 使用本机已有 Ollama 模型；Phase 0 不启动新模型。结束检查应保持 `ollama ps`、`pgrep -af llama-server` 为空，避免后台占用内存。

## 不能直接横向比较的东西

1. 论文中的 compression ratio 可能分别指 input token、soft memory slot、KV entry、retrieved block token 或 peak bytes；报告时必须拆列。
2. Activation Beacon 的 speed/KV 数字依赖训练过的压缩行为、模型、kernel 和硬件；不能拿 CPU/Apple 运行时间替代。
3. Landmark 的 block recall、ICAE 的重建 BLEU、Gist 的 prompt task score、H²MT 的 TTFT 并不是同一个指标。
4. 论文使用的 checkpoint、数据生成器、judge 和上下文长度不同。对比必须固定预算、问题、候选集合和答案键。

## 数据与评审风险

- 未来 query 泄漏进摘要或写入 prompt，会把“未知未来”假设破坏掉。
- 合成 QA 或 LLM judge 可能偏好格式；首要指标应是 ground-truth evidence recall、answer exact match 和 counterfactual utility。
- needle 任务容易让问题显得过于明显；Phase 1 必须加入状态变化、否定、条件、跨事件和延迟相关。

## 代码、权重和版本风险

- 官方仓库有代码不代表发布了对应 checkpoint 或完整训练脚本。
- 依赖版本、FlashAttention/Triton kernel、GPU 型号和 batch/sequence 配置都会影响 latency。
- 所有复现要记录 paper version、repo commit、model hash、tokenizer、CUDA/driver/PyTorch/Transformers 版本、seed、原始 stdout/stderr 和峰值显存。

## 不应过度解释的结果

- “检索到”不等于“检索有用”。RCHAM 必须用去掉该证据后的 answer flip 或 loss difference 估计 utility。
- “访问次数多”不等于“重要”。频繁误召回会制造正反馈，必须与 utility-conditioned baseline 分开。
- “层级树更少比较”不等于 recall 更高。路由成本、层级维护和错误传播必须单独统计。
- Independent reproduction 失败是方法敏感性证据，不是原论文造假证据。

## 未确认候选

SF-AMS、WhenLoss、MARCH、CueMem、Dynamic Hierarchical Sparse Attention 和若干 2026 learned KV policy 的公开主来源尚未在本轮固定。它们在获得一手论文、版本、代码和实验配置前，只能放在待核查列表，不能用来支持“已有完全重合”的结论。
