from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.phase1r.answer_model import FrozenAnswerModel
from experiments.phase1r.generate_data import generate_episode
from experiments.phase1r.policies import POLICIES
from experiments.phase1r.run_phase1r import preflight_cell, run_episode, run_preflight


SIZES = {"hot_bytes": 128, "raw_bytes": 256}


class Phase1RTests(unittest.TestCase):
    def setUp(self) -> None:
        self.episode = generate_episode(seed=7, capacity=8, pressure_factor=2, scenario="cross_event", sizes=SIZES)

    def test_future_query_not_written_into_memory(self) -> None:
        serialized_writes = "\n".join(json.dumps(event["block"], ensure_ascii=False) for event in self.episode["events"] if event["type"] == "write")
        for marker in ("q1", "q2", "q3", "gold_answer", "future_useful_ids", "utility"):
            self.assertNotIn(marker, serialized_writes)

    def test_counterfactual_signal_is_not_uniform_coverage(self) -> None:
        result = run_episode(self.episode, "task_utility")
        utility = result["metrics"]["q1_utility"]
        self.assertGreater(utility["B"], 0.0)
        self.assertEqual(utility["A"], 0.0)
        self.assertNotEqual(utility["A"], utility["B"])

    def test_answer_model_computes_real_log_probability_difference(self) -> None:
        model = FrozenAnswerModel()
        blocks = {block["id"]: block for block in self.episode["memory_sequence"] if block["id"] in {"A", "B", "C", "U"}}
        q1 = next(event for event in self.episode["events"] if event.get("query_id") == "q1")
        full = model.gold_log_probability(q1, blocks)
        masked = model.gold_log_probability(q1, blocks, masked_ids=["B"])
        self.assertGreater(full, masked)

    def test_all_policies_share_post_q1_admission_budget(self) -> None:
        runs = [run_episode(self.episode, policy) for policy in POLICIES]
        budgets = [next(event for event in run["trace"] if event.get("type") == "post_use")["admission_budget"] for run in runs]
        self.assertEqual(budgets, [4] * len(POLICIES))

    def test_q1_observation_occurs_before_promotion(self) -> None:
        run = run_episode(self.episode, "task_utility")
        post_index = next(i for i, event in enumerate(run["trace"]) if event.get("type") == "post_use")
        self.assertTrue(any(event.get("type") == "promote" for event in run["trace"][post_index + 1:]))

    def test_deterministic_and_gate_passes(self) -> None:
        first = generate_episode(seed=7, capacity=8, pressure_factor=2, scenario="cross_event", sizes=SIZES)
        second = generate_episode(seed=7, capacity=8, pressure_factor=2, scenario="cross_event", sizes=SIZES)
        self.assertEqual(first, second)
        episodes = [generate_episode(seed=seed, capacity=8, pressure_factor=2, scenario=scenario, sizes=SIZES) for seed in (7, 11, 19) for scenario in ("cross_event", "redundant_evidence")]
        _, summary = run_preflight(episodes)
        self.assertGreaterEqual(summary["retained_set_disagreement_fraction"], 0.20)

    def test_capacity_invariant(self) -> None:
        for policy in POLICIES:
            run = run_episode(self.episode, policy)
            self.assertTrue(all(event["hot_size"] <= 8 for event in run["trace"]))


if __name__ == "__main__":
    unittest.main()
