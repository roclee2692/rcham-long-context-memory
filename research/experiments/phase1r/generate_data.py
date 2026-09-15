"""Deterministic synthetic episodes for the Phase 1R discriminative test."""

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
    "redundant_evidence",
)


def _block(block_id: str, kind: str, payload: str, rng: random.Random, sizes: dict[str, int]) -> dict[str, Any]:
    # Future query, answer, and utility labels are never written into memory.
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
    gold_answer: str,
    evidence_ids: list[str],
    attention_weights: dict[str, float],
    role: str,
) -> dict[str, Any]:
    return {
        "type": "query",
        "query_id": query_id,
        "question": question,
        "gold_answer": gold_answer,
        "evidence_ids": evidence_ids,
        "answer_context_ids": list(attention_weights),
        "attention_weights": attention_weights,
        "role": role,
    }


def _scenario_plan(scenario: str) -> dict[str, Any]:
    """Evaluator-side plan; policies only receive events as they occur."""
    if scenario == "repeated_useful":
        return {
            "initial": [("M", "target", "archive code ALPHA17 identifies the original record")],
            "after_q1": [], "probes": [],
            "q1": ("Which archive code identifies the original record?", "ALPHA17", ["M"], {"M": 1.0}),
            "q2": ("Which code is required for the later audit?", "ALPHA17", ["M"], {"M": 1.0}),
            "q3": ("Which identifier closes reconciliation?", "ALPHA17", ["M"], {"M": 1.0}),
        }
    if scenario == "related_nonidentical":
        return {
            "initial": [
                ("M", "target", "case ALPHA17 belongs to northern region"),
                ("R", "relation", "northern region uses transfer lane N4"),
                ("U", "distractor", "routine counter has no case meaning"),
            ],
            "after_q1": [("S", "state", "later transfer is approved under state GREEN")], "probes": [],
            "q1": ("Which case, region, and lane were recorded?", "ALPHA17 northern region N4", ["M", "R"], {"M": 0.78, "R": 0.10, "U": 0.12}),
            "q2": ("Which case and newly approved state are needed?", "ALPHA17 GREEN", ["M", "S"], {"M": 0.6, "S": 0.4}),
            "q3": ("Which lane and approved state must be joined?", "N4 GREEN", ["R", "S"], {"R": 0.5, "S": 0.5}),
        }
    if scenario == "frequent_useless":
        return {
            "initial": [("M", "target", "archive code ALPHA17 identifies the original record")]
            + [(f"U{i}", "useless", f"routine counter {i} has no case meaning") for i in range(3)],
            "after_q1": [],
            "probes": [(f"U{i}", f"Which routine counter was observed in check {j}?") for j in range(4) for i in range(3)],
            "q1": ("Which archive code identifies the original record?", "ALPHA17", ["M"], {"M": 0.15, "U0": 0.50, "U1": 0.25, "U2": 0.10}),
            "q2": ("Which code resolves the original case?", "ALPHA17", ["M"], {"M": 1.0}),
            "q3": ("Which code closes the case?", "ALPHA17", ["M"], {"M": 1.0}),
        }
    if scenario == "state_update":
        return {
            "initial": [("M", "old_state", "original permit state BLUE")],
            "after_q1": [("O", "update", "signed update changes permit state to GREEN")], "probes": [],
            "q1": ("What state did the permit have at the first checkpoint?", "BLUE", ["M"], {"M": 1.0}),
            "q2": ("What state should the updated permit have?", "GREEN", ["O"], {"O": 1.0}),
            "q3": ("Which current state belongs in the final report?", "GREEN", ["O"], {"O": 1.0}),
        }
    if scenario == "negation_condition":
        return {
            "initial": [
                ("P", "condition", "policy permits transfer after approval"),
                ("N", "negation", "exception is not active for this case"),
                ("U", "distractor", "routine counter has no policy meaning"),
            ],
            "after_q1": [], "probes": [],
            "q1": ("Which permission and exception status apply?", "permits transfer not active", ["P", "N"], {"P": 0.78, "N": 0.10, "U": 0.12}),
            "q2": ("Which exception status must be checked?", "not active", ["N"], {"N": 1.0}),
            "q3": ("Which permission and exception pair belongs in the audit?", "permits transfer not active", ["P", "N"], {"P": 0.75, "N": 0.25}),
        }
    if scenario == "cross_event":
        return {
            "initial": [
                ("A", "event_a", "event A assigns case ALPHA"),
                ("B", "event_b", "event B moves ALPHA to lane N4"),
                ("C", "event_c", "event C records reviewer J"),
                ("U", "distractor", "routine event has no case meaning"),
            ],
            "after_q1": [], "probes": [],
            "q1": ("Which events establish the initial case and lane chain?", "ALPHA N4", ["A", "B"], {"A": 0.78, "B": 0.10, "C": 0.08, "U": 0.04}),
            "q2": ("Which case and reviewer are needed later?", "ALPHA J", ["A", "C"], {"A": 0.5, "C": 0.5}),
            "q3": ("Which lane and reviewer close the chain?", "N4 J", ["B", "C"], {"B": 0.5, "C": 0.5}),
        }
    if scenario == "delayed_reuse":
        return {
            "initial": [("M", "target", "archive code ALPHA17 identifies the original record")],
            "after_q1": [("R", "intervening", "regional reviewer signs note N4")], "probes": [],
            "q1": ("Which archive code was assigned first?", "ALPHA17", ["M"], {"M": 1.0}),
            "q2": ("Which reviewer note is linked during the intermediate review?", "N4", ["R"], {"R": 1.0}),
            "q3": ("Which original archive code is needed again?", "ALPHA17", ["M"], {"M": 1.0}),
        }
    if scenario == "obsolete_information":
        return {
            "initial": [("M", "old_state", "original routing label LEGACY")],
            "after_q1": [("O", "new_state", "signed update replaces routing label with CURRENT")], "probes": [],
            "q1": ("What routing label was recorded before the update?", "LEGACY", ["M"], {"M": 1.0}),
            "q2": ("What routing label is valid after the update?", "CURRENT", ["O"], {"O": 1.0}),
            "q3": ("Which current label should the system use?", "CURRENT", ["O"], {"O": 1.0}),
        }
    if scenario == "redundant_evidence":
        return {
            "initial": [
                ("A", "redundant", "archive code ALPHA17 is in the primary copy"),
                ("B", "redundant", "archive code ALPHA17 is in the duplicate copy"),
            ],
            "after_q1": [], "probes": [],
            "q1": ("Which archive code is recorded?", "ALPHA17", ["A", "B"], {"A": 0.90, "B": 0.05}),
            "q2": ("Which duplicate record must be checked?", "ALPHA17", ["B"], {"B": 1.0}),
            "q3": ("Which code closes the duplicate reconciliation?", "ALPHA17", ["B"], {"B": 1.0}),
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

    for i in range(capacity + 2):
        block = _block(f"T1_{i}", "distractor", f"unrelated history item {i}", rng, sizes)
        all_blocks.append(block)
        events.append({"type": "write", "time": "t1", "block": block})

    for block_id, question in plan["probes"]:
        events.append(_query(f"probe_{block_id}_{len(events)}", question, "", [block_id], {block_id: 1.0}, "pre_q1_probe"))

    q1_question, q1_answer, q1_evidence, q1_attention = plan["q1"]
    events.append(_query("q1", q1_question, q1_answer, q1_evidence, q1_attention, "first_unexpected"))

    for block_id, kind, payload in plan["after_q1"]:
        block = _block(block_id, kind, payload, rng, sizes)
        all_blocks.append(block)
        events.append({"type": "write", "time": "t4", "block": block})

    for i in range(pressure_factor * capacity):
        block = _block(f"P_{i}", "pressure", f"later history item {i}", rng, sizes)
        all_blocks.append(block)
        events.append({"type": "write", "time": "t4", "block": block})

    q2_question, q2_answer, q2_evidence, q2_attention = plan["q2"]
    events.append(_query("q2", q2_question, q2_answer, q2_evidence, q2_attention, "related_future"))
    if scenario == "delayed_reuse":
        for i in range(capacity):
            block = _block(f"P2_{i}", "late_pressure", f"late pressure item {i}", rng, sizes)
            all_blocks.append(block)
            events.append({"type": "write", "time": "t5", "block": block})
    q3_question, q3_answer, q3_evidence, q3_attention = plan["q3"]
    events.append(_query("q3", q3_question, q3_answer, q3_evidence, q3_attention, "related_future"))
    future_useful_ids = sorted(set(q2_evidence + q3_evidence))
    return {
        "episode_id": f"{scenario}-s{seed}-c{capacity}-p{pressure_factor}",
        "seed": seed, "capacity": capacity, "pressure_factor": pressure_factor, "scenario": scenario,
        "memory_sequence": all_blocks, "events": events,
        "future_useful_ids": future_useful_ids, "q1_evidence_ids": q1_evidence,
    }


def generate_episodes(*, seeds: Iterable[int], capacities: Iterable[int], pressure_factors: Iterable[int], scenarios: Iterable[str], sizes: dict[str, int]) -> list[dict[str, Any]]:
    return [
        generate_episode(seed=seed, capacity=capacity, pressure_factor=pressure_factor, scenario=scenario, sizes=sizes)
        for seed in seeds for capacity in capacities for pressure_factor in pressure_factors for scenario in scenarios
    ]


def write_json(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
