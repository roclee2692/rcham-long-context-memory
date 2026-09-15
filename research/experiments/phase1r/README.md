# Phase 1R — Discriminative Principle Test

This is the one-time correction to the non-identifiable Phase 1 Minimal benchmark.

## Reproduction

```bash
python3 research/experiments/phase1r/run_phase1r.py --preflight-only
python3 research/experiments/phase1r/run_phase1r.py --formal
python3 -m unittest discover -s research/experiments/phase1r/tests -v
```

The formal command refuses to start unless at least 20% of episode-budget cells
show different retained sets for `rmm_like` and `task_utility`.

The frozen answer model is deliberately small and deterministic. It computes a
gold-answer log-probability difference after masking each q1 candidate block;
it is not a learned LLM and does not claim semantic attribution beyond the
synthetic payloads. The RMM-like policy is a documented block-level adaptation
of correctness-weighted attention, not a reproduction of RMM's token-level
fixed-lag training setup.

Raw traces and metrics are written under `results/full/` and are ignored by
the repository's global `results/` rule; the reports and source remain tracked.
