# Phase 1A — Oracle Controller Mechanism Pilot

This directory contains the bounded, deterministic lifecycle simulation. It
does not train a Transformer and it does not measure GPU latency.

Run from the repository root:

```bash
python3 -m unittest discover -s research/experiments/phase1a/tests -p 'test_*.py'
python3 research/experiments/phase1a/run_pilot.py
```

`generate_data.py` creates the shared episode stream. `controllers.py` contains
the six policies. `run_pilot.py` replays every policy against every identical
episode and writes JSONL traces plus CSV/JSON summaries under `results/`.

The pilot is complete and intentionally stops before Phase 1B. See
`research/reports/phase1a_pilot_report.md` for the interpretation and gate
decision.
