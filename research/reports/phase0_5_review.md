# Phase 0.5 Review：Literature Normalization + Experimental Semantics Freeze

日期：2026-09-15  
状态：完成；按要求 STOP。没有训练模型，没有启动正式 Phase 1。

## 1. 本轮做了什么

- 用正式出版页面核对 closest work 的 venue、version-of-record、DOI 和代码状态。
- 将 arXiv 版本保留为补充入口；有正式出版版本时，矩阵以正式版本为主。
- 对 Native Sparse Attention、RecMem、HeteroCache 重新锁定正式记录。
- 对 Landmark Attention、H²MT、HeteroCache、R³Mem、KVzip、MemoryBank 和 SF-AMS 分别记录机制覆盖范围与未覆盖范围。
- 把 `first-time unexpected query` 与 `recurrent/related future query` 从一个含糊的“future-query-unknown”假设拆成两个实验阶段。
- 冻结 Phase 1 的时间线、两个新 baseline、Oracle utility 与 deployable utility proxy 的边界。

## 2. 文献核对结果

### Native Sparse Attention

正式来源是 ACL 2025 Long Paper，ACL Anthology ID `2025.acl-long.1126`，DOI `10.18653/v1/2025.acl-long.1126`，正式页面明确标注 `Best Paper`：[ACL version-of-record](https://aclanthology.org/2025.acl-long.1126/)。arXiv 版本是 [2502.11089](https://arxiv.org/abs/2502.11089)。

论文摘要明确描述 dynamic hierarchical sparse strategy、coarse-grained token compression 和 fine-grained token selection。它属于 natively trained sparse attention，不等于 RCHAM 的 memory lifecycle。ACL 正式页没有链接作者官方代码；本轮发现的是第三方实现，不能把它们写成 official code。矩阵已修正为“author-linked official repo not identified; third-party implementations exist”。

### RecMem

正式来源是 Findings of ACL 2026，ACL Anthology ID `2026.findings-acl.1619`，DOI `10.18653/v1/2026.findings-acl.1619`：[ACL version-of-record](https://aclanthology.org/2026.findings-acl.1619/)。arXiv 版本是 [2605.16045](https://arxiv.org/abs/2605.16045)。官方仓库是 [CaiusDai/RecMem](https://github.com/CaiusDai/RecMem)，README 明确说明论文已接收 ACL 2026 Findings，并给出 `uv.lock`、评测入口和数据路径。

RecMem 的机制是把 incoming interactions 放到 subconscious memory，用轻量 embedding 检索，在 sustained recurrence 后才调用 LLM 做 episodic/semantic consolidation，并做 semantic refinement。它是 external agent memory 的 recurrence-triggered consolidation，不是内部 Transformer/KV 的 q1 utility → cache-tier promotion。

### HeteroCache

正式来源是 ACL 2026 Long Paper，ACL Anthology ID `2026.acl-long.1999`，DOI `10.18653/v1/2026.acl-long.1999`：[ACL version-of-record](https://aclanthology.org/2026.acl-long.1999/)。arXiv 版本是 [2601.13684](https://arxiv.org/abs/2601.13684)。ACL 正式页明确链接官方仓库 [ponytaill/HeteroCache](https://github.com/ponytaill/HeteroCache)。

HeteroCache 已经覆盖 heterogeneous KV budget、代表 head 监测 attention drift、hierarchical storage 和 asynchronous on-demand retrieval；README 给出 clustering、InfiniteBench、LongBench 和 latency 入口。公开摘要和入口没有显示“q1 读完后，用 counterfactual utility 促升该 block 的精度/tier”，所以它是最近的内部 KV retrieval baseline，但当前不判定它已覆盖 RCHAM 完整闭环。

### 其他最近邻

- [Landmark Attention](https://papers.neurips.cc/paper_files/paper/2023/hash/ab05dc8bf36a9f66edbff6992ec86f56-Abstract-Conference.html)，DOI `10.52202/075280-2378`，有 [官方代码](https://github.com/epfml/landmark-attention)：解决 landmark → raw block 的第一次随机访问。
- [H²MT](https://arxiv.org/abs/2605.24930)：目前只确认 arXiv v2 和 DOI `10.48550/arXiv.2605.24930`，没有确认正式 venue 或作者官方代码；已覆盖语义层级和 coarse-to-fine route。
- [R³Mem](https://aclanthology.org/2025.findings-acl.235/)，DOI `10.18653/v1/2025.findings-acl.235`：覆盖 reversible hierarchical retention/reconstruction，但没有确认作者官方代码，且是外部 memory network。
- [KVzip](https://proceedings.neurips.cc/paper_files/paper/2025/hash/f4eaa4b8f2d08edb3f0af990d56134ea-Abstract-Conference.html)，DOI `10.52202/085713-5585`，有 [官方代码](https://github.com/snu-mllab/KVzip)：用 reconstruction importance 做 query-agnostic eviction；这是使用前的 eviction 重要性，不是使用后的 utility。
- [MemoryBank](https://ojs.aaai.org/index.php/AAAI/article/view/29946)，DOI `10.1609/aaai.v38i17.29946`，有 [官方代码](https://github.com/zhongwanjun/MemoryBank-SiliconFriend)：已有时间衰减和 significance reinforcement，但属于 external memory。
- [SF-AMS](https://arxiv.org/abs/2607.22562)：只有 arXiv preprint 和 DOI `10.48550/arXiv.2607.22562`，没有确认正式出版或官方代码。它是最近最接近的 external utility-driven survival + hierarchy 工作，直接提醒我们不能把 utility + decay 当作一般新思想；但它没有被确认是内部 Transformer/KV 闭环，也没有证明 gold counterfactual utility。

## 3. RCHAM 能解决什么、不能解决什么

### A. First-time unexpected query

```text
t0: M 写入，未来 q 不可见
t1: 其他 history 持续写入，M 被压缩/降级
t2: q1 第一次需要 M
```

此时 M 没有 post-use evidence，所以 promotion 尚未发生。RCHAM 不能提前帮助 q1。q1 的成功必须来自：

```text
compressed routing representation + cold/raw fallback
```

这一部分单独测 first-time evidence recall、answer accuracy、cold访问成本。q1 是失败也不说明 promotion 失败，可能是 routing/raw fallback 失败。

### B. Recurrent / related future query

```text
t3: q1 用到 M，系统评估 M 的 post-use utility
t4: 继续写入，产生真实 memory pressure
t5: q2/q3 再次需要 M 或相关证据
```

只有从 t3 开始，promotion 才能提高 M 的 retention、representation precision、cache tier 或 attention accessibility。因此 promotion 的被测对象是 q2/q3 的保留和成本，而不是 q1 的发现。

## 4. Phase 1 语义冻结

新增两个 baseline：

1. **Cold-Raw-Fallback Only**：每次都重新从 cold/raw archive 找，永不促升。它回答 promotion 相比“每次冷检索”节约了什么。
2. **Perfect-Routing + No-Promotion**：假设每次 routing 都完美，但永不促升。它拆开 routing improvement 和 memory lifecycle improvement。

强制 episode 不能只查询一次 M。没有 q2/q3 的 episode 不进入 promotion 主统计。

## 5. Utility 定义

### Oracle utility

```text
u_oracle(M, q1)
  = loss(answer | M removed) - loss(answer | M present)
```

也可以用固定答案键上的 answer flip 作为离散版本。Oracle 只验证“理想 utility 信号是否值得促升”，不能描述成部署算法。

### Deployable utility proxy

Phase 1 暂时只冻结接口，不声称解决。后续候选包括 model confidence change、self-consistency、attention contribution、reward model、prediction-loss proxy 和 learned utility predictor。每个 proxy 都要与 oracle 分开评估精度、校准和成本。

## 6. 对五个问题的明确回答

1. **真正研究什么？** 两者都研究，但分层：q1 是 first-time cold retrieval；核心贡献候选是 q1 后的 repeated-use retention/lifecycle。不能把它们合并成一个 recall 数字。
2. **Promotion 能改善什么？** 只能改善已经暴露价值后的 q2/q3/...：存活、tier、精度、访问成本和后续回答。不能改善 q1 的提前发现。
3. **Oracle 有效后，deployable predictor 是否独立问题？** 是。Oracle 只是机制上界；如何在没有 gold answer 的线上读取后估计 utility，是独立研究问题。
4. **最近论文有没有做完整内部闭环？** 本轮锁定的 primary sources 没有确认一个同时完成 `first cold retrieval → post-use utility → promote precision/tier → later reuse → decay/demotion` 的内部 Transformer/KV 闭环。外部 agent memory 和内部 KV 工作已经分别覆盖许多子环节，所以结论是“未确认完整重合”，不是“无人做过”。
5. **新的最小 novelty statement？**

   > 在固定 memory/retrieval budget 和未来 query 未知的时间序列中，第一次需求由 cold/raw fallback 处理；在读取之后，用可记录的 post-use utility 更新内部 KV/attention memory 等级，并在真实 memory pressure 下测量后续相关 query 的 retention、evidence recall、answer accuracy 和访问成本。

## 7. STOP 闸门

Phase 0.5 已完成。当前不训练模型、不启动正式 Phase 1、不下载新权重、不使用收费 API。下一步只有在用户确认并检查本报告、矩阵和协议后，才进入控制器模拟设计实现。
