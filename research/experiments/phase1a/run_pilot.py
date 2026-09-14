"""Run the deterministic Phase 1A controller pilot and write reproducible outputs."""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    # Add research/ so ``experiments`` resolves as a namespace package.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiments.phase1a.controllers import POLICIES, MemoryController
from experiments.phase1a.generate_data import generate_episodes, write_episodes


HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def run_episode(episode: dict[str, Any], policy: str, config: dict[str, Any]) -> dict[str, Any]:
    controller = MemoryController(
        policy,
        episode["capacity"],
        decay_factor=config["decay_factor"],
        decay_threshold=config["utility_decay_threshold"],
        cooldown_steps=config["cooldown_steps"],
    )
    query_positions: dict[str, int] = {}
    utility_positions: dict[str, int] = {}
    for event in episode["events"]:
        if event["type"] == "write":
            controller.write(event["block"])
        elif event["type"] == "query":
            query_positions[event["query_id"]] = len(controller.trace)
            controller.query(event)
        elif event["type"] == "utility":
            utility_positions[event["for_query"]] = len(controller.trace)
            controller.apply_utility(event["utility_ids"], query_id=event["for_query"])
        else:
            raise ValueError(f"unknown event type: {event['type']}")

    metrics = controller.metrics(
        future_useful_ids=episode["future_useful_ids"],
        useless_ids=episode["useless_ids"],
    )
    metrics.update(
        {
            "policy": policy,
            "episode_id": episode["episode_id"],
            "scenario": episode["scenario"],
            "seed": episode["seed"],
            "capacity": episode["capacity"],
            "pressure_factor": episode["pressure_factor"],
            "delay": episode["delay"],
            "q1_trace_position": query_positions.get("q1", -1),
            "q1_utility_trace_position": utility_positions.get("q1", -1),
        }
    )
    return {
        "episode_id": episode["episode_id"],
        "policy": policy,
        "scenario": episode["scenario"],
        "seed": episode["seed"],
        "capacity": episode["capacity"],
        "pressure_factor": episode["pressure_factor"],
        "delay": episode["delay"],
        "future_useful_ids": episode["future_useful_ids"],
        "useless_ids": episode["useless_ids"],
        "metrics": metrics,
        "trace": controller.trace,
    }


def aggregate(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    metric_keys = [
        "q2_target_survival",
        "q3_target_survival",
        "useful_memory_retention",
        "useless_memory_occupancy",
        "q2_hot_evidence_recall",
        "q3_hot_evidence_recall",
        "q2_cold_blocks",
        "q3_cold_blocks",
        "q2_cold_bytes",
        "q3_cold_bytes",
        "promotion_count",
        "demotion_count",
        "churn",
        "promotion_regret",
        "total_cold_reads",
        "total_cold_bytes",
        "total_blocks_accessed",
        "total_index_probes",
        "tier1_occupancy_q2",
        "tier1_occupancy_q3",
    ]
    output = []
    for group_key, members in sorted(groups.items(), key=lambda item: tuple(str(x) for x in item[0])):
        result = {key: value for key, value in zip(keys, group_key)}
        result["n"] = len(members)
        for metric in metric_keys:
            result[metric] = round(statistics.mean(float(row[metric]) for row in members), 6)
        output.append(result)
    return output


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def pairwise(policy_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_episode = {(row["episode_id"], row["policy"]): row for row in policy_rows}
    comparisons = [
        ("oracle_utility", "retrieval_count"),
        ("oracle_utility", "cold_raw_fallback_only"),
        ("oracle_utility", "perfect_routing_no_promotion"),
    ]
    output = []
    for left, right in comparisons:
        pairs = []
        for (episode_id, policy), row in by_episode.items():
            if policy == left and (episode_id, right) in by_episode:
                pairs.append((row, by_episode[(episode_id, right)]))
        if not pairs:
            continue
        result = {"left": left, "right": right, "n": len(pairs)}
        for metric in [
            "useful_memory_retention",
            "q2_target_survival",
            "q3_target_survival",
            "q2_cold_blocks",
            "q3_cold_blocks",
            "total_cold_reads",
            "churn",
            "promotion_regret",
        ]:
            result[f"delta_{metric}"] = round(statistics.mean(a[metric] - b[metric] for a, b in pairs), 6)
        output.append(result)
    return output


def main() -> None:
    config = load_config()
    episodes = generate_episodes(
        seeds=config["seed_list"],
        capacities=config["capacities"],
        pressure_factors=config["pressure_factors"],
        delays=config["delays"],
        scenarios=config["scenarios"],
        sizes=config["block_sizes"],
    )
    data_path = HERE / "data" / "episodes.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    write_episodes(episodes, data_path)
    (HERE / "data" / "episodes_manifest.json").write_text(
        json.dumps(
            {
                "episode_count": len(episodes),
                "episode_ids": [episode["episode_id"] for episode in episodes],
                "generator": "generate_data.py",
                "full_data_file": "episodes.json",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    traces: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for episode in episodes:
        for policy in config["policies"]:
            trace = run_episode(episode, policy, config)
            traces.append(trace)
            rows.append(trace["metrics"])

    raw_dir = HERE / "results" / "raw"
    metrics_dir = HERE / "results" / "metrics"
    raw_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    with (raw_dir / "traces.jsonl").open("w", encoding="utf-8") as handle:
        for trace in traces:
            handle.write(json.dumps(trace, ensure_ascii=False, sort_keys=True) + "\n")
    (raw_dir / "traces_sample.jsonl").write_text(
        "".join(json.dumps(trace, ensure_ascii=False, sort_keys=True) + "\n" for trace in traces[:2]),
        encoding="utf-8",
    )

    policy_summary = aggregate(rows, ("policy",))
    scenario_summary = aggregate(rows, ("scenario", "policy"))
    write_csv(policy_summary, metrics_dir / "summary_by_policy.csv")
    write_csv(scenario_summary, metrics_dir / "summary_by_scenario_policy.csv")
    pair_rows = pairwise(rows)
    write_csv(pair_rows, metrics_dir / "pairwise.csv")

    pilot_summary = {
        "episode_count": len(episodes),
        "run_count": len(traces),
        "policies": list(config["policies"]),
        "config": config,
        "policy_summary": policy_summary,
        "pairwise": pair_rows,
        "notes": [
            "Perfect routing is shared by every policy; q1 is a cold access before utility.",
            "No latency claim is made; block accesses, cold reads and bytes are cost proxies.",
            "Phase 1B is not run by this script.",
        ],
    }
    (metrics_dir / "pilot_summary.json").write_text(
        json.dumps(pilot_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    hashes = {}
    for path in [data_path, raw_dir / "traces.jsonl"]:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        hashes[path.name] = {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}
    (raw_dir / "manifest.json").write_text(
        json.dumps(
            {
                "full_outputs_are_local_artifacts": True,
                "files": hashes,
                "sample_file": "traces_sample.jsonl",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"episodes": len(episodes), "runs": len(traces), "output": str(metrics_dir)}, indent=2))


if __name__ == "__main__":
    main()
