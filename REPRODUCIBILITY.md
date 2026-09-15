# Reproducibility

This archive separates executed artifacts from plans and literature review.

## What actually ran

- The early compression/navigation probe in `outputs/compression_probe/` ran locally without an API or model download. Its inputs, code, manifest, and failure traces are retained.
- Phase 1, Phase 1A, and Phase 1R are synthetic simulator experiments. Their source, selected raw traces, metrics, and reports remain in `research/experiments/` and `research/reports/`.
- The final source-level review in `research/closeout/` is read-only analysis of existing artifacts. It did not rerun a model or controller.
- No real frozen LLM task-utility experiment has been completed. No Transformer was trained for this project.

## Reproducing archived artifacts

The early probe can be run with:

```bash
python3 -m pip install -r requirements.txt
python3 outputs/compression_probe/probe.py --output-dir work/reproduction
```

The closeout audit can be run with:

```bash
python3 research/closeout/audit_existing_phase1r.py --out /tmp/rcham-closeout-review
```

Archived manifests record SHA-256 values for the source and synthetic artifacts. Raw traces that are not tracked in the repository are identified in the corresponding manifest or report; they are not silently treated as reproduced data.

## Known reproducibility limits

The archived Phase 1R seeds changed a nonce that did not affect policy decisions, so they are not independent task replications. Its scorer, RMM-like proxy, and q2/q3 evidence-availability metric are documented as validity limitations in [the source audit](research/reports/research_closeout.md). Wall-clock timing from the early Python probe is environment-dependent and is not a systems-performance claim.

The project is FROZEN / ARCHIVED. Re-running an archived script does not authorize a new Phase 1 or a real-model experiment.
