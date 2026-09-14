# Phase 1：RCHAM 控制器模拟协议

状态：设计完成，等待 Phase 0 闸门；当前不执行。

## 目的

隔离“检索后被证明有用再促升”这一机制，不把结果混入具体 Transformer、CUDA kernel 或大模型训练。输入可以是冻结的 embedding/hidden representation；控制器维护不同分辨率和存储 tier。

## 因果顺序

```text
history write/compress（看不到未来 query）
→ future query arrives
→ routing and candidate retrieval
→ answer with/without evidence
→ observe utility
→ update promotion/demotion state
```

写入阶段不能读取未来问题、答案或 utility 标签。查询之后才允许计算 utility；测试集 query 不能提前参与压缩、阈值选择或数据生成。

## 基线

| ID | 控制器 | 说明 |
|---|---|---|
| A | Static | 固定 tier/固定压缩，不根据访问更新 |
| B | Recency | 最近写入或最近访问优先 |
| C | Retrieval-count | 被召回次数越多越升格，不检查是否有用 |
| D | Utility-conditioned | 召回后按 counterfactual utility 促升 |
| E | Utility + decay | D 加 age decay、cooldown、容量约束 |
| F | Oracle | 只作为上界，写入阶段知道未来有用性，不能当可部署方法 |

所有基线共享相同 representation、memory budget、retrieval budget、候选数和 raw archive。

## 数据设计

历史中加入未来重要性变化，而不是只放显眼 needle：

- 低频但后面关键的 rare fact；
- 同一实体的 state update；
- 否定和条件关系；
- 需要两个 block 的 cross-event relation；
- 写入时不重要、很久以后才相关的 delayed relevance；
- 会被频繁错误召回的 distractor，测试 retrieval-count 的正反馈。

可先使用确定性 synthetic history，再接 LongMemEval、RULER 或 BABILong（需核对许可证、版本和任务适配）。新数据必须保存生成 seed、事实表、future query split 和原始文本。

## Utility 定义

首选固定答案键的反事实差：

```text
u_i = loss(answer | evidence_i removed)
      - loss(answer | evidence_i present)
```

若模型不提供可靠 token loss，则使用：answer flip、evidence sufficiency、contradiction check 的固定组合。`retrieved` 只记录访问，不作为 utility。utility 预测器若在后续加入，必须与真实 post-use label 分开评估。

## 指标

- evidence recall / answer exact match；
- future-useful retention at equal budget；
- retrieved tokens、promoted/demoted count、tier occupancy；
- churn、promotion regret、utility precision/recall；
- controller latency、index/storage size、更新次数；
- 失败类别：未路由、压缩丢失、读取不足、回答器错误、utility 误判。

## 必须输出的图

1. memory budget vs future-useful retention；
2. retrieval budget vs evidence recall；
3. promotion precision/recall vs churn；
4. 时间轴上的 tier occupancy 和 delayed-relevance recall；
5. utility-conditioned 与 retrieval-count 的 paired per-query 差异。

## 复现与阶段闸门

固定至少 3 个 seed（Pilot 可先 1 个做 pipeline），保存 raw traces、配置、依赖、模型版本和失败样本。只有在 D/E 相对 A/B/C 的优势在匹配预算下重复出现，且控制成本不过高时，才进入 Phase 2。

直接停止或重设计的条件：无稳定 utility 优势；优势只来自更多 tokens；utility 需要泄漏未来 query；churn/容量垄断失控；flat retrieval 在相同预算下更好。
