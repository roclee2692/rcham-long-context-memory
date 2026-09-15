"""Deterministic synthetic lifecycle episodes for Phase 1 Minimal Principle Test."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Iterable


SCENARIOS = (
    "repeated_useful",
    "related_nonidentical",
    "frequent_useless",
    "state_update",
    "negation_condition",
    "cross_event",
    "delayed_reuse",
    "obsolete_information",
)


def _block(block_id: str, kind: str, payload: str, rng: random.Random, sizes: dict[str, int]) -> dict[str, Any]:
    # No future question, answer, or utility label is included in a write.
    return {
        "id": block_id,
        "kind": kind,
        "payload": payload,
        "write_nonce": rng.randrange(1_000_000),
        "hot_bytes": sizes["hot_bytes"],
        "raw_bytes": sizes["raw_bytes"],
    }


def _query(
    query_id: str,
    question: str,
    evidence_ids: list[str],
    attention_weights: dict[str, float],
    role: str,
) -> dict[str, Any]:
    return {
        "type": "query",
        "query_id": query_id,
        "question": question,
        "evidence_ids": evidence_ids,
        "attention_weights": attention_weights,
        "role": role,
    }


def _scenario_plan(scenario: str) -> dict[str, Any]:
    """Only this evaluator-side plan knows future q2/q3 evidence."""
    if scenario == "repeated_useful":
        return {
            "initial": [("M", "target", "archive code ALPHA-17 identifies the original record")],
            "after_q1": [],
            "probes": [],
            "q1": ("At the first checkpoint, which archive code identifies the original record?", ["M"], {"M": 1.0}),
            "q2": ("During the later audit, which code is required for the same record?", ["M"], {"M": 1.0}),
            "q3": ("Which identifier closes the reconciliation for that record?", ["M"], {"M": 1.0}),
        }
    if scenario == "related_nonidentical":
        return {
            "initial": [("M", "target", "case ALPHA-17 belongs to the northern region"), ("R", "relation", "the northern region uses transfer lane N-4")],
            "after_q1": [("S", "state", "the later transfer is approved under state GREEN")],
            "probes": [],
            "q1": ("Which case and region relation was recorded at the first checkpoint?", ["M", "R"], {"M": 0.86, "R": 0.14}),
            "q2": ("Which case and newly approved transfer state are required for the later handoff?", ["M", "S"], {"M": 0.65, "S": 0.35}),
            "q3": ("Which regional lane and approved state must be joined in the handoff note?", ["R", "S"], {"R": 0.55, "S": 0.45}),
        }
    if scenario == "frequent_useless":
        return {
            "initial": [("M", "target", "archive code ALPHA-17 identifies the original record")]
            + [(f"U{i}", "useless", f"routine counter {i} has no case meaning") for i in range(3)],
            "after_q1": [],
            "probes": [(f"U{i}", f"Which routine counter was observed in check {j}?") for j in range(5) for i in range(3)],
            "q1": ("At the first checkpoint, which archive code identifies the original record?", ["M"], {"M": 1.0}),
            "q2": ("After the review queue changes, which code resolves the original case?", ["M"], {"M": 1.0}),
            "q3": ("Which code is required to close the case after routine checks?", ["M"], {"M": 1.0}),
        }
    if scenario == "state_update":
        return {
            "initial": [("M", "old_state", "the original permit is state BLUE")],
            "after_q1": [("O", "update", "a later signed update changes the permit to state GREEN")],
            "probes": [],
            "q1": ("What state did the permit have at the first checkpoint?", ["M"], {"M": 1.0}),
            "q2": ("What state should the updated permit have after the signed change?", ["O"], {"O": 1.0}),
            "q3": ("Which current state belongs in the final report?", ["O"], {"O": 1.0}),
        }
    if scenario == "negation_condition":
        return {
            "initial": [("P", "condition", "the policy permits transfer after approval"), ("N", "negation", "the exception is not active for this case")],
            "after_q1": [],
            "probes": [],
            "q1": ("Under the first review, which condition and negated exception apply?", ["P", "N"], {"P": 0.90, "N": 0.10}),
            "q2": ("Which exception status must be checked before transfer?", ["N"], {"N": 1.0}),
            "q3": ("Which permission and exception pair belongs in the audit record?", ["P", "N"], {"P": 0.90, "N": 0.10}),
        }
    if scenario == "cross_event":
        return {
            "initial": [("A", "event_a", "event A assigns case ALPHA"), ("B", "event_b", "event B moves ALPHA to lane N-4"), ("C", "event_c", "event C records reviewer J")],
            "after_q1": [],
            "probes": [],
            "q1": ("Which two events establish the initial case and lane chain?", ["A", "B"], {"A": 0.82, "B": 0.18}),
            "q2": ("Which case and reviewer are needed for the later audit?", ["A", "C"], {"A": 0.70, "C": 0.30}),
            "q3": ("Which lane and reviewer close the cross-event chain?", ["B", "C"], {"B": 0.60, "C": 0.40}),
        }
    if scenario == "delayed_reuse":
        return {
            "initial": [("M", "target", "archive code ALPHA-17 identifies the original record")],
            "after_q1": [("R", "intervening", "the regional reviewer signs note N-4")],
            "probes": [],
            "q1": ("Which archive code was assigned at the first checkpoint?", ["M"], {"M": 1.0}),
            "q2": ("Which reviewer note is linked during the intermediate review?", ["R"], {"R": 1.0}),
            "q3": ("After the delayed review, which original archive code is needed again?", ["M"], {"M": 1.0}),
        }
    if scenario == "obsolete_information":
        return {
            "initial": [("M", "old_state", "the original routing label is LEGACY")],
            "after_q1": [("O", "new_state", "a signed update replaces the routing label with CURRENT")],
            "probes": [],
            "q1": ("What routing label was recorded before the signed update?", ["M"], {"M": 1.0}),
            "q2": ("What routing label is valid after the signed update?", ["O"], {"O": 1.0}),
            "q3": ("Which current label should the final system use?", ["O"], {"O": 1.0}),
        }
    raise ValueError(f"unknown scenario: {scenario}")


def generate_episode(*, seed: int, capacity: int, pressure_factor: int, scenario: str, sizes: dict[str, int]) -> dict[str, Any]:
    rng = random.Random(seed)
    plan = _scenario_plan(scenario)
    events: list[dict[str, Any]] = []
    all_blocks: list[dict[str, Any]] = []

    for block_id, kind, payload in plan["initial"]:
        block = _block(block_id, kind, payload, rng, sizes)
        all_blocks.append(block)
        events.append({"type": "write", "time": "t0", "block": block})

    # Shared distractor stream creates pressure before q1.  The policy never
    # sees the scenario plan or future query labels.
    for i in range(capacity + 2):
        block = _block(f"T1_{i}", "distractor", f"unrelated history item {i}", rng, sizes)
        all_blocks.append(block)
        events.append({"type": "write", "time": "t1", "block": block})

    for block_id, question in plan["probes"]:
        events.append(_query(f"probe_{block_id}_{len(events)}", question, [block_id], {block_id: 1.0}, "pre_q1_probe"))

    q1_question, q1_evidence, q1_attention = plan["q1"]
    events.append(_query("q1", q1_question, q1_evidence, q1_attention, "first_unexpected"))

    for block_id, kind, payload in plan["after_q1"]:
        block = _block(block_id, kind, payload, rng, sizes)
        all_blocks.append(block)
        events.append({"type": "write", "time": "t4", "block": block})

    # Pressure is deliberately beyond the hot capacity.  For delayed reuse,
    # q2 is emitted before a second pressure burst so q3 tests persistence.
    pressure_count = pressure_factor * capacity
    for i in range(pressure_count):
        block = _block(f"P_{i}", "pressure", f"later history item {i}", rng, sizes)
        all_blocks.append(block)
        events.append({"type": "write", "time": "t4", "block": block})

    q2_question, q2_evidence, q2_attention = plan["q2"]
    events.append(_query("q2", q2_question, q2_evidence, q2_attention, "related_future"))

    if scenario == "delayed_reuse":
        for i in range(capacity):
            block = _block(f"P2_{i}", "late_pressure", f"late pressure item {i}", rng, sizes)
            all_blocks.append(block)
            events.append({"type": "write", "time": "t5", "block": block})

    q3_question, q3_evidence, q3_attention = plan["q3"]
    events.append(_query("q3", q3_question, q3_evidence, q3_attention, "related_future"))
    future_useful_ids = sorted(set(q2_evidence + q3_evidence))
    return {
        "episode_id": f"{scenario}-s{seed}-c{capacity}-p{pressure_factor}",
        "seed": seed,
        "capacity": capacity,
        "pressure_factor": pressure_factor,
        "scenario": scenario,
        "memory_sequence": all_blocks,
        "events": events,
        "future_useful_ids": future_useful_ids,
        "q1_evidence_ids": q1_evidence,
    }


def generate_episodes(*, seeds: Iterable[int], capacities: Iterable[int], pressure_factors: Iterable[int], scenarios: Iterable[str], sizes: dict[str, int]) -> list[dict[str, Any]]:
    return [
        generate_episode(seed=seed, capacity=capacity, pressure_factor=pressure_factor, scenario=scenario, sizes=sizes)
        for seed in seeds
        for capacity in capacities
        for pressure_factor in pressure_factors
        for scenario in scenarios
    ]


def write_json(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
