"""Deterministic synthetic temporal episodes for Phase 1A.

The generator deliberately keeps future query labels out of write events.  The
controller receives exact evidence IDs only at query time (perfect routing),
and receives oracle utility only in the explicit post-q1 utility event.
"""

from __future__ import annotations

import copy
import json
import random
from pathlib import Path
from typing import Any, Iterable


WRITE_KEYS = {
    "id",
    "kind",
    "payload",
    "embedding",
    "raw_bytes",
    "compressed_bytes",
    "hot_bytes",
}
DELAY_WRITES = {"short": 0, "medium": 1, "long": 4}


def _embedding(rng: random.Random, salt: int) -> list[float]:
    """Stable, small synthetic vectors; routing itself is perfect in Phase 1A."""
    return [round(rng.random() + salt * 0.001, 6) for _ in range(4)]


def _block(
    rng: random.Random,
    block_id: str,
    kind: str,
    payload: str,
    sizes: dict[str, int],
) -> dict[str, Any]:
    # This is the only shape made visible to a write event.  It intentionally
    # contains no future query, answer, utility, or scenario labels.
    return {
        "id": block_id,
        "kind": kind,
        "payload": payload,
        "embedding": _embedding(rng, len(block_id)),
        "raw_bytes": sizes["raw_bytes"],
        "compressed_bytes": sizes["compressed_bytes"],
        "hot_bytes": sizes["hot_bytes"],
    }


def _query(
    query_id: str,
    question: str,
    evidence_ids: Iterable[str],
    *,
    stage: str,
    role: str,
) -> dict[str, Any]:
    return {
        "type": "query",
        "time": "t2" if stage == "q1" else "t5",
        "query_id": query_id,
        "stage": stage,
        "question": question,
        "evidence_ids": list(evidence_ids),
        "query_role": role,
    }


def _scenario_spec(scenario: str, capacity: int) -> tuple[list[tuple[str, str]], list[str], list[str], list[tuple[str, str, list[str], str]]]:
    """Return (extra blocks, future useful ids, useless ids, q2/q3 specs)."""
    # q1 is intentionally worded differently from q2 and q3.  The evidence
    # relation, rather than lexical overlap, is what is being tested.
    if scenario == "repeated_useful":
        return (
            [],
            ["M"],
            [],
            [
                ("q2", "During the later audit, which archive identifier must the reviewer use for the same record?", ["M"], "recurrent_use"),
                ("q3", "Which identifier should be paired with the region for final reconciliation?", ["M"], "recurrent_use"),
            ],
        )
    if scenario == "related_nonidentical":
        return (
            [("R", "related fact")],
            ["M", "R"],
            [],
            [
                ("q2", "Which archive code and linked region are required for the later transfer?", ["M", "R"], "related_evidence"),
                ("q3", "For the handoff, what identifier must be joined to the regional note?", ["R", "M"], "related_evidence"),
            ],
        )
    if scenario == "useless_distractor":
        ids = [f"D{i}" for i in range(max(4, capacity + 4))]
        return (
            [(block_id, "frequently retrieved distractor") for block_id in ids],
            ["M"],
            ids,
            [
                ("q2", "After the review queue changes, which archive code resolves the original case?", ["M"], "recurrent_use"),
                ("q3", "Which code is required to close the case after the distractor checks?", ["M"], "recurrent_use"),
            ],
        )
    if scenario == "obsolete_target":
        return (
            [("O", "superseding state"), ("O2", "final superseding state")],
            ["O", "O2"],
            [],
            [
                ("q2", "What is the superseding state after the original record is retired?", ["O"], "obsolete_target"),
                ("q3", "Which final state should the reconciliation report use?", ["O2"], "obsolete_target"),
            ],
        )
    if scenario == "delayed_second_use":
        return (
            [("R", "intervening related fact")],
            ["M", "R"],
            [],
            [
                ("q2", "Which regional note is linked during the intermediate review?", ["R"], "intervening_use"),
                ("q3", "After the delayed review, which original archive code is needed again?", ["M"], "delayed_reuse"),
            ],
        )
    if scenario == "competing_useful":
        return (
            [(f"C{i}", "competing useful fact") for i in range(1, 4)],
            ["M", "C1", "C2", "C3"],
            [],
            [
                ("q2", "Which archive code must be combined with the second competing record?", ["M", "C2"], "competing_use"),
                ("q3", "Which records are needed to close the third competing case?", ["M", "C3"], "competing_use"),
            ],
        )
    raise ValueError(f"unknown scenario: {scenario}")


