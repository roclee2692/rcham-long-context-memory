# 可复用材料清单

状态：项目已结项。复用文件不意味着接受其中的全部研究结论。

| 材料 | 路径 | 可保留用途 | 使用前限制 |
|---|---|---|---|
| 全架构文献矩阵 | `research/literature/architecture_landscape_matrix.csv` | 已有路线与线索索引 | metadata、最新版本与主张支持情况需重新按 primary source 核实；不能用“未发现”证明“没人做” |
| 最近工作与生命周期证据 | `research/literature/closest_work_matrix.csv`, `lifecycle_gap_matrix.csv`, `paper_evidence_ledger.md` | 对齐决策时间、可见信息、fallback 和资源动作 | 作者报告、第三方 harness 与独立团队复现必须区分 |
| 版本化设计 | `docs/`, `research/design/` | 保留思路演化和边界 | 历史研究计划已失效，不能自动执行 |
| synthetic generator | `research/experiments/phase1r/generate_data.py` | 有时间顺序的确定性 fixture，调试事件/容量接口 | 不是自然语言能力 benchmark；nonce seeds 无实际差异，词法与证据 ID 标签可能冲突 |
| controller 与 trace harness | `research/experiments/phase1r/policies.py` | 事件记录、容量检查、原始 traces schema 的示例 | 不可原样作为 RMM/LRU 论文复现；admission、write recency、评分等契约仍需重做 |
| 原 scorer | `research/experiments/phase1r/answer_model.py` | 错误测量设计的教学例子 | 只能称 lexical-overlap scorer，不能作为真实模型 NLL |
| 现有测试 | `research/experiments/phase1r/tests/` | 一些确定性与容量逻辑检查 | 通过不代表研究有效；不检验真实模型、seed 多样性或忠实 baseline |
| 结项只读审计 | `research/closeout/audit_existing_phase1r.py` | 从原文件重新生成描述性审计统计 | 只复核现存记录，不进行模型/策略实验；更正的 cache retention 仍不等于真实 QA |
| 原始证据压缩包 | `research/closeout/evidence/` | 完整保存本次 synthetic raw trace、episodes、原汇总与哈希 | 与原 manifest 核验；gzip 只做无损归档，不改变数值 |
| paper-forensics workflow | 用户提供的 `paper-forensics-skill/SKILL.md`（仓库外） | claim → code → raw → metric 核对、复算与限制说明 | 工作流不是“论文可信”认证；本次未复制或修改仓库外 skill |

本轮使用的 skill 位于：
`/Users/raelon/Drives/D-DevWorkspace/01-活跃项目/01-AI-Agent与自动化/DeepSeekHarnessWorkSpace/paper-forensics-skill/SKILL.md`。

用户之前提供的 `research-workflow.zip` 未在本轮解压、执行或评估，不能将其说成已验证工具。
