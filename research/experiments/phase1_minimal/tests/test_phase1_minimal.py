from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.phase1_minimal.generate_data import generate_episode
from experiments.phase1_minimal.policies import HotMemory, POLICIES
from experiments.phase1_minimal.run_pilot import q1_utility, run_episode


SIZES = {"hot_bytes": 128, "raw_bytes": 256}


class Phase1MinimalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.episode = generate_episode(seed=7, capacity=8, pressure_factor=2, scenario="negation_condition", sizes=SIZES)

    def test_future_query_leakage(self) -> None:
        serialized_writes = "\n".join(json.dumps(event["block"], ensure_ascii=False) for event in self.episode["events"] if event["type"] == "write")
        self.assertNotIn("q1", serialized_writes)
        self.assertNotIn("q2", serialized_writes)
        self.assertNotIn("q3", serialized_writes)
        self.assertNotIn("future_useful_ids", serialized_writes)
        self.assertNotIn("utility", serialized_writes)

    def test_equal_budget_and_shared_history(self) -> None:
        runs = [run_episode(self.episode, policy) for policy in POLICIES]
        traces = [r["trace"] for r in runs]
        write_streams = [[(x["type"], x.get("block_id")) for x in trace if x["type"] == "write"] for trace in traces]
        self.assertTrue(all(stream == write_streams[0] for stream in write_streams))
        self.assertTrue(all(event["hot_size"] <= 8 for trace in traces for event in trace))

    def test_deterministic_seed(self) -> None:
        first = generate_episode(seed=7, capacity=8, pressure_factor=2, scenario="cross_event", sizes=SIZES)
        second = generate_episode(seed=7, capacity=8, pressure_factor=2, scenario="cross_event", sizes=SIZES)
        self.assertEqual(first, second)
        self.assertEqual(run_episode(first, "task_utility"), run_episode(second, "task_utility"))

    def test_q1_promotion_happens_only_after_utility(self) -> None:
        run = run_episode(self.episode, "task_utility")
        q1_index = next(i for i, x in enumerate(run["trace"]) if x.get("type") == "query" and x.get("query_id") == "q1")
        post_index = next(i for i, x in enumerate(run["trace"]) if x.get("type") == "post_use")
        self.assertGreater(post_index, q1_index)
        self.assertTrue(any(x.get("type") == "promote" and x.get("reason") == "q1_task_utility" for x in run["trace"][post_index:]))

    def test_tier_capacity_invariant(self) -> None:
        for policy in POLICIES:
            run = run_episode(self.episode, policy)
            self.assertTrue(all(event["hot_size"] <= 8 for event in run["trace"]))

    def test_task_utility_is_post_q1_counterfactual(self) -> None:
        self.assertEqual(q1_utility(["P", "N"]), {"P": 0.5, "N": 0.5})
        self.assertEqual(q1_utility([]), {})

    def test_q2_q3_are_related_but_not_q1_paraphrases(self) -> None:
        questions = [e["question"] for e in self.episode["events"] if e["type"] == "query"]
        self.assertEqual(len(questions), 3)
        self.assertEqual(len(set(questions)), 3)
        self.assertNotEqual(questions[0], questions[1])
        self.assertNotEqual(questions[0], questions[2])


if __name__ == "__main__":
    unittest.main()
