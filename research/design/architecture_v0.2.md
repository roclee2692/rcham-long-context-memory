# RCHAM 架构草案 v0.2

## 目标

在不让写入过程看到未来 query 的前提下，让历史信息可以先压缩，后来若被证明有用就升格，长期不用再降级。这个草案是可测试的机制说明，不是已经完成的 Transformer 实现。

## 四层记忆

```text
Tier 0  当前局部 attention：正在处理的 token / 最近窗口
Tier 1  高分辨率历史：近期或最近被证明有用的 block/KV
Tier 2  压缩历史：content + routing representation 与 child pointers
Tier 3  冷存储：不可变 raw text/KV archive 和低成本索引
```

每个 block 至少保存：

- `content_repr`：表达内容，服务摘要或粗粒度理解；
- `routing_repr`：表达未来 query 可能通过什么线索命中该 block；
- `children`：指向更细一层；
- `raw_pointer`：指向原始 token/KV，不因降级而删除；
- `utility_posterior`：曾经被证明有用的证据及不确定性；
- `age/last_access/tier`：衰减和容量控制所需的状态。

`content_repr` 和 `routing_repr` 可以共享底层编码器，但在实验中必须允许分离，以免“能概括”被误当成“能导航”。

## 信息流

### 写入

```text
local attention
→ block representation
→ content/routing encoding
→ 根据预算进入 Tier 1/2
→ raw_pointer 写入 Tier 3
```

写入和压缩不能访问未来 query、未来答案或未来 utility 标签。重要性先验只能来自当前可见上下文和明确记录的在线信号。

### 读取与反馈

```text
query
→ Tier 2/1 routing
→ coarse-to-fine child traversal
→ 读取 raw/high-resolution evidence
→ 回答或继续 attention
→ 计算 utility
→ promote / keep / demote
```

`retrieved == useful` 不成立。建议的首个可操作 utility 是：

```text
u = loss(answer | evidence removed) - loss(answer | evidence present)
```

在没有可靠 loss 时，用固定答案键上的 answer flip、evidence sufficiency 和 contradiction 检查组成离散标签。utility 需要置信度和 shrinkage，避免一次偶然命中永久升格。

## 更新规则（概念）

- `PROMOTE`：utility 后验超过阈值，且在 cooldown 后没有违反容量预算；把 block 提到更高精度 tier 或增加访问优先级。
- `KEEP`：证据支持不足但不确定性高时保留现状，不因一次失败立即删除。
- `DEMOTE`：年龄增加、utility 后验下降或预算压力增大时降级到更粗 representation；raw archive 仍可回退。
- `DECAY`：长时间没有有用访问时降低 promotion score；读取本身不自动加分。
- `COOLDOWN`：升格后设置冷却期，防止同一查询循环制造正反馈。

一种待验证的分数形式：

```text
score_i(t+1) = decay(age_i) * score_i(t)
                  + alpha * posterior_utility_i
                  - beta * storage_cost_i
```

这不是最终学习规则，也不预设可微性；Phase 1 先用可解释控制器隔离机制是否有效。

## 不承诺的事情

- 不承诺固定 O(n)；层级维护、候选读取和 utility 评估可能增加成本。
- 不承诺高层摘要保留所有细节；raw fallback 是可恢复性机制，不是无损压缩证明。
- 不承诺一次召回就永久巩固；反馈必须经过 utility 评估、置信度和容量约束。
- 不把外部 RAG 控制器结果直接写成内部 Transformer attention 结果。
