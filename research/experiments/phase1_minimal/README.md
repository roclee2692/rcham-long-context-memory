# Phase 1 — Minimal Principle Test

This CPU-only pilot tests one narrow claim:

> After a first query `q1`, does task-level counterfactual utility predict which memory blocks should remain available for related `q2/q3` better than recency, frequency, attention, or an RMM-like demonstrated-attention signal?

It is not a Transformer implementation. It has no neural compression, GPU/CPU/SSD movement, CUDA, or latency claim.

The simulator processes an episode in order:

```text
t0 writes → t1 distractor writes/probes → q1 → post-use utility → pressure writes → q2/q3
```

At write time, the manager receives only the block payload and its current state. Future query labels and future evidence IDs remain evaluator metadata. `q1` is allowed to retrieve its known synthetic evidence from an immutable archive so that routing is not the variable under test.

Policies:

- `recency`
- `frequency`
- `attention`
- `rmm_like`
- `task_utility`
- `oracle_future_reuse` (upper bound only; uses future q2/q3 labels and is not deployable)

The q2/q3 answer metric is deliberately a **hot-memory answer proxy**: all required evidence must be hot before the query. Evidence recall and future-useful retention are reported separately. This prevents a cold archive from hiding the lifecycle difference while avoiding any claim about real model accuracy.

Run a one-seed smoke test first:

```bash
python3 research/experiments/phase1_minimal/run_pilot.py --smoke
```

Then run the frozen three-seed pilot:

```bash
python3 research/experiments/phase1_minimal/run_pilot.py
```

Tests:

```bash
python3 -m unittest discover -s research/experiments/phase1_minimal/tests -v
```

Results are written under `results/smoke/` and `results/full/`. The raw trace is the source of all aggregate metrics.
