# Phase 1：RCHAM 时间序列控制器模拟协议

状态：语义已冻结，等待 Phase 0.5 人工检查；当前不执行。

## 研究对象

Phase 1 不训练 Transformer，也不测 CUDA kernel。只使用冻结的 embedding/hidden representation、memory tiers、routing 和一个可解释 controller，回答：

> 在第一次需求由 cold/raw fallback 解决以后，post-use utility promotion 是否能在后续 memory pressure 下改善重复/相关 query？

## 强制 episode 时间线

每个 episode 至少包含一个真正的后续 query：

```text
t0: 写入 memory M；未来 query 不可见
t1: 写入大量其他 history，M 进入 compressed/cold tier
t2: q1 第一次需要 M；只允许 normal retrieval / cold/raw fallback
t3: 计算 M 对 q1 的 post-use utility；controller 更新 promote/keep/demote
t4: 继续写入大量 history，产生真实 memory pressure
t5: q2/q3 再次需要 M 或语义相关证据
     测 M 是否存活、所在 tier、召回成本、answer accuracy、evidence recall
```

如果一个 memory 在整个 episode 只被查询一次，只能用于 first-time recall，不能用来证明 promotion 有价值。`q1` 评估和 `q2/q3` 评估必须分开统计。

## 因果和信息隔离

```text
history write/compress（看不到未来 query、future answer、future utility）
→ q1 arrives
→ compressed routing + cold/raw fallback
→ answer with/without M
→ observe utility
→ update tier/promotion
→ memory pressure
→ q2/q3
```

写入、压缩、阈值选择和索引构建不能读取测试 query。只有 q1 回答完成后，才允许计算 M 的 utility。训练/调参和测试必须按完整 episode 切分，不能把同一 memory 的 q2 线索泄漏到 q1 写入。

## Baselines

| ID | 控制器 | 作用 |
|---|---|---|
| A | Static | 固定 tier/固定压缩，不根据访问更新 |
| B | Recency | 最近写入或最近访问优先 |
| C | Retrieval-count | 被召回次数越多越升格，不检查是否有用 |
| D | Utility-conditioned promotion | q1 之后按 utility 促升 |
| E | Utility + decay | D 加 age decay、cooldown 和容量约束 |
| F | Oracle | 写入阶段知道未来有用性，只作上界，不能称为部署算法 |
| G | Cold-Raw-Fallback Only | 每次都从 cold/raw archive 重新找，不促升；测 promotion 到底节约什么 |
| H | Perfect-Routing + No-Promotion | 假设每次 routing 都完美，但永不促升；拆分 routing 改善与 lifecycle 改善 |

A–E、G–H 必须共享同一 representation、memory budget、retrieval budget、候选数和 raw archive。F 只允许用于上界曲线。

## First-time 与 repeated-use 指标

### q1（首次需求）

- cold/raw evidence recall；
- q1 answer exact match；
- first-time retrieved tokens、cold I/O 或索引访问；
- q1 route failure / compression miss / answerer failure 分类。

### q2/q3（促升后的后续需求）

- M 是否仍存活；
- M 所在 tier 和 representation precision；
- evidence recall、answer exact match；
- retrieved tokens、访问延迟、cold fallback 次数；
- future-useful retention at equal budget。

只在 q2/q3 汇总 promotion effect；不能用 q1 的 recall 代替。

## Utility 两层定义

### Oracle Utility

允许 gold answer 或 counterfactual loss：

```text
u_oracle(M, q1)
  = loss(answer | M removed)
  - loss(answer | M present)
```

也可以使用固定答案键上的 answer flip 作为离散替代。Oracle 的目的只是判断“理想 post-use utility 是否值得促升”，不能被描述成可部署算法。

### Deployable Utility Proxy

Phase 1 只冻结接口，不假装已经解决。候选后续信号包括：model confidence change、self-consistency、attention contribution、reward model、prediction-loss proxy、learned utility predictor。每一种 proxy 都必须与 oracle utility 单独比较 precision、recall、calibration 和成本。

`retrieved` 只表示访问，`retrieved == useful` 禁止作为标签。一次误召回不能自动增加 promotion score。

## 数据设计

每个 episode 至少包含：

- q1 前未知、q2 后重复使用的 rare fact；
- entity state update；
- 否定和条件关系；
- 跨 block/cross-event relation；
- 延迟相关（delayed relevance）；
- 高频错误召回 distractor，测试 retrieval-count 的正反馈；
- 在 t4 压力阶段足够多的无关 history，使 tier 竞争真实发生。

先用确定性 synthetic episodes，再考虑 LongMemEval、RULER 或 BABILong；每个数据集先核对许可证、版本、任务是否真的支持时间序列 utility。保存 seed、事实表、q1/q2 split、原始 history 和 future-use labels。

## 指标

- q1 first-time evidence recall / answer accuracy；
- q2/q3 future-useful retention / evidence recall / answer accuracy；
- retrieved tokens、cold fallback count、promotion/demotion count；
- tier occupancy、precision、representation size；
- churn、promotion regret、utility precision/recall、calibration；
- controller latency、index/storage size、utility calculation cost；
- 失败类别：未路由、压缩丢失、冷读取失败、回答器错误、utility 误判、容量挤占。

## 必须输出的图

1. q1 与 q2/q3 分开的 memory budget vs recall/accuracy；
2. promotion 后 tier occupancy 的时间线；
3. q2/q3 future-useful retention vs promotion policy；
4. promotion precision/recall vs churn；
5. cold-fallback-only 与 utility promotion 的 retrieved tokens/latency 差异；
6. perfect-routing/no-promotion 与 utility promotion 的 paired per-episode 差异。

## 复现与阶段闸门

Pilot 只能先验证 pipeline；正式 Phase 1 至少使用 3 个 seeds，保存 q1/q2 raw traces、配置、依赖、版本、失败样本和自动统计脚本。只有当 D/E 相对 A/B/C/G/H 在匹配预算下稳定改善 q2/q3，并且 utility 计算成本不过高，才允许 Phase 2。

直接停止或重设计：没有 q2/q3；utility 泄漏未来 query；promotion 只改善 q1；优势只来自更多存储/读取；churn 或容量垄断失控；perfect-routing/no-promotion 已同样好；flat/cold retrieval 在相同预算下更好。
