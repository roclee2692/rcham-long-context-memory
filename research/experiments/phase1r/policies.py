"""Bounded hot-memory simulator for Phase 1R."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


POLICIES = ("recency", "frequency", "attention", "rmm_like", "task_utility", "oracle_future_reuse")


class HotMemory:
    def __init__(self, policy: str, capacity: int, admission_budget: int | None = None) -> None:
        if policy not in POLICIES:
            raise ValueError(policy)
        self.policy = policy
        self.capacity = capacity
        self.admission_budget = admission_budget if admission_budget is not None else max(1, capacity // 2)
        self.hot: dict[str, dict[str, Any]] = {}
        self.archive: dict[str, dict[str, Any]] = {}
        self.last_access: dict[str, int] = {}
        self.write_order: dict[str, int] = {}
        self.frequency: dict[str, int] = {}
        self.attention: dict[str, float] = {}
        self.rmm_signal: dict[str, float] = {}
        self.task_utility: dict[str, float] = {}
        self.future_reuse: dict[str, float] = {}
        self._oracle_ids: set[str] = set()
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
        return min(self.hot, key=lambda block_id: (
            self._score(block_id), self.last_access.get(block_id, 0), self.write_order.get(block_id, 0), block_id,
        ))

    def _ensure_hot(self, block_id: str, reason: str) -> None:
        if block_id in self.hot:
            return
        if block_id not in self.archive:
            raise KeyError(block_id)
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
        for store in (self.frequency, self.attention, self.rmm_signal, self.task_utility, self.future_reuse):
            store.setdefault(block_id, 0.0 if store is not self.frequency else 0)
        if block_id in self._oracle_ids:
            self.future_reuse[block_id] = 1.0
        self._ensure_hot(block_id, "write")
        self._record({"type": "write", "block_id": block_id})

    def query(self, query: dict[str, Any], *, answer_correct: bool | None = None) -> dict[str, Any]:
        self.step += 1
        evidence = list(query["evidence_ids"])
        hot_before = [block_id for block_id in evidence if block_id in self.hot]
        cold_before = [block_id for block_id in evidence if block_id not in self.hot]
        self.cold_reads += len(cold_before)
        self.cold_bytes += sum(self.archive[block_id]["raw_bytes"] for block_id in cold_before)
        recall = len(hot_before) / len(evidence) if evidence else 1.0
        hot_answer = 1.0 if len(hot_before) == len(evidence) else 0.0
        result = {
            "query_id": query["query_id"], "role": query["role"], "evidence_ids": evidence,
            "hot_ids_before": hot_before, "cold_ids_before": cold_before,
            "hot_evidence_recall": recall, "hot_answer_accuracy": hot_answer,
            "archive_answer_accuracy": 1.0, "model_answer_correct": answer_correct,
            "cold_blocks": len(cold_before), "cold_bytes": sum(self.archive[block_id]["raw_bytes"] for block_id in cold_before),
            "tier1_occupancy": len(self.hot),
        }
        self.query_results[query["query_id"]] = result
        # Every policy sees the same q1 attention candidate set and gets the
        # same admission opportunity; only its score differs.
        for block_id, weight in query["attention_weights"].items():
            self.frequency[block_id] = self.frequency.get(block_id, 0) + 1
            self.last_access[block_id] = self.step
            self.attention[block_id] = self.attention.get(block_id, 0.0) + float(weight)
        self._record({"type": "query", **result})
        return result

    def observe_q1(self, query: dict[str, Any], utility: dict[str, float], answer_correct: bool) -> None:
        """Update policy-specific signals after q1 and admit equal slots."""
        self.step += 1
        candidates = list(query["attention_weights"])
        for block_id in candidates:
            # Block-level adaptation of RMM's correctness-weighted attention
            # demonstration.  Unlike the old benchmark, correctness is
            # computed by the frozen answer model and is not a constant input.
            self.rmm_signal[block_id] = max(
                self.rmm_signal.get(block_id, 0.0),
                float(query["attention_weights"].get(block_id, 0.0)) * float(answer_correct),
            )
        for block_id, value in utility.items():
            self.task_utility[block_id] = max(self.task_utility.get(block_id, 0.0), float(value))
        self._record({
            "type": "post_use", "query_id": query["query_id"], "utility": dict(utility),
            "rmm_signal": {block_id: self.rmm_signal.get(block_id, 0.0) for block_id in candidates},
            "policy_scores": {block_id: self._score(block_id) for block_id in candidates},
            "answer_correct": answer_correct, "admission_budget": self.admission_budget,
        })
        if self.policy == "oracle_future_reuse":
            return
        ranked = sorted(
            (block_id for block_id in candidates if self._score(block_id) > 0),
            key=lambda block_id: (-self._score(block_id), self.write_order.get(block_id, 0), block_id),
        )[: self.admission_budget]
        for block_id in ranked:
            self._ensure_hot(block_id, f"q1_{self.policy}")

    def set_oracle_future_labels(self, future_useful_ids: list[str]) -> None:
        if self.policy == "oracle_future_reuse":
            self._oracle_ids.update(future_useful_ids)
            for block_id in future_useful_ids:
                self.future_reuse[block_id] = 1.0

    def _record(self, event: dict[str, Any]) -> None:
        self.trace.append({**event, "step": self.step, "hot_ids": sorted(self.hot), "hot_size": len(self.hot), "archive_size": len(self.archive)})

    def evaluate(self, future_useful_ids: list[str], useless_ids: list[str]) -> dict[str, Any]:
        future, useless = set(future_useful_ids), set(useless_ids)
        q2, q3 = self.query_results.get("q2", {}), self.query_results.get("q3", {})
        q23 = [q2, q3]
        retained_future = [len(set(q.get("hot_ids_before", [])) & future) / len(future) if future else 1.0 for q in q23]
        retained_useless = [len(set(q.get("hot_ids_before", [])) & useless) / len(useless) if useless else 0.0 for q in q23]
        precision = [len(set(q.get("hot_ids_before", [])) & future) / len(q.get("hot_ids_before", [])) if q.get("hot_ids_before") else 1.0 for q in q23]
        q1 = self.query_results.get("q1", {})
        return {
            "policy": self.policy, "q1_hot_evidence_recall": q1.get("hot_evidence_recall", 0.0), "q1_cold_blocks": q1.get("cold_blocks", 0),
            "q2_hot_evidence_recall": q2.get("hot_evidence_recall", 0.0), "q3_hot_evidence_recall": q3.get("hot_evidence_recall", 0.0),
            "q2_answer_accuracy": q2.get("hot_answer_accuracy", 0.0), "q3_answer_accuracy": q3.get("hot_answer_accuracy", 0.0),
            "future_useful_retention": sum(retained_future) / len(retained_future), "q2_future_useful_retention": retained_future[0],
            "q3_future_useful_retention": retained_future[1], "retained_useless_blocks": sum(retained_useless) / len(retained_useless),
            "retention_precision": sum(precision) / len(precision), "eviction_regret": 1.0 - (sum(retained_future) / len(retained_future)),
            "promotion_count": self.promotions, "eviction_count": self.evictions, "churn": self.promotions + self.evictions,
            "cold_blocks_total": self.cold_reads, "cold_bytes_total": self.cold_bytes,
            "q2_tier1_occupancy": q2.get("tier1_occupancy", len(self.hot)), "q3_tier1_occupancy": q3.get("tier1_occupancy", len(self.hot)),
        }
