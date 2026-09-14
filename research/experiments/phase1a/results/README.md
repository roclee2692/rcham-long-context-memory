# Phase 1A generated outputs

Run `python3 research/experiments/phase1a/run_pilot.py` to regenerate the
complete artifacts. The full `data/episodes.json` and
`results/raw/traces.jsonl` are deliberately kept as local raw artifacts rather
than committed to Git because the current pilot produces a large deterministic
trace file. `episodes_manifest.json`, `results/raw/manifest.json`,
`traces_sample.jsonl`, and the compact metrics summaries are the reviewable
tracked artifacts. The manifest records byte counts and SHA-256 hashes for the
full local files.
