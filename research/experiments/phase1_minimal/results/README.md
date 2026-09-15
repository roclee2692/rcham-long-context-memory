# Phase 1 Minimal outputs

`full/raw_traces.jsonl` is the complete raw source for the 576-run pilot. It is generated locally and ignored by the repository-wide `results/` rule because it is about 19 MB. `full/raw_traces_sample.jsonl`, the manifests, and aggregate CSVs are committed as inspectable artifacts.

The report is generated from the full raw trace by `run_pilot.py`; no aggregate is hand edited.
