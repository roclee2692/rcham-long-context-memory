# RCHAM 可证伪假设（Phase 0.5 冻结版）

## H0：第一次召回和后续保留是两个实验问题

`q1` 到来前，M 没有 post-use evidence；promotion 不可能改善 `q1` 的先验发现。第一次只评估 cold/raw fallback 的 evidence recall、answer accuracy 和访问成本。

`q1` 之后，M 才有 utility evidence；随后 memory pressure 和 `q2/q3/...` 才能评估 promotion 的保留收益。

**反证：**若实验没有 q1 后的压力区间和后续 query，则它不能支持 promotion 假设，只能报告 first-time recall。

## H1：post-use utility 促升改善后续保留

在固定 memory budget、retrieval budget、candidate 数、representation 和回答模型下，utility-conditioned promotion 在 q2/q3 的 future-useful retention 高于 static、recency、retrieval-count 和 cold-fallback-only。

**反证：**utility 方法不高于最强非 utility baseline，或优势只出现在 q1、更多存储或更多读取的情况下。

## H2：promotion 改变的是资源等级，不是第一次路由

第一次 query 的 recall 由 compressed routing + cold/raw fallback 决定；promotion 只应改变 M 在 q2/q3 时的 tier、精度、访问 token 和 latency。

**反证：**方法在 q1 就声称因 promotion 获得优势，或没有记录 q1 的基线状态。

## H3：分辨率与 raw pointer 降低不可逆遗忘

层级 `routing_repr → child → raw_pointer` 在相同预算下能降低 evidence miss；高层摘要不能直接回答但能指向原文，计为 routing 成功，不计为 content retention 成功。

**反证：**平面 cold retrieval 在相同候选和 token 预算下同样好或更好，或层级错误传播抵消收益。

## H4：decay/cooldown 防止促升正反馈

utility + decay + cooldown 的 tier occupancy、promotion regret 和 churn 比无衰减/无 cooldown 更稳定，且不牺牲后续 utility retention。

**反证：**早期偶然命中的 block 长期垄断 hot tier，或者 churn/容量挤占使后续 recall 下降。

## H5：Oracle utility 有效不等于可部署 predictor 已解决

Oracle 使用 gold answer 或 counterfactual loss 只能验证“理想 utility 信号是否值得用于促升”。deployable utility proxy（confidence change、self-consistency、attention contribution、reward model、prediction-loss proxy 或 learned predictor）是独立后续问题。

**反证：**Oracle 本身在匹配预算下也无后续优势，则不应继续投入 utility predictor。

## H6：内部 attention 集成才是后续系统假设

仅在 Phase 2 测试：小型 Transformer 接入控制器后，在相同质量阈值下 KV bytes/latency 是否降低。Phase 1 controller simulation 不支持 H6。

**反证：**控制器、I/O、训练不稳定性或 utility 计算成本超过节省。

## 控制变量

固定 history、future query 时间顺序、答案键、embedding/hidden representation、memory budget、retrieval budget、候选数、随机 seed 和评分代码。每个 episode 保存 q1 前状态、q1 结果、utility、tier 更新、memory pressure、q2/q3 结果和 raw trace。
