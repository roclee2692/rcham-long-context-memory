"""Small deterministic hot-memory simulator for the principle test."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


POLICIES = (
    "recency",
    "frequency",
    "attention",
    "rmm_like",
    "task_utility",
    "oracle_future_reuse",
)


class HotMemory:
    """A bounded hot set plus an immutable archive.

    The manager receives events one at a time.  It never receives the episode's
    future-use labels.  The evaluator supplies those labels only after the run
    to score retention and the optional oracle upper bound.
    """

    def __init__(self, policy: str, capacity: int) -> None:
        if policy not in POLICIES:
            raise ValueError(policy)
        self.policy = policy
        self.capacity = capacity
        self.hot: dict[str, dict[str, Any]] = {}
        self.archive: dict[str, dict[str, Any]] = {}
        self.last_access: dict[str, int] = {}
        self.write_order: dict[str, int] = {}
        self.frequency: dict[str, int] = {}
        self.attention: dict[str, float] = {}
        self.rmm_signal: dict[str, float] = {}
        self.task_utility: dict[str, float] = {}
        self.future_reuse: dict[str, float] = {}
        self.step = 0
        self.write_index = 0
        self.cold_reads = 0
        self.cold_bytes = 0
        self.evictions = 0
        self.promotions = 0
        self.trace: list[dict[str, Any]] = []
        self.query_results: dict[str, dict[str, Any]] = {}

    def _score(self, block_id: str) -> float:
        if self.policy == "recency":
            return float(self.last_access.get(block_id, 0))
        if self.policy == "frequency":
            return float(self.frequency.get(block_id, 0))
        if self.policy == "attention":
            return self.attention.get(block_id, 0.0)
        if self.policy == "rmm_like":
            return self.rmm_signal.get(block_id, 0.0)
        if self.policy == "task_utility":
            return self.task_utility.get(block_id, 0.0)
        if self.policy == "oracle_future_reuse":
            return self.future_reuse.get(block_id, 0.0)
        raise AssertionError(self.policy)

    def _victim(self) -> str:
        # Stable tie-breaking makes traces reproducible and gives recency a
        # deterministic insertion-order fallback.
        return min(self.hot, key=lambda block_id: (self._score(block_id), self.last_access.get(block_id, 0), self.write_order.get(block_id, 0), block_id))

    def _ensure_hot(self, block_id: str, reason: str) -> None:
        if block_id in self.hot:
            return
        if len(self.hot) >= self.capacity:
            victim = self._victim()
            del self.hot[victim]
            self.evictions += 1
            self._record({"type": "evict", "block_id": victim, "reason": reason})
        self.hot[block_id] = deepcopy(self.archive[block_id])
        self.promotions += 1
        self._record({"type": "promote", "block_id": block_id, "reason": reason})

    def write(self, block: dict[str, Any]) -> None:
        self.step += 1
        block_id = block["id"]
        self.archive[block_id] = deepcopy(block)
        self.write_index += 1
        self.write_order.setdefault(block_id, self.write_index)
        self.frequency.setdefault(block_id, 0)
        self.attention.setdefault(block_id, 0.0)
        self.rmm_signal.setdefault(block_id, 0.0)
        self.task_utility.setdefault(block_id, 0.0)
        self.future_reuse.setdefault(block_id, 0.0)
        self._ensure_hot(block_id, "write")
        self._record({"type": "write", "block_id": block_id})

    def query(self, query: dict[str, Any]) -> dict[str, Any]:
        self.step += 1
        evidence = list(query["evidence_ids"])
        hot_before = [block_id for block_id in evidence if block_id in self.hot]
        cold_before = [block_id for block_id in evidence if block_id not in self.hot]
        self.cold_reads += len(cold_before)
        self.cold_bytes += sum(self.archive[block_id]["raw_bytes"] for block_id in cold_before)
        recall = len(hot_before) / len(evidence) if evidence else 1.0
        hot_answer = 1.0 if len(hot_before) == len(evidence) else 0.0
        result = {
            "query_id": query["query_id"],
            "role": query["role"],
            "evidence_ids": evidence,
            "hot_ids_before": hot_before,
            "cold_ids_before": cold_before,
            "hot_evidence_recall": recall,
            "hot_answer_accuracy": hot_answer,
            "archive_answer_accuracy": 1.0,
            "cold_blocks": len(cold_before),
            "cold_bytes": sum(self.archive[block_id]["raw_bytes"] for block_id in cold_before),
            "tier1_occupancy": len(self.hot),
        }
        self.query_results[query["query_id"]] = result
        for block_id in evidence:
            self.frequency[block_id] = self.frequency.get(block_id, 0) + 1
            self.last_access[block_id] = self.step
            self.attention[block_id] = self.attention.get(block_id, 0.0) + float(query["attention_weights"].get(block_id, 0.0))
        self._record({"type": "query", **result})
        return result

    def observe_q1(self, query: dict[str, Any], utility: dict[str, float], answer_correct: bool = True) -> None:
        """Receive only q1-derived signals after q1 has completed."""
        self.step += 1
        for block_id, weight in query["attention_weights"].items():
            self.rmm_signal[block_id] = max(self.rmm_signal.get(block_id, 0.0), float(weight) * float(answer_correct))
        for block_id, value in utility.items():
            self.task_utility[block_id] = max(self.task_utility.get(block_id, 0.0), float(value))
        # Record observation before any promotion.  This makes the causal
        # boundary explicit in the raw trace: q1 finished, utility became
        # observable, and only then may a policy change residency.
        self._record({"type": "post_use", "query_id": query["query_id"], "utility": utility, "rmm_signal": dict(self.rmm_signal)})
        if self.policy == "rmm_like":
            for block_id, value in self.rmm_signal.items():
                if value > 0:
                    self._ensure_hot(block_id, "q1_rmm_like")
        elif self.policy == "task_utility":
            for block_id, value in utility.items():
                if value > 0:
                    self._ensure_hot(block_id, "q1_task_utility")

    def set_oracle_future_labels(self, future_useful_ids: list[str]) -> None:
        # This is intentionally called only by the optional non-deployable
        # upper-bound policy.  Other policy instances never receive it.
        if self.policy == "oracle_future_reuse":
            for block_id in future_useful_ids:
                self.future_reuse[block_id] = 1.0

    def _record(self, event: dict[str, Any]) -> None:
        self.trace.append({
            **event,
            "step": self.step,
            "hot_ids": sorted(self.hot),
            "hot_size": len(self.hot),
            "archive_size": len(self.archive),
        })

    def evaluate(self, future_useful_ids: list[str], useless_ids: list[str]) -> dict[str, Any]:
        future = set(future_useful_ids)
        useless = set(useless_ids)
        q2 = self.query_results.get("q2", {})
        q3 = self.query_results.get("q3", {})
        q23 = [q2, q3]
        retained_future = [len(set(q.get("hot_ids_before", [])) & future) / len(future) if future else 1.0 for q in q23]
        retained_useless = [len(set(q.get("hot_ids_before", [])) & useless) / len(useless) if useless else 0.0 for q in q23]
        precision = [
            len(set(q.get("hot_ids_before", [])) & future) / len(q.get("hot_ids_before", [])) if q.get("hot_ids_before") else 1.0
            for q in q23
        ]
        q1 = self.query_results.get("q1", {})
        return {
            "policy": self.policy,
            "q1_hot_evidence_recall": q1.get("hot_evidence_recall", 0.0),
            "q1_cold_blocks": q1.get("cold_blocks", 0),
            "q2_hot_evidence_recall": q2.get("hot_evidence_recall", 0.0),
            "q3_hot_evidence_recall": q3.get("hot_evidence_recall", 0.0),
            "q2_answer_accuracy": q2.get("hot_answer_accuracy", 0.0),
            "q3_answer_accuracy": q3.get("hot_answer_accuracy", 0.0),
            "future_useful_retention": sum(retained_future) / len(retained_future),
            "q2_future_useful_retention": retained_future[0],
            "q3_future_useful_retention": retained_future[1],
            "retained_useless_blocks": sum(retained_useless) / len(retained_useless),
            "retention_precision": sum(precision) / len(precision),
            "eviction_regret": 1.0 - (sum(retained_future) / len(retained_future)),
            "promotion_count": self.promotions,
            "eviction_count": self.evictions,
            "churn": self.promotions + self.evictions,
            "cold_blocks_total": self.cold_reads,
            "cold_bytes_total": self.cold_bytes,
            "q2_tier1_occupancy": q2.get("tier1_occupancy", len(self.hot)),
            "q3_tier1_occupancy": q3.get("tier1_occupancy", len(self.hot)),
        }
