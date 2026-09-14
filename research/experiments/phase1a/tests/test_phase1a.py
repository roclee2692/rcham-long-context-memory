from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

RESEARCH_ROOT = Path(__file__).resolve().parents[3]
if str(RESEARCH_ROOT) not in sys.path:
    sys.path.insert(0, str(RESEARCH_ROOT))

from experiments.phase1a.controllers import POLICIES
from experiments.phase1a.controllers import MemoryController
from experiments.phase1a.generate_data import WRITE_KEYS, generate_episode, generate_episodes
from experiments.phase1a.run_pilot import load_config, run_episode


class Phase1ATests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config()
        self.episode = generate_episode(
            seed=7,
            capacity=8,
            pressure_factor=2,
            delay="medium",
            scenario="repeated_useful",
            sizes=self.config["block_sizes"],
        )

    def test_future_query_leakage(self) -> None:
        for event in self.episode["events"]:
            if event["type"] == "write":
                self.assertEqual(set(event["block"]), WRITE_KEYS)
                serialized = json.dumps(event["block"], ensure_ascii=False)
                self.assertNotIn("q1", serialized)
                self.assertNotIn("q2", serialized)
                self.assertNotIn("q3", serialized)
                self.assertNotIn("utility", serialized)
        # Future labels live in evaluator metadata, never in writes.
        self.assertIn("future_useful_ids", self.episode)
        self.assertNotIn("future_useful_ids", self.episode["events"][0]["block"])

    def test_equal_budget_and_shared_history(self) -> None:
        runs = [run_episode(self.episode, policy, self.config) for policy in POLICIES]
        self.assertEqual({run["capacity"] for run in runs}, {8})
        # The immutable raw archive and event/query history are independent of
        # policy; only lifecycle decisions may differ.
        archive_ids = {block["id"] for block in self.episode["memory_sequence"]}
        self.assertTrue(archive_ids)
        query_stream = [
            (event["query_id"], tuple(event["evidence_ids"]))
            for event in self.episode["events"]
            if event["type"] == "query"
        ]
        for run in runs:
            self.assertEqual(run["metrics"]["total_index_probes"], len(query_stream))
            self.assertEqual(run["trace"][-1]["tier3_size"], len(archive_ids))
            self.assertEqual(
                [(event["query_id"], tuple(event["evidence_ids"])) for event in run["trace"] if event.get("type") == "query"],
                query_stream,
            )
            for event in run["trace"]:
                self.assertLessEqual(event["tier1_size"], 8)

    def test_deterministic_seed(self) -> None:
        first = generate_episodes(
            seeds=[7], capacities=[8], pressure_factors=[2], delays=["short"], scenarios=["competing_useful"], sizes=self.config["block_sizes"]
        )
        second = generate_episodes(
            seeds=[7], capacities=[8], pressure_factors=[2], delays=["short"], scenarios=["competing_useful"], sizes=self.config["block_sizes"]
        )
        self.assertEqual(first, second)
        run_a = run_episode(first[0], "oracle_utility", self.config)
        run_b = run_episode(second[0], "oracle_utility", self.config)
        self.assertEqual(run_a, run_b)

    def test_q1_promotion_happens_only_after_utility(self) -> None:
        run = run_episode(self.episode, "oracle_utility", self.config)
        query_events = [event for event in run["trace"] if event.get("type") == "query" and event.get("query_id") == "q1"]
        utility_events = [event for event in run["trace"] if event.get("type") == "utility" and event.get("for_query") == "q1"]
        self.assertEqual(len(query_events), 1)
        self.assertEqual(len(utility_events), 1)
        self.assertNotIn("M", query_events[0]["hot_ids_before_update"])
        trace_index = {id(event): index for index, event in enumerate(run["trace"])}
        self.assertLess(trace_index[id(query_events[0])], trace_index[id(utility_events[0])])
        promotion_index = next(
            index for index, event in enumerate(run["trace"])
            if event.get("type") == "promotion" and event.get("block_id") == "M" and "oracle_utility" in event.get("reason", "")
        )
        self.assertGreater(promotion_index, trace_index[id(query_events[0])])

    def test_tier_capacity_invariant(self) -> None:
        episodes = generate_episodes(
            seeds=[7, 11], capacities=[8, 16], pressure_factors=[2, 4], delays=["short", "long"], scenarios=self.config["scenarios"], sizes=self.config["block_sizes"]
        )
        for episode in episodes:
            for policy in POLICIES:
                run = run_episode(episode, policy, self.config)
                for event in run["trace"]:
                    self.assertLessEqual(event["tier1_size"], episode["capacity"])

    def test_q2_q3_are_not_q1_rewrites(self) -> None:
        questions = [event["question"] for event in self.episode["events"] if event["type"] == "query"]
        self.assertEqual(len(questions), 3)
        self.assertEqual(len(set(questions)), 3)
        self.assertNotEqual(questions[0], questions[1])
        self.assertNotEqual(questions[0], questions[2])


if __name__ == "__main__":
    unittest.main()
