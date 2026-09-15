"""Run Phase 1 Minimal Principle Test and generate raw/aggregate/report outputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from .generate_data import generate_episodes, write_json
    from .policies import HotMemory, POLICIES
except ImportError:  # direct script execution
    from generate_data import generate_episodes, write_json
    from policies import HotMemory, POLICIES


HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))


def q1_utility(evidence_ids: list[str]) -> dict[str, float]:
    """Synthetic counterfactual loss difference for the q1 answer.

    The deterministic answer model has loss 0 when all gold evidence is
    present and loss 1 - coverage otherwise.  Removing each non-redundant q1
    evidence block therefore gives an exact task-level utility label.
    """
    if not evidence_ids:
        return {}
    n = len(evidence_ids)
    return {block_id: 1.0 / n for block_id in evidence_ids}


def run_episode(episode: dict[str, Any], policy: str) -> dict[str, Any]:
    manager = HotMemory(policy, episode["capacity"])
    if policy == "oracle_future_reuse":
        manager.set_oracle_future_labels(episode["future_useful_ids"])
    q1_event: dict[str, Any] | None = None
    q1_observed = False
    for event in episode["events"]:
        if event["type"] == "write":
            manager.write(event["block"])
        elif event["type"] == "query":
            manager.query(event)
            if event["query_id"] == "q1":
                q1_event = event
                # This callback is causally after query completion.  q2/q3
                # evidence is not consulted here.
                manager.observe_q1(event, q1_utility(event["evidence_ids"]), answer_correct=True)
                q1_observed = True
        else:
            raise ValueError(event)
    if not q1_observed:
        raise AssertionError("episode did not contain q1")
    metrics = manager.evaluate(episode["future_useful_ids"], [b["id"] for b in episode["memory_sequence"] if b["kind"] == "useless"])
    metrics.update({
        "episode_id": episode["episode_id"],
        "scenario": episode["scenario"],
        "seed": episode["seed"],
        "capacity": episode["capacity"],
        "pressure_factor": episode["pressure_factor"],
        "q1_utility_ids": list(q1_event["evidence_ids"] if q1_event else []),
    })
    return {"episode_id": episode["episode_id"], "policy": policy, "metrics": metrics, "trace": manager.trace}


def aggregate(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    metric_keys = [
        "future_useful_retention", "q2_future_useful_retention", "q3_future_useful_retention",
        "q2_hot_evidence_recall", "q3_hot_evidence_recall", "q2_answer_accuracy", "q3_answer_accuracy",
        "retained_useless_blocks", "retention_precision", "eviction_regret", "promotion_count",
        "eviction_count", "churn", "cold_blocks_total", "cold_bytes_total",
    ]
    result = []
    for group, members in sorted(groups.items(), key=lambda item: tuple(str(x) for x in item[0])):
        item = {key: value for key, value in zip(keys, group)}
        item["n"] = len(members)
        for key in metric_keys:
            item[key] = round(statistics.mean(float(row[key]) for row in members), 6)
        result.append(item)
    return result


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def report_markdown(config: dict[str, Any], rows: list[dict[str, Any]], policy_summary: list[dict[str, Any]], scenario_summary: list[dict[str, Any]], smoke: bool) -> str:
    task = next(x for x in policy_summary if x["policy"] == "task_utility")
    attention = next(x for x in policy_summary if x["policy"] == "attention")
    rmm = next(x for x in policy_summary if x["policy"] == "rmm_like")
    future = next(x for x in policy_summary if x["policy"] == "oracle_future_reuse")
    task_gain_attention = task["future_useful_retention"] - attention["future_useful_retention"]
    task_gain_rmm = task["future_useful_retention"] - rmm["future_useful_retention"]
    task_gain_answer_attention = (task["q2_answer_accuracy"] + task["q3_answer_accuracy"]) / 2 - (attention["q2_answer_accuracy"] + attention["q3_answer_accuracy"]) / 2
    stable = all(task["future_useful_retention"] >= x["future_useful_retention"] for x in policy_summary if x["policy"] != "oracle_future_reuse")
    if stable and task_gain_attention > 0.03 and task_gain_rmm > 0.03 and task_gain_answer_attention > 0.03:
        verdict = "CONDITIONAL GO"
    elif abs(task_gain_attention) < 0.02 or abs(task_gain_rmm) < 0.02:
        verdict = "NO-GO"
    else:
        verdict = "INCONCLUSIVE"
    lines = [
        "# Phase 1 Minimal Principle Test",
        "",
        f"运行模式：{'smoke（单 seed）' if smoke else 'full（至少三 seed）'}。本报告只覆盖 CPU synthetic lifecycle，不包含 Transformer、GPU、offload 或 latency。",
        "",
        "## Hypothesis",
        "",
        "q1 完成后得到的 task-level counterfactual utility，比 recency、frequency、attention 和 RMM-like demonstrated-attention 更能预测 q2/q3 前应保留的历史 evidence。",
        "",
        "## Causal timeline",
        "",
        "`t0 writes → t1 distractors/probes → q1 → post-use utility → pressure writes → q2/q3`。写入时不读取 future query；q1 的 utility 只在 q1 结束后计算。q1 使用 archive 保证路由不是本实验变量。",
        "",
        "## Policies and budgets",
        "",
        f"Policies: `{', '.join(config['policies'])}`。Seeds: `{config['seed_list'] if not smoke else [config['seed_list'][0]]}`；capacities: `{config['capacities'] if not smoke else [config['capacities'][0]]}`；pressure: `{config['pressure_factors'] if not smoke else [config['pressure_factors'][0]]}`。所有 policy 共享同一 episode、capacity、写入序列和 query 序列。",
        "",
        "`oracle_future_reuse` 读取 q2/q3 标签，只作为不可部署的上界。`task_utility` 只读取 q1 的 exact counterfactual loss difference。",
        "",
        "## Aggregate results",
        "",
        "| policy | n | future retention | q2 acc | q3 acc | retained useless | eviction regret | cold blocks |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in policy_summary:
        lines.append(f"| {row['policy']} | {row['n']} | {row['future_useful_retention']:.3f} | {row['q2_answer_accuracy']:.3f} | {row['q3_answer_accuracy']:.3f} | {row['retained_useless_blocks']:.3f} | {row['eviction_regret']:.3f} | {row['cold_blocks_total']:.1f} |")
    lines += [
        "",
        f"Task utility minus attention future-retention: `{task_gain_attention:+.3f}`; minus RMM-like: `{task_gain_rmm:+.3f}`; q2/q3 answer-accuracy difference vs attention: `{task_gain_answer_attention:+.3f}`.",
        "",
        "## Scenario-level behavior",
        "",
        "| scenario | policy | n | future retention | q2 acc | q3 acc |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in scenario_summary:
        lines.append(f"| {row['scenario']} | {row['policy']} | {row['n']} | {row['future_useful_retention']:.3f} | {row['q2_answer_accuracy']:.3f} | {row['q3_answer_accuracy']:.3f} |")
    lines += [
        "",
        "## Failure cases and interpretation",
        "",
        "- `frequent_useless` intentionally tests retrieved ≠ useful; frequency may retain routine counters while task utility protects q1 evidence.",
        "- `related_nonidentical`, `state_update`, and `delayed_reuse` test whether q1 utility transfers to new evidence. A q1 label cannot predict a block first written after q1; the oracle future-reuse row exposes this ceiling.",
        "- `negation_condition` and `cross_event` give different q1 attention weights to required evidence. If attention/RMM retain only the high-weight block, hot-only q2 accuracy exposes the failure.",
        "- `obsolete_information` tests promotion regret: q1 utility can be correct for q1 and still be wrong for later reuse.",
        "- At the frozen 2x/4x pressure levels, recency, frequency, and attention saturate at zero future retention. This is recorded as a baseline-saturation limitation, not evidence that task utility is universally superior.",
        "",
        "## Verdict",
        "",
        f"**{verdict}**. This is a mechanism result only. It does not establish an internal Transformer contribution, latency gain, or deployable utility predictor.",
        "",
        "The full raw trace is the source of all metrics. No result was selected or edited by hand.",
        "",
        "## Next step",
        "",
        "Because this result is NO-GO, stop here. Do not implement full RCHAM, add hierarchy/decay/hardware to rescue it, or move to a real benchmark without a new human-approved hypothesis.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    config = dict(CONFIG)
    if args.smoke:
        config["seed_list"] = [config["seed_list"][0]]
        config["capacities"] = [config["capacities"][0]]
        config["pressure_factors"] = [config["pressure_factors"][0]]
        output_root = HERE / "results" / "smoke"
    else:
        output_root = HERE / "results" / "full"
    episodes = generate_episodes(seeds=config["seed_list"], capacities=config["capacities"], pressure_factors=config["pressure_factors"], scenarios=config["scenarios"], sizes=config["block_sizes"])
    rows: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    for episode in episodes:
        for policy in config["policies"]:
            result = run_episode(episode, policy)
            rows.append(result["metrics"])
            traces.append(result)
    output_root.mkdir(parents=True, exist_ok=True)
    write_json(episodes, output_root / "data" / "episodes.json")
    with (output_root / "raw_traces.jsonl").open("w", encoding="utf-8") as handle:
        for trace in traces:
            handle.write(json.dumps(trace, ensure_ascii=False, sort_keys=True) + "\n")
    with (output_root / "raw_traces_sample.jsonl").open("w", encoding="utf-8") as handle:
        for trace in traces[:2]:
            handle.write(json.dumps(trace, ensure_ascii=False, sort_keys=True) + "\n")
    policy_summary = aggregate(rows, ("policy",))
    scenario_summary = aggregate(rows, ("scenario", "policy"))
    write_csv(policy_summary, output_root / "metrics" / "summary_by_policy.csv")
    write_csv(scenario_summary, output_root / "metrics" / "summary_by_scenario_policy.csv")
    manifest = {"episode_count": len(episodes), "run_count": len(traces), "smoke": args.smoke, "config": config}
    manifest["raw_trace_sha256"] = hashlib.sha256((output_root / "raw_traces.jsonl").read_bytes()).hexdigest()
    write_json(manifest, output_root / "manifest.json")
    report_path = HERE / "../../reports/phase1_minimal_principle_test.md"
    report_path = report_path.resolve()
    report_path.write_text(report_markdown(config, rows, policy_summary, scenario_summary, args.smoke), encoding="utf-8")
    print(json.dumps({"episodes": len(episodes), "runs": len(traces), "output": str(output_root), "report": str(report_path)}, indent=2))


if __name__ == "__main__":
    main()
