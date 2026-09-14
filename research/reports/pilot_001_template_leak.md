# Archived invalid run: template leakage

这不是有效实验结果，只是方法学失败记录。

早期数据生成器使用了可由问题中的 station/gauge 编号推导的答案格式。模型即使没有从召回原文中得到证据，也可能根据题号猜出答案。例如 Q4 选错原文块后仍输出了对应 state token。该运行因此不能用于支持压缩或召回结论。

处理方式：保留原始 prompt、response、metrics 和图表在 `results/raw/pilot_001_template_leak/`、`results/metrics/pilot_001_template_leak/` 和 `results/figures/pilot_001_template_leak/`；修正后的 Pilot 使用 seeded opaque answer tokens，并重新生成所有结果。失败运行没有被删除或覆盖。
