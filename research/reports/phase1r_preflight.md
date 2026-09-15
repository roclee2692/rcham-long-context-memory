# Phase 1R Pre-flight Gate

本文件只报告 RMM-like 与 Task Utility 是否在新定义下产生真实决策分歧；正式 policy comparison 只有在 gate 通过后才允许运行。

- Episode-budget cells: `108`
- Score-vector disagreement: `108/108`
- Retained-set disagreement: `24/108` = `0.222`
- Eviction-decision disagreement: `60/108`
- Mean Pearson: `0.2596`; mean Spearman: `0.2000`
- Mean Top-K Jaccard: `1.0000`
- Cells with rank reversal: `12`

## Gate: PASS

Threshold: retained-set disagreement >= `0.20`.

The RMM-like signal is a block-level adaptation of correctness-weighted attention after q1; correctness is computed by the frozen answer model. It is not the original token-level fixed-lag RMM implementation, and the difference is recorded here rather than hidden.

## Disagreement examples

| episode | scenario | capacity | pressure | RMM scores | Task scores |
|---|---|---:|---:|---|---|
| cross_event-s7-c8-p2 | cross_event | 8 | 2 | `{'A': 0.78, 'B': 0.1, 'C': 0.08, 'U': 0.04}` | `{'A': 0.0, 'B': 3.0, 'C': 0.0, 'U': 0.0}` |
| redundant_evidence-s7-c8-p2 | redundant_evidence | 8 | 2 | `{'A': 0.9, 'B': 0.05}` | `{'A': 0.0, 'B': 0.0}` |
| cross_event-s7-c8-p4 | cross_event | 8 | 4 | `{'A': 0.78, 'B': 0.1, 'C': 0.08, 'U': 0.04}` | `{'A': 0.0, 'B': 3.0, 'C': 0.0, 'U': 0.0}` |
| redundant_evidence-s7-c8-p4 | redundant_evidence | 8 | 4 | `{'A': 0.9, 'B': 0.05}` | `{'A': 0.0, 'B': 0.0}` |
| cross_event-s7-c16-p2 | cross_event | 16 | 2 | `{'A': 0.78, 'B': 0.1, 'C': 0.08, 'U': 0.04}` | `{'A': 0.0, 'B': 3.0, 'C': 0.0, 'U': 0.0}` |
| redundant_evidence-s7-c16-p2 | redundant_evidence | 16 | 2 | `{'A': 0.9, 'B': 0.05}` | `{'A': 0.0, 'B': 0.0}` |
| cross_event-s7-c16-p4 | cross_event | 16 | 4 | `{'A': 0.78, 'B': 0.1, 'C': 0.08, 'U': 0.04}` | `{'A': 0.0, 'B': 3.0, 'C': 0.0, 'U': 0.0}` |
| redundant_evidence-s7-c16-p4 | redundant_evidence | 16 | 4 | `{'A': 0.9, 'B': 0.05}` | `{'A': 0.0, 'B': 0.0}` |
| cross_event-s11-c8-p2 | cross_event | 8 | 2 | `{'A': 0.78, 'B': 0.1, 'C': 0.08, 'U': 0.04}` | `{'A': 0.0, 'B': 3.0, 'C': 0.0, 'U': 0.0}` |
| redundant_evidence-s11-c8-p2 | redundant_evidence | 8 | 2 | `{'A': 0.9, 'B': 0.05}` | `{'A': 0.0, 'B': 0.0}` |
