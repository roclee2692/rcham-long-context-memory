"""Read existing Phase 1R artifacts only; never import or run an experiment.

Recompute descriptive statistics and evidence hashes for project closeout.
No generator, answer model, controller, test, or network call is executed.
"""

from __future__ import annotations

import argparse
import collections
import csv
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LEGACY = ROOT / "research/experiments/phase1r/results/full"


def read_artifact(name):
    local = LEGACY / name
    packed = HERE / "evidence" / (name.replace("/", "_") + ".gz")
    if local.is_file():
        return local.read_bytes()
    return gzip.decompress(packed.read_bytes())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def mean(values):
    return statistics.mean(values) if values else None


def correlation(xs, ys):
    if len(xs) < 2:
        return None
    dx, dy = [x - mean(xs) for x in xs], [y - mean(ys) for y in ys]
    denominator = math.sqrt(sum(x*x for x in dx) * sum(y*y for y in dy))
    return sum(x*y for x, y in zip(dx, dy)) / denominator if denominator else None


def ranks(values):
    # Average tied ranks, unlike the experiment do not invent a correlation
    # for a constant vector.
    return [1 + sum(y < x for y in values) + (sum(y == x for y in values)-1)/2 for x in values]


def qevents(run):
    return {e["query_id"]: e for e in run["trace"] if e["type"] == "query"}


