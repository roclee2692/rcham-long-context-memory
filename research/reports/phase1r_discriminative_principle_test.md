# Phase 1R — Discriminative Principle Test

本实验只验证 q1 后两种 utility policy 是否真正可区分及其最小 downstream 后果；没有 Transformer 训练、GPU、硬件 tier 或大型模型。

## Pre-flight gate

Retained-set disagreement: `24/108` = `0.222`; threshold `0.20`; gate **PASS**.

## Frozen answer model and signals

Task Utility uses a fixed lexical answer scorer. For every q1 candidate block it recomputes gold-answer log probability after masking that block; utility is `logp(full) - logp(masked)`. No 1/n coverage label is used.

RMM-like is a block-level adaptation of RMM's demonstrated correctness-weighted attention: q1 attention mass is multiplied by the frozen model's computed q1 correctness after q1. It is not a reproduction of RMM's token-level fixed-lag buffer or training procedure; that difference limits the claim.

All policies receive the same q1 candidate set and `capacity//2` post-use admission slots. Recency, frequency, attention, RMM-like, and task utility update their own signal after q1; none receives q2/q3 labels.

## Results — all episodes

| policy | n | future retention | q2 acc | q3 acc | eviction regret | retained useless | cold blocks |
|---|---:|---:|---:|---:|---:|---:|---:|
| attention | 108 | 0.556 | 0.556 | 0.667 | 0.444 | 0.000 | 3.6 |
| frequency | 108 | 0.556 | 0.556 | 0.667 | 0.444 | 0.000 | 3.6 |
| oracle_future_reuse | 108 | 0.843 | 1.000 | 1.000 | 0.157 | 0.000 | 1.7 |
| recency | 108 | 0.556 | 0.556 | 0.667 | 0.444 | 0.000 | 3.6 |
| rmm_like | 108 | 0.556 | 0.556 | 0.667 | 0.444 | 0.000 | 3.6 |
| task_utility | 108 | 0.389 | 0.333 | 0.444 | 0.611 | 0.000 | 4.1 |

## Results — episodes with RMM/Task retained-set disagreement

| policy | n | future retention | q2 acc | q3 acc | eviction regret |
|---|---:|---:|---:|---:|---:|
| attention | 24 | 0.833 | 1.000 | 1.000 | 0.167 |
| frequency | 24 | 0.833 | 1.000 | 1.000 | 0.167 |
| oracle_future_reuse | 24 | 0.833 | 1.000 | 1.000 | 0.167 |
| recency | 24 | 0.833 | 1.000 | 1.000 | 0.167 |
| rmm_like | 24 | 0.833 | 1.000 | 1.000 | 0.167 |
| task_utility | 24 | 0.083 | 0.000 | 0.000 | 0.917 |

### Conditional-on-disagreement win rate

- Task Utility future-retention wins over RMM-like: `0/24` = `0.000`.
- Task Utility combined q2/q3 accuracy wins over RMM-like: `0/24` = `0.000`.

## Required failure checks

- Recency/frequency/attention baseline saturation: **NO**. q1 post-use admission was shared, so a zero result would be a benchmark semantic failure rather than a general claim about these signals.
- Synthetic scenarios include high-attention causally useless candidates, low-attention necessary evidence, redundant evidence, obsolete-after-q1 state, related non-identical q2/q3, frequent useless distractors, and delayed reuse.
- `oracle_future_reuse` is an upper bound and receives future labels by construction.

## Representative failure cases

- `cross_event`: the frozen lexical model gives q1 utility to `B` but zero to `A`, because `B` also contains the token `ALPHA`. The q2 query later needs `A` and `C`; this exposes the limit of lexical counterfactual attribution, not evidence that a semantic answer model would make the same assignment.
- `redundant_evidence`: removing either q1 copy leaves the gold answer supported by the other copy, so both task utilities are zero. q2/q3 later request the `B` copy, which is deliberately future-specific and cannot be predicted from q1 utility alone.
- `obsolete_information`: q1 utility correctly identifies the old state for q1, while q2/q3 require a state written after q1. Promotion cannot solve this first-time future information case.

## Verdict

**NO-GO**.

The conditional win check requires Task Utility to beat RMM-like on future retention or combined q2/q3 answer accuracy inside the actual disagreement subset. This does not establish a deployable utility predictor or an internal Transformer contribution.

The run is complete. Do not add hierarchy, decay, hardware tier, or a larger benchmark in this phase.
