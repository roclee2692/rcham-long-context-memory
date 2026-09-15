"""Run the gated Phase 1R discriminative principle test.

Usage is intentionally two-step:

    python run_phase1r.py --preflight-only
    python run_phase1r.py --formal

The second command refuses to run unless the first command records at least
20% retained-set disagreement between RMM-like and task-utility policies.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from .answer_model import FrozenAnswerModel
    from .generate_data import generate_episodes, write_json
    from .policies import HotMemory, POLICIES
except ImportError:  # direct script execution
    from answer_model import FrozenAnswerModel
    from generate_data import generate_episodes, write_json
    from policies import HotMemory, POLICIES


HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
REPORT_DIR = (HERE / "../../reports").resolve()


def _post_use_event(result: dict[str, Any]) -> dict[str, Any]:
    return next(event for event in result["trace"] if event.get("type") == "post_use")


def _query_event(result: dict[str, Any], query_id: str) -> dict[str, Any]:
    return next(event for event in result["trace"] if event.get("type") == "query" and event.get("query_id") == query_id)


def _ranked(scores: dict[str, float], k: int) -> list[str]:
    return [block_id for block_id, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:k]]


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    denom = math.sqrt(sum(x * x for x in dx) * sum(y * y for y in dy))
    return sum(x * y for x, y in zip(dx, dy)) / denom if denom else 1.0


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    result = [0.0] * len(values)
    pos = 0
    while pos < len(order):
        end = pos + 1
        while end < len(order) and values[order[end]] == values[order[pos]]:
            end += 1
        rank = (pos + 1 + end) / 2.0
        for index in order[pos:end]:
            result[index] = rank
        pos = end
    return result


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    return _pearson(_ranks(xs), _ranks(ys))


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _episode_budget_key(episode: dict[str, Any]) -> str:
    return episode["episode_id"]


def q1_counterfactual_utilities(episode: dict[str, Any], q1: dict[str, Any], archive: dict[str, dict[str, Any]], model: FrozenAnswerModel) -> tuple[dict[str, float], float, dict[str, float]]:
    full_logp = model.gold_log_probability(q1, archive)
    utility: dict[str, float] = {}
    removed_logp: dict[str, float] = {}
    for block_id in q1["answer_context_ids"]:
        removed_logp[block_id] = model.gold_log_probability(q1, archive, masked_ids=[block_id])
        utility[block_id] = max(0.0, full_logp - removed_logp[block_id])
    return utility, full_logp, removed_logp


def run_episode(episode: dict[str, Any], policy: str, model: FrozenAnswerModel | None = None) -> dict[str, Any]:
    model = model or FrozenAnswerModel()
    manager = HotMemory(policy, episode["capacity"])
    if policy == "oracle_future_reuse":
        manager.set_oracle_future_labels(episode["future_useful_ids"])
    q1_payload: dict[str, Any] = {}
    q1_utility: dict[str, float] = {}
    q1_full_logp = 0.0
    q1_removed_logp: dict[str, float] = {}
    for event in episode["events"]:
        if event["type"] == "write":
            manager.write(event["block"])
        elif event["type"] == "query":
            answer_correct = None
            if event["query_id"] != "q1" or event.get("gold_answer"):
                answer_correct = model.answer_correct(event, manager.archive)
            manager.query(event, answer_correct=answer_correct)
            if event["query_id"] == "q1":
                q1_payload = event
                q1_utility, q1_full_logp, q1_removed_logp = q1_counterfactual_utilities(episode, event, manager.archive, model)
                manager.observe_q1(event, q1_utility, answer_correct=bool(answer_correct))
        else:
            raise ValueError(event)
    if not q1_payload:
        raise AssertionError("episode did not contain q1")
    useless_ids = [block["id"] for block in episode["memory_sequence"] if block["kind"] in {"useless", "distractor"}]
    metrics = manager.evaluate(episode["future_useful_ids"], useless_ids)
    metrics.update({
        "episode_id": episode["episode_id"], "scenario": episode["scenario"], "seed": episode["seed"],
        "capacity": episode["capacity"], "pressure_factor": episode["pressure_factor"],
        "q1_utility": q1_utility, "q1_full_logp": q1_full_logp, "q1_removed_logp": q1_removed_logp,
        "q1_answer_correct": _query_event({"trace": manager.trace}, "q1").get("model_answer_correct"),
    })
    return {"episode_id": episode["episode_id"], "policy": policy, "metrics": metrics, "trace": manager.trace}


def preflight_cell(episode: dict[str, Any], rmm: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    rmm_post, task_post = _post_use_event(rmm), _post_use_event(task)
    rmm_scores = dict(rmm_post["policy_scores"])
    task_scores = dict(task_post["policy_scores"])
    all_ids = sorted(set(rmm_scores) | set(task_scores))
    xs = [float(rmm_scores.get(block_id, 0.0)) for block_id in all_ids]
    ys = [float(task_scores.get(block_id, 0.0)) for block_id in all_ids]
    top_k = episode["capacity"] // 2
    rmm_top, task_top = set(_ranked(rmm_scores, top_k)), set(_ranked(task_scores, top_k))
    rmm_q23 = set(_query_event(rmm, "q2")["hot_ids_before"]) | set(_query_event(rmm, "q3")["hot_ids_before"])
    task_q23 = set(_query_event(task, "q2")["hot_ids_before"]) | set(_query_event(task, "q3")["hot_ids_before"])
    rmm_evictions = [event["block_id"] for event in rmm["trace"] if event.get("type") == "evict"]
    task_evictions = [event["block_id"] for event in task["trace"] if event.get("type") == "evict"]
    rank_reversals = 0
    for index, left in enumerate(all_ids):
        for right in all_ids[index + 1:]:
            if rmm_scores.get(left, 0.0) > rmm_scores.get(right, 0.0) and task_scores.get(right, 0.0) > task_scores.get(left, 0.0):
                rank_reversals += 1
    outcome_diff = any(
        rmm["metrics"][name] != task["metrics"][name]
        for name in ("q2_hot_evidence_recall", "q3_hot_evidence_recall", "q2_answer_accuracy", "q3_answer_accuracy")
    )
    return {
        "episode_id": _episode_budget_key(episode), "scenario": episode["scenario"], "seed": episode["seed"],
        "capacity": episode["capacity"], "pressure_factor": episode["pressure_factor"],
        "pearson": _pearson(xs, ys), "spearman": _spearman(xs, ys),
        "top_k": top_k, "top_k_jaccard": _jaccard(rmm_top, task_top),
        "score_vectors_differ": xs != ys, "retained_set_disagreement": rmm_q23 != task_q23,
        "q2_retained_set_disagreement": set(_query_event(rmm, "q2")["hot_ids_before"]) != set(_query_event(task, "q2")["hot_ids_before"]),
        "q3_retained_set_disagreement": set(_query_event(rmm, "q3")["hot_ids_before"]) != set(_query_event(task, "q3")["hot_ids_before"]),
        "eviction_decision_disagreement": rmm_evictions != task_evictions,
        "rank_reversal_count": rank_reversals,
        "outcome_disagreement": outcome_diff,
        "rmm_scores": rmm_scores, "task_scores": task_scores,
    }


def run_preflight(episodes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    model = FrozenAnswerModel()
    cells: list[dict[str, Any]] = []
    for episode in episodes:
        rmm = run_episode(episode, "rmm_like", model)
        task = run_episode(episode, "task_utility", model)
        cells.append(preflight_cell(episode, rmm, task))
    n = len(cells)
    summary = {
        "cells": n,
        "score_vector_disagreement": sum(cell["score_vectors_differ"] for cell in cells),
        "retained_set_disagreement": sum(cell["retained_set_disagreement"] for cell in cells),
        "eviction_decision_disagreement": sum(cell["eviction_decision_disagreement"] for cell in cells),
        "outcome_disagreement": sum(cell["outcome_disagreement"] for cell in cells),
        "mean_pearson": statistics.mean(cell["pearson"] for cell in cells if cell["pearson"] is not None),
        "mean_spearman": statistics.mean(cell["spearman"] for cell in cells if cell["spearman"] is not None),
        "mean_top_k_jaccard": statistics.mean(cell["top_k_jaccard"] for cell in cells),
        "rank_reversal_cells": sum(cell["rank_reversal_count"] > 0 for cell in cells),
    }
    summary["retained_set_disagreement_fraction"] = summary["retained_set_disagreement"] / n if n else 0.0
    summary["passed"] = summary["retained_set_disagreement_fraction"] >= CONFIG["preflight_disagreement_threshold"]
    return cells, summary


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    serializable = []
    for row in rows:
        serializable.append({key: json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else value for key, value in row.items()})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(serializable[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(serializable)


def aggregate(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    metrics = ["future_useful_retention", "q2_answer_accuracy", "q3_answer_accuracy", "q2_hot_evidence_recall", "q3_hot_evidence_recall", "eviction_regret", "retained_useless_blocks", "promotion_count", "eviction_count", "cold_blocks_total"]
    output = []
    for group, members in sorted(groups.items(), key=lambda item: tuple(str(x) for x in item[0])):
        row = {key: value for key, value in zip(keys, group)}; row["n"] = len(members)
        for metric in metrics:
            row[metric] = round(statistics.mean(float(member[metric]) for member in members), 6)
        output.append(row)
    return output


def _policy_row(rows: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    return next(row for row in rows if row["policy"] == policy)


def write_preflight_report(summary: dict[str, Any], cells: list[dict[str, Any]], path: Path) -> None:
    differing = [cell for cell in cells if cell["retained_set_disagreement"]]
    lines = [
        "# Phase 1R Pre-flight Gate", "",
        "本文件只报告 RMM-like 与 Task Utility 是否在新定义下产生真实决策分歧；正式 policy comparison 只有在 gate 通过后才允许运行。", "",
        f"- Episode-budget cells: `{summary['cells']}`",
        f"- Score-vector disagreement: `{summary['score_vector_disagreement']}/{summary['cells']}`",
        f"- Retained-set disagreement: `{summary['retained_set_disagreement']}/{summary['cells']}` = `{summary['retained_set_disagreement_fraction']:.3f}`",
        f"- Eviction-decision disagreement: `{summary['eviction_decision_disagreement']}/{summary['cells']}`",
        f"- Mean Pearson: `{summary['mean_pearson']:.4f}`; mean Spearman: `{summary['mean_spearman']:.4f}`",
        f"- Mean Top-K Jaccard: `{summary['mean_top_k_jaccard']:.4f}`",
        f"- Cells with rank reversal: `{summary['rank_reversal_cells']}`",
        "",
        f"## Gate: {'PASS' if summary['passed'] else 'FAIL'}",
        "",
        f"Threshold: retained-set disagreement >= `{CONFIG['preflight_disagreement_threshold']:.2f}`.", "",
        "The RMM-like signal is a block-level adaptation of correctness-weighted attention after q1; correctness is computed by the frozen answer model. It is not the original token-level fixed-lag RMM implementation, and the difference is recorded here rather than hidden.", "",
        "## Disagreement examples", "",
        "| episode | scenario | capacity | pressure | RMM scores | Task scores |", "|---|---|---:|---:|---|---|",
    ]
    for cell in differing[:10]:
        lines.append(f"| {cell['episode_id']} | {cell['scenario']} | {cell['capacity']} | {cell['pressure_factor']} | `{cell['rmm_scores']}` | `{cell['task_scores']}` |")
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def report_markdown(config: dict[str, Any], preflight: dict[str, Any], rows: list[dict[str, Any]], conditional_rows: list[dict[str, Any]], path: Path) -> None:
    policy_summary = aggregate(rows, ("policy",))
    conditional_summary = aggregate(conditional_rows, ("policy",)) if conditional_rows else []
    rmm = _policy_row(policy_summary, "rmm_like"); task = _policy_row(policy_summary, "task_utility")
    rmm_cond = next((row for row in conditional_summary if row["policy"] == "rmm_like"), None)
    task_cond = next((row for row in conditional_summary if row["policy"] == "task_utility"), None)
    task_wins_retention = bool(task_cond and rmm_cond and task_cond["future_useful_retention"] > rmm_cond["future_useful_retention"])
    task_wins_accuracy = bool(task_cond and rmm_cond and (task_cond["q2_answer_accuracy"] + task_cond["q3_answer_accuracy"]) > (rmm_cond["q2_answer_accuracy"] + rmm_cond["q3_answer_accuracy"]))
    paired_conditional = []
    if conditional_rows:
        by_episode = {row["episode_id"]: row for row in conditional_rows}
        for episode_id in sorted({row["episode_id"] for row in conditional_rows}):
            episode_rows = {row["policy"]: row for row in conditional_rows if row["episode_id"] == episode_id}
            if "rmm_like" in episode_rows and "task_utility" in episode_rows:
                paired_conditional.append((episode_rows["task_utility"], episode_rows["rmm_like"]))
    retention_wins = sum(task_row["future_useful_retention"] > rmm_row["future_useful_retention"] for task_row, rmm_row in paired_conditional)
    accuracy_wins = sum(
        (task_row["q2_answer_accuracy"] + task_row["q3_answer_accuracy"]) > (rmm_row["q2_answer_accuracy"] + rmm_row["q3_answer_accuracy"])
        for task_row, rmm_row in paired_conditional
    )
    baseline_saturated = all(_policy_row(policy_summary, policy)["future_useful_retention"] == 0 for policy in ("recency", "frequency", "attention"))
    if not preflight["passed"]:
        verdict = "NON-IDENTIFIABLE AGAIN"
    elif task_wins_retention or task_wins_accuracy:
        verdict = "CONDITIONAL GO"
    else:
        verdict = "NO-GO"
    lines = [
        "# Phase 1R — Discriminative Principle Test", "",
        "本实验只验证 q1 后两种 utility policy 是否真正可区分及其最小 downstream 后果；没有 Transformer 训练、GPU、硬件 tier 或大型模型。", "",
        "## Pre-flight gate", "",
        f"Retained-set disagreement: `{preflight['retained_set_disagreement']}/{preflight['cells']}` = `{preflight['retained_set_disagreement_fraction']:.3f}`; threshold `{config['preflight_disagreement_threshold']:.2f}`; gate **{'PASS' if preflight['passed'] else 'FAIL'}**.", "",
        "## Frozen answer model and signals", "",
        "Task Utility uses a fixed lexical answer scorer. For every q1 candidate block it recomputes gold-answer log probability after masking that block; utility is `logp(full) - logp(masked)`. No 1/n coverage label is used.", "",
        "RMM-like is a block-level adaptation of RMM's demonstrated correctness-weighted attention: q1 attention mass is multiplied by the frozen model's computed q1 correctness after q1. It is not a reproduction of RMM's token-level fixed-lag buffer or training procedure; that difference limits the claim.", "",
        "All policies receive the same q1 candidate set and `capacity//2` post-use admission slots. Recency, frequency, attention, RMM-like, and task utility update their own signal after q1; none receives q2/q3 labels.", "",
        "## Results — all episodes", "",
        "| policy | n | future retention | q2 acc | q3 acc | eviction regret | retained useless | cold blocks |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in policy_summary:
        lines.append(f"| {row['policy']} | {row['n']} | {row['future_useful_retention']:.3f} | {row['q2_answer_accuracy']:.3f} | {row['q3_answer_accuracy']:.3f} | {row['eviction_regret']:.3f} | {row['retained_useless_blocks']:.3f} | {row['cold_blocks_total']:.1f} |")
    lines += ["", "## Results — episodes with RMM/Task retained-set disagreement", ""]
    if conditional_summary:
        lines += ["| policy | n | future retention | q2 acc | q3 acc | eviction regret |", "|---|---:|---:|---:|---:|---:|"]
        for row in conditional_summary:
            lines.append(f"| {row['policy']} | {row['n']} | {row['future_useful_retention']:.3f} | {row['q2_answer_accuracy']:.3f} | {row['q3_answer_accuracy']:.3f} | {row['eviction_regret']:.3f} |")
        denominator = len(paired_conditional)
        lines += [
            "", "### Conditional-on-disagreement win rate", "",
            f"- Task Utility future-retention wins over RMM-like: `{retention_wins}/{denominator}` = `{retention_wins / denominator:.3f}`.",
            f"- Task Utility combined q2/q3 accuracy wins over RMM-like: `{accuracy_wins}/{denominator}` = `{accuracy_wins / denominator:.3f}`.",
        ]
    else:
        lines.append("No disagreement subset exists; the gate failed and formal run was not permitted.")
    lines += [
        "", "## Required failure checks", "",
        f"- Recency/frequency/attention baseline saturation: **{'YES' if baseline_saturated else 'NO'}**. q1 post-use admission was shared, so a zero result would be a benchmark semantic failure rather than a general claim about these signals.",
        "- Synthetic scenarios include high-attention causally useless candidates, low-attention necessary evidence, redundant evidence, obsolete-after-q1 state, related non-identical q2/q3, frequent useless distractors, and delayed reuse.",
        "- `oracle_future_reuse` is an upper bound and receives future labels by construction.",
        "", "## Representative failure cases", "",
        "- `cross_event`: the frozen lexical model gives q1 utility to `B` but zero to `A`, because `B` also contains the token `ALPHA`. The q2 query later needs `A` and `C`; this exposes the limit of lexical counterfactual attribution, not evidence that a semantic answer model would make the same assignment.",
        "- `redundant_evidence`: removing either q1 copy leaves the gold answer supported by the other copy, so both task utilities are zero. q2/q3 later request the `B` copy, which is deliberately future-specific and cannot be predicted from q1 utility alone.",
        "- `obsolete_information`: q1 utility correctly identifies the old state for q1, while q2/q3 require a state written after q1. Promotion cannot solve this first-time future information case.",
        "", "## Verdict", "", f"**{verdict}**.", "",
        "The conditional win check requires Task Utility to beat RMM-like on future retention or combined q2/q3 answer accuracy inside the actual disagreement subset. This does not establish a deployable utility predictor or an internal Transformer contribution.",
        "", "The run is complete. Do not add hierarchy, decay, hardware tier, or a larger benchmark in this phase.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--formal", action="store_true")
    args = parser.parse_args()
    episodes = generate_episodes(
        seeds=CONFIG["seed_list"], capacities=CONFIG["capacities"], pressure_factors=CONFIG["pressure_factors"],
        scenarios=CONFIG["scenarios"], sizes=CONFIG["block_sizes"],
    )
    output_root = HERE / "results" / "full"
    output_root.mkdir(parents=True, exist_ok=True)
    if args.preflight_only:
        cells, summary = run_preflight(episodes)
        write_json(summary, output_root / "preflight_summary.json")
        write_csv(cells, output_root / "metrics" / "preflight_cells.csv")
        write_preflight_report(summary, cells, REPORT_DIR / "phase1r_preflight.md")
        print(json.dumps({"mode": "preflight", **summary, "report": str(REPORT_DIR / "phase1r_preflight.md")}, indent=2))
        return
    preflight_path = output_root / "preflight_summary.json"
    if not preflight_path.exists():
        raise SystemExit("Refusing formal run: execute --preflight-only first.")
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if not preflight.get("passed"):
        raise SystemExit("NON-IDENTIFIABLE AGAIN: pre-flight retained-set disagreement is below threshold; formal run not started.")
    model = FrozenAnswerModel()
    results = [run_episode(episode, policy, model) for episode in episodes for policy in POLICIES]
    rows = [result["metrics"] for result in results]
    cells, _ = run_preflight(episodes)
    disagreement_ids = {cell["episode_id"] for cell in cells if cell["retained_set_disagreement"]}
    conditional_rows = [row for row in rows if row["episode_id"] in disagreement_ids]
    write_json(episodes, output_root / "data" / "episodes.json")
    with (output_root / "raw_traces.jsonl").open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    write_csv(aggregate(rows, ("policy",)), output_root / "metrics" / "summary_by_policy.csv")
    write_csv(aggregate(rows, ("scenario", "policy")), output_root / "metrics" / "summary_by_scenario_policy.csv")
    write_csv(aggregate(conditional_rows, ("policy",)) if conditional_rows else [], output_root / "metrics" / "summary_conditional_disagreement.csv")
    manifest = {"episode_count": len(episodes), "run_count": len(results), "config": CONFIG, "preflight": preflight}
    manifest["raw_trace_sha256"] = hashlib.sha256((output_root / "raw_traces.jsonl").read_bytes()).hexdigest()
    write_json(manifest, output_root / "manifest.json")
    report_path = REPORT_DIR / "phase1r_discriminative_principle_test.md"
    report_markdown(CONFIG, preflight, rows, conditional_rows, report_path)
    print(json.dumps({"mode": "formal", "episodes": len(episodes), "runs": len(results), "conditional_cells": len(disagreement_ids), "report": str(report_path)}, indent=2))


if __name__ == "__main__":
    main()
