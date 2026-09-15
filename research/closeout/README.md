# Research Closeout

RCHAM 当前 FROZEN / ARCHIVED（暂时冻结），核心真实模型假设未充分验证、未被证伪。见 [当前决策及重启条件](../PROJECT_STATUS.md)。本目录保存既有结项证据；旧 Phase 1R 实现保持关闭，审计结论见 [复核报告](../reports/research_closeout.md)。

- [关闭的研究主张](rejected_hypotheses.md)
- [可复用材料及限制](reusable_infrastructure.md)
- [只记录的开放问题](open_questions.md)
- [Phase 1R 审计统计](phase1r_audit_summary.json)
- [原始证据清单](evidence/manifest.json)

本目录下的审计脚本只读取现有 traces，不导入原实验实现、不执行模型、generator 或 controller：

```bash
python3 research/closeout/audit_existing_phase1r.py --out /tmp/rcham-closeout-review
```

脚本优先读取本地未变更的 Phase 1R raw 文件；在干净 checkout 没有忽略目录的情况下，读取已提交的 gzip 证据。它验证原 trace hash 并生成同样的审计结果。

旧 Phase 1R 源码、报告数值与本地原始 artifacts 不覆盖。归档副本是 synthetic JSON/CSV 的无损 gzip，mtime 固定为 0；压缩与解压验证不属于新的实验。
