# Phase 1A Pilot Report — Oracle Controller Mechanism

**Status:** completed; Phase 1B was not executed.

**Date:** 2026-09-15

## Current hypothesis

After a first cold access has exposed that a memory block was useful, an
oracle utility signal can promote that block to a higher-resolution tier. Under
the same memory budget and later write pressure, this may improve repeated-use
retention and reduce future cold reads. This experiment does **not** claim to
solve first-time unexpected queries: q1 is deliberately handled by perfect
routing plus cold/raw fallback before any promotion.

The supplied `research-workflow` prior-art gate also changes the interpretation:
cache locality, retrieval-count policies, KV retention, and utility-aware
memory management are already established components. This pilot therefore
tests only the lifecycle mechanism under a controlled, equal-budget simulation;
it is not a novelty claim for the general idea.

## 1. Experimental design

Each deterministic episode follows this timeline:

```text
t0  write target M
t1  write enough distractors to evict M from Tier 1
t2  q1 needs M; exact evidence IDs provide perfect routing and M is read cold
t3  after q1, oracle utility(M) is delivered to the controller
t4  write pressure well beyond Tier 1 capacity
t5  q2 and q3 request repeated or related evidence
```

The controller never sees future query labels, future answers, or future
utility at write time. Tier 1 is bounded hot/high-resolution memory; Tier 2 is
an unbounded compressed index; Tier 3 is an immutable raw archive. No neural
compression, Transformer, GPU, paid API, or latency claim is involved.

The sweep generated **486 episodes** and replayed each under six policies,
for **2,916 controller runs**. Every policy replayed the same episode events,
capacity, evidence IDs, seed, and raw archive.

## 2. Controllers

| Policy | Rule |
|---|---|
| Static | No access-based promotion after writes. |
| Retrieval-count | Every retrieved block increases its count and can be promoted, regardless of usefulness. |
| Oracle utility | Only the post-q1 oracle utility label can promote a block. |
| Oracle utility + decay + cooldown | Oracle promotion plus score decay and a cooldown before demotion. |
| Cold-Raw-Fallback Only | No post-use promotion; every later cold miss reads Tier 3. |
| Perfect-Routing + No-Promotion | Perfect evidence routing but no lifecycle promotion; control for routing value. |

The scenarios include repeated useful memory, related-but-nonidentical future
evidence, frequently retrieved useless distractors, initially useful but later
obsolete memory, delayed second use, and competing useful memories.

## 3. Frozen parameters

```yaml
seeds: [7, 11, 19]
tier1_capacity: [8, 16, 32]
post_q1_pressure: [2x, 4x, 8x tier1 capacity]
delay: [short, medium, long]
block_sizes: {hot: 128, compressed: 16, raw: 256} bytes
decay_factor: 0.97
decay_threshold: 0.10
cooldown_steps: 3
```

The complete machine-readable configuration is in
[config.json](../experiments/phase1a/config.json).

## 4. Aggregate results

Values are means over all 486 episodes. `useful_retention` is the fraction of
future-useful blocks in Tier 1 at q2/q3; `cold_reads` counts all q1/q2/q3 raw
block reads; `regret` counts post-q1 promotions of blocks not labelled
future-useful by the evaluator.

| Policy | q2 M survival | q3 M survival | useful retention | q2 cold blocks | q3 cold blocks | cold reads | churn | regret |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Static | 0.000 | 0.000 | 0.000 | 1.333 | 1.333 | 3.667 | 403.889 | 0.000 |
| Retrieval-count | 0.500 | 0.833 | 0.458 | 0.833 | 0.333 | 2.167 | 408.222 | 3.944 |
| Oracle utility | **0.667** | **0.833** | **0.500** | **0.667** | 0.500 | 2.167 | 405.889 | 0.167 |
| Oracle + decay/cooldown | 0.253 | 0.327 | 0.184 | 1.080 | 1.006 | 6.864 | 424.160 | 0.167 |
| Cold-Raw-Fallback Only | 0.000 | 0.000 | 0.000 | 1.333 | 1.333 | 3.667 | 403.889 | 0.000 |
| Perfect-Routing + No-Promotion | 0.000 | 0.000 | 0.000 | 1.333 | 1.333 | 3.667 | 403.889 | 0.000 |

Paired differences (`oracle utility - comparison`) were:

