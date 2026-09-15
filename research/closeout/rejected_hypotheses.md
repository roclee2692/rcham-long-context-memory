# Rejected hypotheses / 已关闭的研究主张

> **状态注：**下表保留结项时的主张处置记录；广义方向及尚未有效测试的核心假设现为 [DORMANT / ARCHIVED](../PROJECT_STATUS.md)。冻结不撤回因果时间顺序、证据误读和实验有效性方面的更正，也不批准新实验。

2026-09-15。以 [最终结项复核](../reports/research_closeout.md) 为准。

本清单防止把已停止的主张换个名字重新立项。`CLOSED` 表示本项目不继续投入，不自动等于数学反证或真实模型上的普遍否定。

| 主张 | 当初为何合理 | 已有反例或缺失证据 | 最终状态与边界 |
|---|---|---|---|
| 层级结构本身提高 recall | 分层摘要可缩小搜索范围 | 早期同预算向量原型未显示这种保证；搜索比较次数减少也未转化成 Python latency 优势 | CLOSED AS ASSUMED ADVANTAGE；不外推为全部层级方法无效 |
| 局部 Attention + 压缩 + 层级 + fallback 是新的整体架构贡献 | 能把完整细节与计算预算分离 | prior-art audit 发现大量组件与接口相关工作；本项目未形成经验证的独特贡献 | TERMINATED AS CURRENT NOVELTY DIRECTION；不是穷尽文献后证明“不可能创新” |
| post-use promotion 能帮助第一次意外 query | 使用后提升重要记忆似乎可弥补先前压缩 | 时间顺序不成立：q1 结束后才有信号，无法提前改变同一次 q1 | REJECTED AS CAUSAL CLAIM |
| q1 的贡献越精确，q2/q3 保留就越好 | 当前使用可能提供未来复用线索 | Phase 1 Minimal 不可区分；Phase 1R 的词面 proxy 在现有规则下负结果，但真实模型、RMM 与指标契约不满足 | CLOSED — INSUFFICIENT VALIDATED BENEFIT；真实模型的一般效用命题未充分测试 |
| 当前 task utility 可直接作为逐块缓存价值 | 留下影响当前答案最大的块 | 冗余副本每个单独删除都零损失，但全删会失去答案；旧状态可以对 q1 有用而未来不再适用 | REJECTED AS GUARANTEE；零 singleton marginal 不代表全局集合无价值 |
| 三个 seed 和 0/24 胜出已证明跨随机样本稳定失败 | 有多次运行和条件胜率 | seed 只改变未使用 nonce；24 单元来自两个固定模板，旧 gate 还漏掉 36 个平局分歧 | REJECTED AS EVIDENCE INTERPRETATION |
| 继续加 hierarchy / decay / tier 可以救当前路线 | 系统组合可能弥补局部缺点 | 没有独立正证据；会把失败主张换成更复杂、不可归因的目标 | OUT OF SCOPE；不得作为本项目自动后续步骤 |

历史结果全部保留。对错误表述加更正说明，不删除失败样本，不将结项改成新的算法任务。
