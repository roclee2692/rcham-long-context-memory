# Phase 1 Minimal Principle Test

运行模式：full（至少三 seed）。本报告只覆盖 CPU synthetic lifecycle，不包含 Transformer、GPU、offload 或 latency。

## Hypothesis

q1 完成后得到的 task-level counterfactual utility，比 recency、frequency、attention 和 RMM-like demonstrated-attention 更能预测 q2/q3 前应保留的历史 evidence。

## Causal timeline

`t0 writes → t1 distractors/probes → q1 → post-use utility → pressure writes → q2/q3`。写入时不读取 future query；q1 的 utility 只在 q1 结束后计算。q1 使用 archive 保证路由不是本实验变量。

## Policies and budgets

Policies: `recency, frequency, attention, rmm_like, task_utility, oracle_future_reuse`。Seeds: `[7, 11, 19]`；capacities: `[8, 16]`；pressure: `[2, 4]`。所有 policy 共享同一 episode、capacity、写入序列和 query 序列。

`oracle_future_reuse` 读取 q2/q3 标签，只作为不可部署的上界。`task_utility` 只读取 q1 的 exact counterfactual loss difference。

## Aggregate results

| policy | n | future retention | q2 acc | q3 acc | retained useless | eviction regret | cold blocks |
|---|---:|---:|---:|---:|---:|---:|---:|
| attention | 96 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 5.9 |
| frequency | 96 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 5.9 |
| oracle_future_reuse | 96 | 0.823 | 1.000 | 1.000 | 0.000 | 0.177 | 2.1 |
| recency | 96 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 5.9 |
| rmm_like | 96 | 0.458 | 0.375 | 0.500 | 0.000 | 0.542 | 4.4 |
| task_utility | 96 | 0.458 | 0.375 | 0.500 | 0.000 | 0.542 | 4.4 |

Task utility minus attention future-retention: `+0.458`; minus RMM-like: `+0.000`; q2/q3 answer-accuracy difference vs attention: `+0.438`.

## Scenario-level behavior

| scenario | policy | n | future retention | q2 acc | q3 acc |
|---|---|---:|---:|---:|---:|
| cross_event | attention | 12 | 0.000 | 0.000 | 0.000 |
| cross_event | frequency | 12 | 0.000 | 0.000 | 0.000 |
| cross_event | oracle_future_reuse | 12 | 0.667 | 1.000 | 1.000 |
| cross_event | recency | 12 | 0.000 | 0.000 | 0.000 |
| cross_event | rmm_like | 12 | 0.333 | 0.000 | 0.000 |
| cross_event | task_utility | 12 | 0.333 | 0.000 | 0.000 |
| delayed_reuse | attention | 12 | 0.000 | 0.000 | 0.000 |
| delayed_reuse | frequency | 12 | 0.000 | 0.000 | 0.000 |
| delayed_reuse | oracle_future_reuse | 12 | 0.500 | 1.000 | 1.000 |
| delayed_reuse | recency | 12 | 0.000 | 0.000 | 0.000 |
| delayed_reuse | rmm_like | 12 | 0.250 | 0.000 | 1.000 |
| delayed_reuse | task_utility | 12 | 0.250 | 0.000 | 1.000 |
| frequent_useless | attention | 12 | 0.000 | 0.000 | 0.000 |
| frequent_useless | frequency | 12 | 0.000 | 0.000 | 0.000 |
| frequent_useless | oracle_future_reuse | 12 | 1.000 | 1.000 | 1.000 |
| frequent_useless | recency | 12 | 0.000 | 0.000 | 0.000 |
| frequent_useless | rmm_like | 12 | 1.000 | 1.000 | 1.000 |
| frequent_useless | task_utility | 12 | 1.000 | 1.000 | 1.000 |
| negation_condition | attention | 12 | 0.000 | 0.000 | 0.000 |
| negation_condition | frequency | 12 | 0.000 | 0.000 | 0.000 |
| negation_condition | oracle_future_reuse | 12 | 0.750 | 1.000 | 1.000 |
| negation_condition | recency | 12 | 0.000 | 0.000 | 0.000 |
| negation_condition | rmm_like | 12 | 0.750 | 1.000 | 1.000 |
| negation_condition | task_utility | 12 | 0.750 | 1.000 | 1.000 |
| obsolete_information | attention | 12 | 0.000 | 0.000 | 0.000 |
| obsolete_information | frequency | 12 | 0.000 | 0.000 | 0.000 |
| obsolete_information | oracle_future_reuse | 12 | 1.000 | 1.000 | 1.000 |
| obsolete_information | recency | 12 | 0.000 | 0.000 | 0.000 |
| obsolete_information | rmm_like | 12 | 0.000 | 0.000 | 0.000 |
| obsolete_information | task_utility | 12 | 0.000 | 0.000 | 0.000 |
| related_nonidentical | attention | 12 | 0.000 | 0.000 | 0.000 |
| related_nonidentical | frequency | 12 | 0.000 | 0.000 | 0.000 |
| related_nonidentical | oracle_future_reuse | 12 | 0.667 | 1.000 | 1.000 |
| related_nonidentical | recency | 12 | 0.000 | 0.000 | 0.000 |
| related_nonidentical | rmm_like | 12 | 0.333 | 0.000 | 0.000 |
| related_nonidentical | task_utility | 12 | 0.333 | 0.000 | 0.000 |
| repeated_useful | attention | 12 | 0.000 | 0.000 | 0.000 |
| repeated_useful | frequency | 12 | 0.000 | 0.000 | 0.000 |
| repeated_useful | oracle_future_reuse | 12 | 1.000 | 1.000 | 1.000 |
| repeated_useful | recency | 12 | 0.000 | 0.000 | 0.000 |
| repeated_useful | rmm_like | 12 | 1.000 | 1.000 | 1.000 |
| repeated_useful | task_utility | 12 | 1.000 | 1.000 | 1.000 |
| state_update | attention | 12 | 0.000 | 0.000 | 0.000 |
| state_update | frequency | 12 | 0.000 | 0.000 | 0.000 |
| state_update | oracle_future_reuse | 12 | 1.000 | 1.000 | 1.000 |
| state_update | recency | 12 | 0.000 | 0.000 | 0.000 |
| state_update | rmm_like | 12 | 0.000 | 0.000 | 0.000 |
| state_update | task_utility | 12 | 0.000 | 0.000 | 0.000 |

## Failure cases and interpretation

- `frequent_useless` intentionally tests retrieved ≠ useful; frequency may retain routine counters while task utility protects q1 evidence.
- `related_nonidentical`, `state_update`, and `delayed_reuse` test whether q1 utility transfers to new evidence. A q1 label cannot predict a block first written after q1; the oracle future-reuse row exposes this ceiling.
- `negation_condition` and `cross_event` give different q1 attention weights to required evidence. If attention/RMM retain only the high-weight block, hot-only q2 accuracy exposes the failure.
- `obsolete_information` tests promotion regret: q1 utility can be correct for q1 and still be wrong for later reuse.
- At the frozen 2x/4x pressure levels, recency, frequency, and attention saturate at zero future retention. This is recorded as a baseline-saturation limitation, not evidence that task utility is universally superior.

## Verdict

**NO-GO**. This is a mechanism result only. It does not establish an internal Transformer contribution, latency gain, or deployable utility predictor.

The full raw trace is the source of all metrics. No result was selected or edited by hand.

## Next step

Because this result is NO-GO, stop here. Do not implement full RCHAM, add hierarchy/decay/hardware to rescue it, or move to a real benchmark without a new human-approved hypothesis.
