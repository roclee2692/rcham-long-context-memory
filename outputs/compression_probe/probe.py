#!/usr/bin/env python3
"""Mechanical mean-index / hierarchical recall pilot; NOT a language-model experiment.

Run: python3 probe.py --output-dir ./results
Dependencies: Python 3 and NumPy only. No model, API, download, or training.
All queries are generated AFTER all indexes for their history have been built.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_name, "1")
import numpy as np


CONFIG = dict(
    n_records=[256, 1024, 4096], dimension=64, leaf_records=16, branching=4,
    seeds=[17, 41, 83], histories_per_seed=3, queries_per_history=20,
    themes=16, within_theme_noise=0.7, query_noise_per_dimension=0.08,
    bootstrap_samples=2000,
)
METHODS = ["raw_full_scan", "flat_1", "flat_2", "flat_4", "tree_beam_1", "tree_beam_2", "tree_beam_4"]


def normalize(x):
    return (x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-12)).astype(np.float32)


def topk(scores, k):
    # Stable sort gives deterministic tie handling. Its cost is included in timing.
    return np.argsort(-scores, kind="stable")[:k]


class Index:
    def __init__(self, keys, values, evidence_ids):
        start = time.perf_counter_ns()
        self.keys, self.values, self.evidence_ids = keys, values, evidence_ids
        n, d = keys.shape
        leaf, branch = CONFIG["leaf_records"], CONFIG["branching"]
        self.means = [keys.reshape(n // leaf, leaf, d).mean(axis=1)]
        while len(self.means[-1]) > 1:
            previous = self.means[-1]
            assert len(previous) % branch == 0
            self.means.append(previous.reshape(-1, branch, d).mean(axis=1))
        self.levels = [normalize(x) for x in self.means]
        # Build once, then discard redundant means: the stored search index is levels.
        del self.means
        # Arithmetic child/record ranges suffice for this regular tree: no dense pointers.
        self.build_ms = (time.perf_counter_ns() - start) / 1e6
        self.index_vector_bytes = sum(x.nbytes for x in self.levels)
        self.raw_storage_bytes = keys.nbytes + values.nbytes + evidence_ids.nbytes

    def route(self, query, method, target_position, capture=False):
        start = time.perf_counter_ns()
        visited, trace = 0, []
        if method == "raw_full_scan":
            leaves = np.arange(len(self.levels[0]))
        elif method.startswith("flat_"):
            k = int(method.rsplit("_", 1)[1])
            scores = self.levels[0] @ query
            visited = len(scores)
            leaves = topk(scores, k)
        else:
            width = int(method.rsplit("_", 1)[1])
            current = np.array([0], dtype=np.int64)
            for level in range(len(self.levels) - 2, -1, -1):
                candidates = (current[:, None] * CONFIG["branching"] + np.arange(CONFIG["branching"])).reshape(-1)
                scores = self.levels[level][candidates] @ query
                visited += len(candidates)
                kept = topk(scores, min(width, len(candidates)))
                current = candidates[kept]
                if capture:
                    target_node = int(target_position // (CONFIG["leaf_records"] * CONFIG["branching"] ** level))
                    trace.append(dict(level_from_leaf=level, candidate_nodes=candidates.tolist(),
                                      candidate_scores=scores.tolist(), kept_nodes=current.tolist(),
                                      target_ancestor=target_node,
                                      target_ancestor_considered=bool(target_node in candidates),
                                      target_ancestor_kept=bool(target_node in current)))
            leaves = current
        route_ms = (time.perf_counter_ns() - start) / 1e6
        return leaves, visited, route_ms, trace

    def read(self, query, leaves, target_evidence):
        start = time.perf_counter_ns()
        positions = (leaves[:, None] * CONFIG["leaf_records"] + np.arange(CONFIG["leaf_records"])).reshape(-1)
        # This exact raw-vector scorer is an ORACLE READER diagnostic, not LLM QA.
        scores = self.keys[positions] @ query
        winner_position = positions[int(np.argmax(scores))]
        ids = self.evidence_ids[positions]
        return dict(
            evidence_recalled=int(target_evidence in ids),
            oracle_reader_correct=int(self.evidence_ids[winner_position] == target_evidence),
            predicted_evidence_id=int(self.evidence_ids[winner_position]),
            records_read=len(positions), raw_vectors_scored=len(scores),
            leaf_blocks_read=len(leaves),
            read_score_ms=(time.perf_counter_ns() - start) / 1e6,
        )


def bootstrap_paired(rows, n, scenario, left, right, metric, rng):
    relevant = [r for r in rows if r["n_records"] == n and r["scenario"] == scenario and r["method"] in (left, right)]
    blocks = {}
    for r in relevant:
        blocks.setdefault(r["history_id"], {}).setdefault(r["method"], []).append(r[metric])
    diffs = np.array([np.mean(x[left]) - np.mean(x[right]) for x in blocks.values()])
    samples = diffs[rng.integers(len(diffs), size=(CONFIG["bootstrap_samples"], len(diffs)))].mean(axis=1)
    return dict(n_records=n, scenario=scenario, left=left, right=right, metric=metric,
                matched_raw_read_budget=left.rsplit("_", 1)[1] == right.rsplit("_", 1)[1],
                comparison_note="Routing costs differ; different suffixes also mean different raw-read budgets.",
                paired_difference=float(diffs.mean()), ci95_percentile=np.quantile(samples, [0.025, 0.975]).tolist(),
                resampling_unit="independent history (all its queries retained together)", histories=len(diffs))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    rows, index_rows, error_trace = [], [], None
    for n in CONFIG["n_records"]:
        for seed in CONFIG["seeds"]:
            for history_number in range(CONFIG["histories_per_seed"]):
                rng = np.random.default_rng(np.random.SeedSequence([seed, n, history_number]))
                d = CONFIG["dimension"]
                evidence_ids = np.arange(n, dtype=np.int64)
                values = rng.integers(100000, 999999, size=n, dtype=np.int64)
                independent = normalize(rng.normal(size=(n, d)))
                centers = normalize(rng.normal(size=(CONFIG["themes"], d)))
                topic_ids = np.repeat(np.arange(CONFIG["themes"]), n // CONFIG["themes"])
                perturbations = normalize(rng.normal(size=(n, d)))
                clustered = normalize(centers[topic_ids] + CONFIG["within_theme_noise"] * perturbations)
                shuffle = rng.permutation(n)
                histories = {
                    "random_keys": (independent, values.copy(), evidence_ids.copy()),
                    "topic_grouped": (clustered, values.copy(), evidence_ids.copy()),
                    "topic_shuffled": (clustered[shuffle], values[shuffle], evidence_ids[shuffle]),
                }
                assert np.array_equal(histories["topic_grouped"][0], histories["topic_shuffled"][0][np.argsort(shuffle)])
                # ALL indexes are constructed without seeing targets or queries.
                indexes = {name: Index(*data) for name, data in histories.items()}
                history_id = f"n{n}_seed{seed}_history{history_number}"
                for scenario, index in indexes.items():
                    canonical_order = np.argsort(index.evidence_ids)
                    payload_hash = hashlib.sha256(index.keys[canonical_order].tobytes() + index.values[canonical_order].tobytes()).hexdigest()
                    index_rows.append(dict(history_id=history_id, n_records=n, scenario=scenario,
                                           build_ms=index.build_ms, index_vector_bytes=index.index_vector_bytes,
                                           raw_storage_bytes=index.raw_storage_bytes,
                                           levels_including_root=len(index.levels),
                                           canonical_archive_sha256=payload_hash,
                                           index_vectors=sum(len(x) for x in index.levels)))
                # Independent query RNG; paired scenarios get the same target IDs/noise.
                qrng = np.random.default_rng(np.random.SeedSequence([seed, n, history_number, 987654321]))
                targets = qrng.integers(n, size=CONFIG["queries_per_history"])
                noises = qrng.normal(size=(len(targets), d)) * CONFIG["query_noise_per_dimension"]
                for scenario, index in indexes.items():
                    inverse = np.argsort(index.evidence_ids)
                    for query_number, (target, noise) in enumerate(zip(targets, noises)):
                        position = int(inverse[target])
                        query = normalize(index.keys[position] + noise)
                        query_hash = hashlib.sha256(query.tobytes()).hexdigest()
                        results = {}
                        for method in METHODS:
                            leaves, visited, route_ms, _ = index.route(query, method, position)
                            read = index.read(query, leaves, target)
                            row = dict(history_id=history_id, seed=seed, history_number=history_number,
                                       n_records=n, scenario=scenario, query_number=query_number,
                                       query_id=f"{history_id}_q{query_number}", target_evidence_id=int(target),
                                       query_sha256=query_hash,
                                       method=method, routing_vectors_scored=visited, route_ms=route_ms,
                                       total_search_ms=route_ms + read["read_score_ms"], **read)
                            rows.append(row)
                            results[method] = (row, leaves)
                        if (error_trace is None and scenario == "random_keys"
                                and results["flat_4"][0]["evidence_recalled"]
                                and not results["tree_beam_4"][0]["evidence_recalled"]):
                            leaves, visited, _, trace = index.route(query, "tree_beam_4", position, capture=True)
                            error_trace = dict(
                                explanation="Raw evidence is present; an ancestor is pruned by mean-summary routing. Flat and tree both read 4 leaves / 64 records.",
                                history_id=history_id, scenario=scenario, query_number=query_number,
                                n_records=n, target_evidence_id=int(target), target_archive_position=position,
                                target_value=int(index.values[position]), target_leaf=position // CONFIG["leaf_records"],
                                archive_has_target=bool(target in index.evidence_ids),
                                raw_full_scan_correct=bool(results["raw_full_scan"][0]["oracle_reader_correct"]),
                                query_vector=query.tolist(), target_key_vector=index.keys[position].tolist(),
                                flat_4_selected_leaves=results["flat_4"][1].tolist(),
                                tree_beam_4_selected_leaves=leaves.tolist(), tree_trace=trace,
                            )
        print(f"Completed n={n}; {len(rows)} method-query rows; elapsed={time.perf_counter()-start:.2f}s", flush=True)

    with (args.output_dir / "per_query.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    with (args.output_dir / "per_history_index.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(index_rows[0])); writer.writeheader(); writer.writerows(index_rows)
    summaries = []
    for n in CONFIG["n_records"]:
        for scenario in histories:
            for method in METHODS:
                subset = [r for r in rows if r["n_records"] == n and r["scenario"] == scenario and r["method"] == method]
                summary = dict(n_records=n, scenario=scenario, method=method, queries=len(subset), independent_histories=9)
                for metric in ["evidence_recalled", "oracle_reader_correct", "routing_vectors_scored", "records_read", "raw_vectors_scored", "leaf_blocks_read", "route_ms", "read_score_ms", "total_search_ms"]:
                    summary[metric + "_mean"] = float(np.mean([r[metric] for r in subset]))
                summary["total_search_ms_median"] = float(np.median([r["total_search_ms"] for r in subset]))
                summaries.append(summary)
    with (args.output_dir / "summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0])); writer.writeheader(); writer.writerows(summaries)
    brng = np.random.default_rng(20260914)
    cis = [bootstrap_paired(rows, n, scenario, left, right, "evidence_recalled", brng)
           for n in CONFIG["n_records"] for scenario in histories
           for left, right in [("tree_beam_4", "flat_4"), ("tree_beam_4", "tree_beam_1")]]
    report = dict(
        title="Synthetic mean-summary navigation pilot, not neural compression evidence",
        config=CONFIG, methods=METHODS, environment=dict(python=sys.version, numpy=np.__version__, platform=platform.platform()),
        wall_seconds=time.perf_counter()-start, method_query_rows=len(rows),
        evaluated_query_scenarios=len(rows)//len(METHODS),
        distinct_underlying_queries=len({r["query_sha256"] for r in rows}),
        caveats=[
            "Keys are synthetic vectors, not learned token embeddings or natural-language semantic representations.",
            "Mean summaries and cosine routing are untrained; no claim about limits of trained compressors.",
            "Queries are target keys plus noise: diagnostic vector retrieval, not downstream language understanding.",
            "Raw archive is retained in full; index compression does not mean equal reduction of total memory.",
            "The reader exactly scores candidate raw keys; it is not an LLM and does not establish QA accuracy.",
            "raw_full_scan reads all records: it is a deliberately non-budget-matched reference.",
            "flat_k and tree_beam_k share the same index and read identical k*16 raw records; routing work differs.",
            "Tree beam width is bounded globally at each level, not separately for each parent.",
            "Routing vector counts omit sort overhead; wall timings include it, but Python/CPU timings are not GPU speedups.",
            "Timing uses a fixed method order without dedicated warmup/randomized microbenchmark repetitions; treat it as diagnostic only.",
            "All flat methods retain the same shared tree for controlled routing comparison, although a standalone flat index would not require internal nodes.",
            "Index bytes count float32 vector payload only; raw bytes count key, int64 value and int64 evidence ID payloads. Python/allocator/query memory excluded.",
            "Tree has implicit arithmetic source pointers; richer metadata, extraction and learned compression would add cost.",
            "9 histories per setting are a small pilot. History-block bootstrap intervals are descriptive, not confirmatory significance tests.",
            "No temporal state reconstruction, training, neural Attention baseline, KV cache, or device transfer is tested.",
        ],
        summary=summaries, paired_history_bootstrap=cis,
    )
    for filename, obj in [("report.json", report), ("error_trace.json", error_trace)]:
        (args.output_dir / filename).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    assert len(rows) == 11340
    for row in rows:
        if row["method"] != "raw_full_scan":
            assert row["records_read"] <= 64
            assert row["records_read"] == 16 * int(row["method"].rsplit("_", 1)[1])
    assert error_trace is not None
    paired_hashes = {}
    for row in rows:
        if row["scenario"] in ("topic_grouped", "topic_shuffled"):
            key = (row["query_id"], row["method"])
            if key in paired_hashes:
                assert paired_hashes[key] == row["query_sha256"]
            paired_hashes[key] = row["query_sha256"]
    print(json.dumps(dict(output_dir=str(args.output_dir.resolve()), elapsed_seconds=report["wall_seconds"], method_query_rows=len(rows)), indent=2))


if __name__ == "__main__":
    main()