def generate_episode(
    *,
    seed: int,
    capacity: int,
    pressure_factor: int,
    delay: str,
    scenario: str,
    sizes: dict[str, int] | None = None,
) -> dict[str, Any]:
    sizes = sizes or {"hot_bytes": 128, "compressed_bytes": 16, "raw_bytes": 256}
    rng = random.Random(seed)
    extras, future_useful_ids, useless_ids, q_specs = _scenario_spec(scenario, capacity)
    writes: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []

    target = _block(rng, "M", "target", "archive code ALPHA-17 for the original record", sizes)
    writes.append(target)
    events.append({"type": "write", "time": "t0", "block": copy.deepcopy(target)})

    # t1 ensures M is evicted from hot storage before q1 in every policy.
    t1_count = max(capacity + 2, pressure_factor * capacity)
    t1_blocks: list[dict[str, Any]] = []
    for i in range(t1_count):
        block = _block(rng, f"T1_{i}", "t1_distractor", f"unrelated history item {i}", sizes)
        t1_blocks.append(block)
        writes.append(block)
        events.append({"type": "write", "time": "t1", "block": copy.deepcopy(block)})

    # Scenario-specific blocks are written after q1, except the useless
    # distractors which are queried repeatedly to expose count-policy error.
    q1 = _query(
        "q1",
        "At the initial checkpoint, which archive code was assigned to the original record?",
        ["M"],
        stage="q1",
        role="first_cold_use",
    )
    events.append(q1)
    events.append({"type": "utility", "time": "t3", "for_query": "q1", "utility_ids": ["M"]})

    # Make distractor blocks available after q1, then query them.  They are
    # frequent retrievals but deliberately have empty oracle utility.
    for block_id, kind in extras:
        block = _block(rng, block_id, kind, f"payload for {block_id}", sizes)
        writes.append(block)
        events.append({"type": "write", "time": "t4", "block": copy.deepcopy(block)})
        if scenario == "useless_distractor":
            events.append(
                _query(
                    f"qd_{block_id}",
                    f"Which routine check mentions {block_id}?",
                    [block_id],
                    stage="distractor",
                    role="frequent_useless_retrieval",
                )
            )

    # Additional pressure is shared across all policies by virtue of the same
    # event stream.  It is intentionally larger than Tier 1 capacity.
    delay_count = DELAY_WRITES[delay] * capacity
    for i in range(delay_count + pressure_factor * capacity):
        block = _block(rng, f"P_{i}", "pressure", f"post checkpoint pressure item {i}", sizes)
        writes.append(block)
        events.append({"type": "write", "time": "t4", "block": copy.deepcopy(block)})

    for query_id, question, evidence, role in q_specs:
        events.append(_query(query_id, question, evidence, stage=query_id, role=role))

    # Metadata is kept outside block write payloads, so it is available to the
    # evaluator but never leaked to the controller at write time.
    return {
        "episode_id": f"{scenario}-s{seed}-c{capacity}-p{pressure_factor}-{delay}",
        "seed": seed,
        "scenario": scenario,
        "capacity": capacity,
        "pressure_factor": pressure_factor,
        "delay": delay,
        "future_useful_ids": future_useful_ids,
        "useless_ids": useless_ids,
        "memory_sequence": writes,
        "events": events,
    }


def generate_episodes(
    *,
    seeds: Iterable[int],
    capacities: Iterable[int],
    pressure_factors: Iterable[int],
    delays: Iterable[str],
    scenarios: Iterable[str],
    sizes: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    episodes = []
    for seed in seeds:
        for capacity in capacities:
            for pressure_factor in pressure_factors:
                for delay in delays:
                    for scenario in scenarios:
                        episodes.append(
                            generate_episode(
                                seed=seed,
                                capacity=capacity,
                                pressure_factor=pressure_factor,
                                delay=delay,
                                scenario=scenario,
                                sizes=sizes,
                            )
                        )
    return episodes


def write_episodes(episodes: list[dict[str, Any]], path: str | Path) -> None:
    Path(path).write_text(json.dumps(episodes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    research_root = Path(__file__).resolve().parents[2]
    config_path = research_root / "experiments" / "phase1a" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    episodes = generate_episodes(
        seeds=config["seed_list"],
        capacities=config["capacities"],
        pressure_factors=config["pressure_factors"],
        delays=config["delays"],
        scenarios=config["scenarios"],
        sizes=config["block_sizes"],
    )
    write_episodes(episodes, research_root / "experiments" / "phase1a" / "data" / "episodes.json")
    print(f"wrote {len(episodes)} episodes")
