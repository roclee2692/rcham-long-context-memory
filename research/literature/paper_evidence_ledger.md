# RCHAM Phase 0：论文证据账本

审计日期：2026-09-14  
方法：只把公开的一手论文、作者仓库和明确的独立复现记录作为证据。`paper reports` 不等于 `independently reproduced`，代码存在也不等于在本机可运行。

## 结论

本轮没有找到一篇公开工作明确同时实现以下完整闭环：

```text
未来 query 未知的写入
→ 多层压缩与分层存储
→ query 逐层粗到细定位并回到原文/KV
→ 召回后用 counterfactual utility 判断“真的有用”
→ utility-conditioned promotion
→ 长期不用 demotion/decay
→ 内部 Transformer/KV 生命周期
```

这是一个**暂定边界**，不是“无人做过”的证明。H²MT 已经非常接近层级语义索引和 coarse-to-fine 路由；HeteroCache 已经接近动态 KV 分层和按需读取；R³Mem、RecMem 和 MemoryBank 已经覆盖外部记忆中的保留、检索、巩固或遗忘。RCHAM 的可辩护差异只能是“反馈信号的定义、更新时机和内部 KV 生命周期的组合”，不能把压缩、层级或召回本身写成创新。

## 逐项证据

| 公开工作 | 已经建立的事实 | 本项目不能据此声称 | 对 RCHAM 的直接启示 |
|---|---|---|---|
| [Compressive Transformer](https://arxiv.org/abs/1911.05507) | 近期记忆与压缩旧记忆并存；压缩历史可继续参与语言建模。 | “压缩历史”是新机制。 | 要把不可逆压缩和可恢复原文分开记录。 |
| [Landmark Attention](https://arxiv.org/abs/2305.16300) / [代码](https://github.com/epfml/landmark-attention) | query 先与 landmark 比较，再取相关历史 block；原始 block 可回退。 | “小表示导航原文”是新机制。 | 它是 RCHAM 的内部 raw-fallback 基线；公开实现没有核对到完整层级 promotion/demotion。 |
| [Gist Tokens](https://proceedings.neurips.cc/paper_files/paper/2023/hash/3d77c6dcc7f143aa2154e7f4d5e22d68-Abstract-Conference.html) / [代码](https://github.com/jayelm/gisting) | 通过特殊 token 压缩 prompt，并报告最高约 26x prompt compression。 | prompt compression 或 gist 表示本身是新机制。 | 需要用相同预算比较存储成本和答案质量。 |
| [AutoCompressor](https://arxiv.org/abs/2305.14788) / [代码](https://github.com/princeton-nlp/AutoCompressors) | summary vectors 可递归传给后续模型。 | summary vectors 或递归压缩本身是新机制。 | 其 checkpoint/training dependence 必须在复现报告中单列。 |
| [ICAE](https://arxiv.org/abs/2307.06945) / [代码](https://github.com/getao/icae) | memory slots 可压缩上下文；论文报告 memory size 变小会明显伤害重建和任务表现。 | 高倍率压缩无损。 | 未来重要性未知是压缩的核心风险，而不是附带问题。 |
| [Infini-attention](https://arxiv.org/abs/2404.07143) / [独立复现](https://github.com/huggingface/blog/blob/main/blog/infini-attention.md) | 局部 attention 与压缩长期 memory 可放入同一 block；论文报告超长 passkey/摘要实验。 | 论文表中的长上下文数字已被普遍复现。 | HF 的独立复现显示收敛和重复压缩敏感，必须保留 reproduction warning。 |
| [HMT](https://arxiv.org/abs/2405.06067) / [代码](https://github.com/OswaldHe/HMT-pytorch) | 学习式 memory recurrence 和层级记忆可以支持长上下文。 | recurrence + hierarchy 是新机制。 | 需要控制器实验拆出 utility 反馈的增量贡献。 |
| [R³Mem](https://aclanthology.org/2025.findings-acl.235.pdf) | reversible compression、hierarchical compression、virtual memory tokens 与原文重建组合在外部 memory network 中。 | “可逆压缩 + 层级记忆”是新机制。 | 它是 retention/retrieval 组合的最近外部工作；需明确 RCHAM 的内部 KV 和 post-use utility 差异。 |
| [Activation Beacon](https://arxiv.org/abs/2401.03462) / [代码](https://github.com/FlagOpen/FlagEmbedding/tree/master/research/Long_LLM/activation_beacon) | 渐进压缩每层 K/V，论文报告约 8x KV 降低和约 2x 推理加速。 | 8x KV 压缩或 activation compression 本身是新机制。 | 纸面 latency 依赖训练、硬件、kernel 与 ratio；不能直接移植成 Apple 结果。 |
| [HeteroCache](https://arxiv.org/abs/2601.13684) | training-free heterogeneous KV budget、分层存储、attention drift 触发异步按需读取，论文报告 224K 上下文最高约 3x decoding acceleration。 | 动态 KV 分层和按需历史读取是新机制。 | 它是内部 storage/retrieval 最近邻；需要核对是否存在“召回后 utility 证据驱动促升”。摘要未显示该闭环。 |
| [H²MT](https://arxiv.org/abs/2605.24930) | 离线语义层级、bottom-up memory embedding、推理时 coarse-to-fine pruning；报告 LongBench 和技术文档效率结果。 | 层级语义树和粗到细路由是新机制。 | 它是 RCHAM 最接近的 hierarchy baseline；目前公开摘要没有显示 post-retrieval utility-conditioned KV lifecycle。 |
| [RecMem](https://arxiv.org/abs/2605.16045) / [代码](https://github.com/CaiusDai/RecMem) | 长运行 agent 的 recurrence-based memory consolidation、语义重复触发的巩固和细节恢复。 | “被重复使用就巩固”在 agent memory 中是新机制。 | 作为外部 agent memory 对照，不能直接等同内部 attention。 |
| [MemoryBank](https://arxiv.org/abs/2305.10250) | 外部记忆按时间和重要性使用 Ebbinghaus 式遗忘/强化。 | 时间衰减或记忆强化本身是新机制。 | RCHAM 应测试真实 utility，而不是把访问次数当作 usefulness。 |
| [KVzip](https://arxiv.org/abs/2505.23416) | query-agnostic KV eviction 以 context reconstruction 重要性压缩缓存，论文报告 3–4x cache reduction 和约 2x decoding latency reduction。 | query-agnostic eviction 或 context reconstruction objective 本身是新机制。 | 它提醒我们区分“写入前预测重要”与“回读后证明有用”。 |

## 论文报告与独立证据的分离

- Activation Beacon、ICAE、AutoCompressor 和 Gist Tokens 都是训练过的系统；其数字不能被当作任意基础模型上的 plug-in 结果。
- 论文使用的 LongBench、NIAH、合成 QA、模型评审和原生 compression ratio 不同，不能把 `8x KV`、`4x slots` 和 `26x prompt` 放在一个未经换算的排行榜里。
- Activation Beacon 的 NIAH 评测使用 ChatGPT 判断；ICAE 的 PLC 训练数据使用 GPT-4 生成。RCHAM benchmark 必须优先采用固定答案和证据位置。
- Hugging Face 的 [Infini-attention 独立记录](https://github.com/huggingface/blog/blob/main/blog/infini-attention.md) 报告了收敛调试和重复压缩导致的记忆退化。这是可复现性警告，不是对原论文诚信的判断。

## 证据等级（paper-forensics）

- G0：本轮未见公开证据支持造假、篡改或抄袭。
- G1（中等）：可复现性、checkpoint 依赖、硬件/评测协议和模型评审存在已记录限制。
- G2–G4：本轮没有达到这些等级的证据。

## 仍缺的证据

H²MT、HeteroCache 的完整代码和训练/推理配置仍需单独核对；SF-AMS、WhenLoss、MARCH、CueMem、Dynamic Hierarchical Sparse Attention 等名字没有在本轮主来源中全部确认，不能先写成已存在的同类工作。下一阶段如要引用，必须补论文 DOI/arXiv、代码 commit、数据和运行入口。
