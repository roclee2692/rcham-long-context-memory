# Metrics

`pilot_metrics.json` 和 `pilot_summary.csv` 由 `src/evaluation/score_pilot.py` 从 raw rows 自动生成。评分脚本会把跳过的 Q8 从 B/C 分母排除，并排除复用 chunk router 的层级 B/C 诊断行；这些原始行仍保留在 raw 输出中。
