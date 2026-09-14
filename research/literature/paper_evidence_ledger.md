# RCHAM Phase 0.5：论文证据账本

审计日期：2026-09-15
审计方式：优先使用正式出版页面、ACL/NeurIPS/PMLR/OpenReview 的 version-of-record；arXiv 只作为版本和补充入口。官方代码必须由论文页、作者仓库或 README 的明确声明确认。`paper reports`、`code exists`、`independently reproduced` 三者分开记录。

## 版本和代码核对结果

| 工作 | version-of-record / DOI | arXiv | 官方代码核对 | 对 RCHAM 的结论 |
|---|---|---|---|---|
| Native Sparse Attention | [ACL 2025 Long Paper](https://aclanthology.org/2025.acl-long.1126/), DOI `10.18653/v1/2025.acl-long.1126`；ACL 页面明确标注 Best Paper | [2502.11089](https://arxiv.org/abs/2502.11089) | ACL 论文页和摘要没有作者代码链接；本轮未找到可确认的 author-linked official repo。GitHub 上的第三方实现不能标成官方代码。 | NSA 已有动态层级稀疏、压缩分支、选择分支和滑窗，但没有证据表明它实现 post-use utility promotion/demotion。 |
| RecMem | [Findings ACL 2026](https://aclanthology.org/2026.findings-acl.1619/), DOI `10.18653/v1/2026.findings-acl.1619` | [2605.16045](https://arxiv.org/abs/2605.16045) | [CaiusDai/RecMem](https://github.com/CaiusDai/RecMem) README 明确写明论文和 ACL 2026 Findings，并提供 `uv.lock`、评测入口和数据路径。 | 它通过语义 recurrence 决定何时 consolidation，是外部 agent memory 的“重复出现后巩固”工作；不是内部 Transformer/KV 的 tier promotion。 |
| HeteroCache | [ACL 2026 Long Paper](https://aclanthology.org/2026.acl-long.1999/), DOI `10.18653/v1/2026.acl-long.1999` | [2601.13684](https://arxiv.org/abs/2601.13684) | ACL 正式页明确给出 [ponytaill/HeteroCache](https://github.com/ponytaill/HeteroCache)。README 包含 head clustering、InfiniteBench/LongBench 和 latency 入口。 | 这是内部 KV 分层、attention drift 监测和异步冷读取的最近邻；公开描述没有显示“回答后 counterfactual utility 促升”。 |
| Landmark Attention | [NeurIPS 2023](https://papers.neurips.cc/paper_files/paper/2023/hash/ab05dc8bf36a9f66edbff6992ec86f56-Abstract-Conference.html), DOI `10.52202/075280-2378` | [2305.16300](https://arxiv.org/abs/2305.16300) | [epfml/landmark-attention](https://github.com/epfml/landmark-attention) README 明确称为论文实现，并含 frozen reproduction code 与 Triton/FlashAttention 路径。 | 已经解决第一次 query 的 landmark → raw block 路由；没有看到层级促升、utility 反馈或衰减生命周期。 |
| H²MT | 当前只能确认 [arXiv:2605.24930](https://arxiv.org/abs/2605.24930)，arXiv DOI `10.48550/arXiv.2605.24930`；本轮未找到正式会议 version-of-record | [2605.24930v2](https://arxiv.org/abs/2605.24930) | 本轮没有找到作者公开代码；代码索引页面显示 Request Code，不能当作官方实现。 | 已覆盖离线语义树、bottom-up embedding 和 coarse-to-fine route；是否有更细的 lifecycle 机制不能从摘要推断，当前不宣称有。 |
| R³Mem | [Findings ACL 2025](https://aclanthology.org/2025.findings-acl.235/), DOI `10.18653/v1/2025.findings-acl.235` | [2502.15957](https://arxiv.org/abs/2502.15957) | ACL 页没有官方代码链接；本轮未找到作者代码仓库。Papers With Code 也没有实现条目，不能把非作者仓库当官方。 | 已覆盖 reversible context compression、document/entity hierarchy 和 raw reconstruction；是外部 memory network，不是 post-use internal KV promotion。 |
| KVzip | [NeurIPS 2025 Oral](https://proceedings.neurips.cc/paper_files/paper/2025/hash/f4eaa4b8f2d08edb3f0af990d56134ea-Abstract-Conference.html), DOI `10.52202/085713-5585` | [2505.23416](https://arxiv.org/abs/2505.23416) | [snu-mllab/KVzip](https://github.com/snu-mllab/KVzip) README 标明 NeurIPS'25 Oral，含 CUDA 12.1、评测脚本和模型适配；NVIDIA kvpress 另有集成。 | 它用 context reconstruction 估计 query-agnostic eviction importance；这是写入/淘汰前的预测，不是某次未来 query 用完之后的 utility 反馈。 |
| MemoryBank | [AAAI 2024](https://ojs.aaai.org/index.php/AAAI/article/view/29946), DOI `10.1609/aaai.v38i17.29946` | [2305.10250](https://arxiv.org/abs/2305.10250) | [zhongwanjun/MemoryBank-SiliconFriend](https://github.com/zhongwanjun/MemoryBank-SiliconFriend) README 提供数据、memory bank 和 SiliconFriend 代码；评测含 ChatGPT 生成对话和人工 probing questions。 | 已有外部 memory 的时间衰减和 significance reinforcement；不是内部 attention/KV，且访问/重要性不等于 counterfactual utility。 |
| SF-AMS | 本轮未找到正式出版版本；arXiv DOI `10.48550/arXiv.2607.22562` | [2607.22562](https://arxiv.org/abs/2607.22562) | 本轮未找到作者公开代码或 version-of-record；只能作为 preprint evidence。 | 这是最近的 external utility-driven survival + hierarchy + temporal usage 工作，直接压缩了“utility + decay”创新空间，但摘要没有证明内部 Transformer/KV 闭环，也没有证明 gold counterfactual utility。 |

## 重新划分：第一次召回与重复使用

### A. First-time unexpected query

历史 `M` 从未被证明重要，第一次被未来 query 使用时，promotion 尚未发生。因此 RCHAM 不能提前帮助这一次。成功必须来自：

```text
compressed routing representation
+ cold/raw fallback
```

这部分已有 Landmark Attention、H²MT、HeteroCache 等相邻路线；RCHAM 的 Phase 1 必须把 first-time recall 单独报告。

### B. Recurrent / related future query

在第一次读取后，如果证据对 `q1` 的回答有 post-use utility，控制器才可以在 `t3` 更新 `M`：

```text
提高 retention
提高 representation precision
提高 cache tier
提高 attention accessibility
```

因此 promotion 只能改善 `q2/q3/...` 的保留和读取成本，不能改善 `q1` 的提前发现概率。

## 证据等级（paper-forensics）

- G0：本轮没有公开证据支持造假、篡改或抄袭。
- G1（中等）：多数数字依赖训练 checkpoint、硬件 kernel、数据生成方式、judge 和评测协议；H²MT/SF-AMS 仍是 preprint，代码状态不完整。
- G2–G4：本轮没有达到这些等级的证据。

## 对核心问题的回答

本轮没有在主来源中找到以下**内部 Transformer/KV 完整闭环**：

```text
first cold retrieval
→ post-use utility
→ promote precision/tier
→ later reuse
→ decay/demotion
```

但外部 agent memory 已经分别覆盖其中若干边：MemoryBank 的 decay/reinforcement、RecMem 的 recurrence-triggered consolidation、SF-AMS 的 utility-driven survival，R³Mem 的 reversible hierarchical retention；内部 cache/attention 工作已覆盖 Landmark 的 raw fallback、H²MT 的 coarse-to-fine hierarchy、HeteroCache 的 drift-triggered tier retrieval、KVzip 的 query-agnostic eviction。因而 RCHAM 的创新边界只能写成“内部 KV 生命周期 + post-use utility 的严格定义与预算匹配验证”，不能写成一般性的 memory promotion 新发现。

## Phase 0-B：生命周期近邻补充

本轮精读后，原先“没有观察后资源重分配”的说法需要收窄：

| 工作 | 新确认的覆盖 | 仍未覆盖的部分 |
|---|---|---|
| [EVICPRESS](https://arxiv.org/html/2512.14946) | context-level quality re-profile；按质量、TTFT、频率把 KV 在 GPU/CPU/SSD 间重新压缩、驱逐和放置；报告 H100/CPU/SSD I/O | 不是 exact token/block evidence identity；cache miss 主要 recompute，不是 q1 raw evidence fallback；没有明确 t7 decay；当前为 preprint，未核实官方代码 |
| [AdaptCache](https://arxiv.org/html/2509.00105) | 用历史频率和质量-延迟曲线做 context-level DRAM/SSD placement、压缩和 eviction | 预测/历史 utility，不是 q1 后 actual utility；无 evidence attribution、raw fallback 或显式 decay；未核实官方代码 |
| [IMPRESS](https://www.usenix.org/conference/fast25/presentation/chen-weijian-impress) | prefix KV 的重要性分数和 GPU/CPU/disk placement，并测 TTFT | 无 q1 后 utility、精确 evidence identity、promotion/decay 闭环；未核实作者代码 |
| [Strata](https://arxiv.org/html/2508.18572) | 层级 context cache、radix-tree、scheduler 和生产式 I/O/TTFT | 无 post-use utility 和 exact internal KV lifecycle；没有明确 decay；当前按 preprint 处理 |

因此当前准确表述是：**context-level serving system 的观察后重分配已经存在；token/block-level internal KV 的“冷读→证据归因→后续精度/层级改变→再利用→显式降级”仍未在本轮主来源中确认。** 这是“未确认完整重合”，不是“没人做过”。

另一个需要保留的负证据是 [RMM](https://arxiv.org/html/2607.24667)：它给出了 lagged demonstrated utility，但在自然文本/独立 streaming multi-turn 对照中 utility 退化为普通 attention，说明 post-use 信号不一定带来部署优势。