def audit():
    raw = read_artifact("raw_traces.jsonl")
    data = read_artifact("data/episodes.json")
    manifest = json.loads(read_artifact("manifest.json"))
    episodes = json.loads(data)
    runs = [json.loads(line) for line in raw.splitlines() if line.strip()]
    assert digest(raw) == manifest["raw_trace_sha256"], "raw trace hash mismatch"
    assert len(runs) == manifest["run_count"] and len(episodes) == manifest["episode_count"]
    pairs = collections.defaultdict(dict)
    for run in runs:
        assert run["policy"] not in pairs[run["episode_id"]]
        pairs[run["episode_id"]][run["policy"]] = run
    cells, schedules, summaries = [], collections.defaultdict(set), []
    correct, exact_keyword_formula, matches_attention, nonbinding = 0, 0, 0, 0
    for ep in episodes:
        pair = pairs[ep["episode_id"]]
        a, b = pair["rmm_like"], pair["task_utility"]
        aq, bq = qevents(a), qevents(b)
        ap = next(e for e in a["trace"] if e["type"] == "post_use")
        bp = next(e for e in b["trace"] if e["type"] == "post_use")
        q1 = next(e for e in ep["events"] if e.get("query_id") == "q1")
        correct += ap["answer_correct"] is True
        matches_attention += ap["rmm_signal"] == q1["attention_weights"]
        nonbinding += len(q1["attention_weights"]) <= ap["admission_budget"]
        values = b["metrics"]["q1_utility"].values()
        exact_keyword_formula += all(abs(v/3 - round(v/3)) < 1e-12 for v in values)
        scores_a, scores_b = ap["policy_scores"], bp["policy_scores"]
        ids = sorted(set(scores_a) | set(scores_b))
        xs, ys = [scores_a.get(i, 0) for i in ids], [scores_b.get(i, 0) for i in ids]
        evidence_diff = any(set(aq[q]["hot_ids_before"]) != set(bq[q]["hot_ids_before"]) for q in ("q2", "q3"))
        full_diff = any(set(aq[q]["hot_ids"]) != set(bq[q]["hot_ids"]) for q in ("q2", "q3"))
        # Preserve the original gate's union definition for exact comparison.
        old_gate = set(aq["q2"]["hot_ids_before"] + aq["q3"]["hot_ids_before"]) != set(bq["q2"]["hot_ids_before"] + bq["q3"]["hot_ids_before"])
        ev_a = [e["block_id"] for e in a["trace"] if e["type"] == "evict"]
        ev_b = [e["block_id"] for e in b["trace"] if e["type"] == "evict"]
        reversal = any((xs[i]-xs[j])*(ys[i]-ys[j]) < 0 for i in range(len(ids)) for j in range(i))
        future = set(ep["future_useful_ids"])
        row = {k: ep[k] for k in ("episode_id", "scenario", "seed", "capacity", "pressure_factor")}
        row.update(old_gate=old_gate, evidence_set_disagreement=evidence_diff,
                   full_cache_disagreement=full_diff, eviction_sequence_disagreement=ev_a != ev_b,
                   pearson=correlation(xs, ys), spearman=correlation(ranks(xs), ranks(ys)),
                   strict_rank_reversal=reversal)
        for policy, run in pair.items():
            queries = qevents(run)
            true_retention = mean([len(set(queries[q]["hot_ids"]) & future)/len(future) for q in ("q2", "q3")])
            proxy = mean([queries[q]["hot_answer_accuracy"] for q in ("q2", "q3")])
            old_retention = mean([len(set(queries[q]["hot_ids_before"]) & future)/len(future) for q in ("q2", "q3")])
            assert abs(old_retention - run["metrics"]["future_useful_retention"]) < 1e-12
            assert all(e["hot_size"] <= ep["capacity"] for e in run["trace"])
            summaries.append(dict(episode_id=ep["episode_id"], policy=policy,
                                  original_retention=old_retention, full_cache_future_retention=true_retention,
                                  q2_q3_evidence_availability_proxy=proxy))
            if policy in ("rmm_like", "task_utility"):
                row[policy + "_full_cache_retention"] = true_retention
                row[policy + "_original_retention"] = old_retention
                row[policy + "_answer_proxy"] = proxy
        cells.append(row)
        events = json.loads(json.dumps(ep["events"]))
        for event in events:
            if event["type"] == "write":
                event["block"].pop("write_nonce", None)
        schedules[(ep["scenario"], ep["capacity"], ep["pressure_factor"])].add(digest(json.dumps(events, sort_keys=True).encode()))
    aggregate = []
    subset_stats = {}
    for subset in ("all", "old_gate", "full_cache_disagreement"):
        selected = [c for c in cells if subset == "all" or c[subset]]
        selected_ids = {c["episode_id"] for c in selected}
        for policy in sorted({r["policy"] for r in runs}):
            vals = [r for r in summaries if r["episode_id"] in selected_ids and r["policy"] == policy]
            item = dict(subset=subset, policy=policy, n=len(vals))
            for key in ("original_retention", "full_cache_future_retention", "q2_q3_evidence_availability_proxy"):
                item[key] = mean([r[key] for r in vals])
            aggregate.append(item)
        subset_stats[subset] = dict(n=len(selected))
        for metric in ("full_cache_retention", "original_retention", "answer_proxy"):
            delta = [c["task_utility_"+metric] - c["rmm_like_"+metric] for c in selected]
            subset_stats[subset][metric] = dict(wins=sum(v > 1e-12 for v in delta),
                                               losses=sum(v < -1e-12 for v in delta),
                                               ties=sum(abs(v) <= 1e-12 for v in delta))
    summary = dict(
        analysis="existing artifact audit only; no new experimental run",
        evaluated_commit="c9b8b19f42298a158485090a2d93da36aa3a58d9",
        raw_trace_sha256=digest(raw), episodes_sha256=digest(data), manifest_hash_verified=True,
        episodes=len(episodes), runs=len(runs), q1_correct_true=correct,
        q1_rmm_score_equals_handcrafted_attention=matches_attention,
        utilities_all_multiples_of_three_cells=exact_keyword_formula,
        q1_admission_candidate_count_at_most_slots_cells=nonbinding,
        unique_decision_relevant_schedules=sum(map(len, schedules.values())),
        nominal_seed_groups=len(schedules),
        different_decision_relevant_schedules_within_seed_group=sum(len(s) > 1 for s in schedules.values()),
        old_gate_disagreement=sum(c["old_gate"] for c in cells),
        full_cache_disagreement=sum(c["full_cache_disagreement"] for c in cells),
        eviction_sequence_disagreement=sum(c["eviction_sequence_disagreement"] for c in cells),
        strict_rank_reversal_cells=sum(c["strict_rank_reversal"] for c in cells),
        pearson_defined=sum(c["pearson"] is not None for c in cells),
        spearman_defined=sum(c["spearman"] is not None for c in cells),
        pearson_defined_mean=mean([c["pearson"] for c in cells if c["pearson"] is not None]),
        spearman_defined_mean=mean([c["spearman"] for c in cells if c["spearman"] is not None]),
        subsets=subset_stats,
    )
    return summary, cells, aggregate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=HERE)
    args = parser.parse_args()
    summary, cells, aggregate = audit()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "phase1r_audit_summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    for name, rows in (("phase1r_audit_cells.csv", cells), ("phase1r_audit_aggregates.csv", aggregate)):
        with (args.out / name).open("w", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
