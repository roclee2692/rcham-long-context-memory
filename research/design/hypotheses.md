# RCHAM 可证伪假设

## H1：读取后 utility 促升有收益

在固定存储预算、候选数量、检索 token 数和回答模型下，utility-conditioned promotion 的 future-useful retention 高于 static、recency-only 和 retrieval-count-only。

**反证：**utility 方法不高于最强非 utility baseline，或优势只来自更多存储/读取。

## H2：分辨率 + raw pointer 减少不可逆遗忘

层级 `routing_repr → child → raw_pointer` 在相同摘要预算下，能降低 evidence miss；高层无法回答但能导航也算成功。

**反证：**平面检索在相同候选和 token 预算下同样好或更好，或层级错误传播抵消收益。

## H3：衰减和 cooldown 防止正反馈

utility + decay + cooldown 的 tier occupancy、promotion regret 和 churn 比无衰减/无 cooldown 更稳定。

**反证：**促升集中到早期偶然命中的 block，或长期占满 Tier 1 导致未来重要事实 recall 下降。

## H4：内部 attention 集成存在质量—成本收益

只有 Phase 2 才测试：小型 Transformer 接入控制器后，在相同质量阈值下 KV bytes/latency 更低。

**反证：**控制器成本、I/O 或训练不稳定性超过节省；不得把模拟器结果当作 H4 证据。

## 控制变量

固定 history、future query 集合、答案键、embedding/hidden representation、memory budget、retrieval budget、候选数、随机 seed 和评测代码。每个方法必须输出逐步 raw trace，统计从 raw trace 自动重算。