| Comparison | useful retention | q2 M survival | q3 M survival | q2 cold blocks | q3 cold blocks | total cold reads | churn | regret |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Retrieval-count | +0.042 | +0.167 | +0.000 | -0.167 | +0.167 | 0.000 | -2.333 | -3.778 |
| Cold-Raw-Fallback Only | +0.500 | +0.667 | +0.833 | -0.667 | -0.833 | -1.500 | +2.000 | +0.167 |
| Perfect-Routing + No-Promotion | +0.500 | +0.667 | +0.833 | -0.667 | -0.833 | -1.500 | +2.000 | +0.167 |

## 5. Scenario findings

- **Repeated useful:** utility and retrieval-count both retain M for q2/q3;
  promotion is valuable relative to cold-only, but utility has no advantage over
  count when every access is useful.
- **Useless distractor:** utility retains M and has zero post-q1 regret;
  retrieval-count is misled by frequent useless accesses (mean regret 22.7 in
  this scenario) and loses M at q2 in the aggregate scenario slice.
- **Related-nonidentical and competing-useful:** utility protects the block
  proven useful by q1, but cannot anticipate a new related block that has never
  produced utility. Retrieval-count can promote that block after q2, which is
  evidence for the first-time limitation rather than evidence against the
  lifecycle mechanism.
- **Obsolete target:** utility promotion of M is correctly counted as regret
  once later evidence makes M obsolete. This is a real failure mode for a
  utility-only controller and motivates deployable decay/demotion research.
- **Decay/cooldown:** the chosen conservative toy decay demotes useful blocks
  during long pressure. It reduced retention and increased cold reads in this
  pilot; it is not a positive result for the current parameters.

## 6. Raw trace example

For `repeated_useful-s7-c8-p2-short` under `oracle_utility`:

```text
q1: M is not in Tier 1; cold_blocks=1; cold_bytes=256
utility(q1): M promoted after q1; Tier 1 size=8
q2: M in Tier 1; hot_evidence_recall=1.0; cold_blocks=0
q3: M in Tier 1; hot_evidence_recall=1.0; cold_blocks=0
```

The complete unmodified traces are in
[traces.jsonl](../experiments/phase1a/results/raw/traces.jsonl).

## 7. Failure cases and limits

1. Utility promotion does not improve q1 routing; q1 is intentionally a cold
   access in every policy.
2. Utility cannot foresee a related block first requested at q2. The cold
   fallback is still required for that first unexpected evidence.
3. Retrieval-count can match utility when all retrievals are useful, and it can
   outperform utility on a newly exposed related block because it receives a
   q2 access signal. `retrieved != useful` remains a meaningful distinction.
4. The decay/cooldown parameters are not tuned and currently hurt retention.
5. This simulator uses exact evidence IDs and synthetic byte sizes. It does not
   establish answer accuracy, neural compression quality, Transformer
   training stability, GPU memory reduction, or wall-clock latency.
6. The very high churn values count deterministic write-driven tier movement;
   they are useful for policy comparison within this simulator but are not a
   production cache benchmark.

## 8. Gate decision

**CONDITIONAL GO for a narrowly scoped Phase 1B design, but Phase 1B is not
executed here.**

The mechanism earns a conditional pass because oracle utility clearly beats
cold-only/perfect-routing-no-promotion on later retention and cold reads, and
it avoids the useless-distractor failure of retrieval-count. However, its
advantage over retrieval-count is small in the all-scenario mean, it cannot
solve first-time related evidence, and the current decay/cooldown toy policy is
worse. The result does not justify a Transformer implementation yet.

Before any Phase 1B, the next falsifying test should use a realistic memory
sequence with imperfect routing and a deployable utility proxy, while keeping
the same paired episodes and budget controls. The prior-art gate must be
repeated before claiming novelty or scaling the experiment.

## 9. Reproducibility and stopping point

Commands run:

```bash
python3 -m unittest discover -s research/experiments/phase1a/tests -p 'test_*.py'
python3 research/experiments/phase1a/run_pilot.py
```

All six required tests pass. The generated JSON, JSONL, CSV, and configuration
files are retained under `research/experiments/phase1a/`. No model process,
GPU job, large download, or paid API was started. This report is the stopping
point; Phase 1B and Transformer integration remain unexecuted.
