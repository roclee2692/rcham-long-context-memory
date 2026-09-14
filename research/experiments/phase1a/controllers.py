"""Small, explainable tier lifecycle controllers for Phase 1A."""

from __future__ import annotations

import copy
from typing import Any, Iterable


POLICIES = (
    "static",
    "retrieval_count",
    "oracle_utility",
    "oracle_utility_decay_cooldown",
    "cold_raw_fallback_only",
    "perfect_routing_no_promotion",
)


class MemoryController:
    """A deterministic three-tier memory simulator.

    Tier 1 is bounded hot/high-resolution memory, Tier 2 is an unbounded
    compressed index, and Tier 3 is an immutable raw archive.  Routing is
    supplied by the episode as exact evidence IDs; this pilot studies only
    post-use lifecycle decisions.
    """

    def __init__(
        self,
        policy: str,
        capacity: int,
        *,
        decay_factor: float = 0.97,
        decay_threshold: float = 0.10,
        cooldown_steps: int = 3,
    ) -> None:
        if policy not in POLICIES:
            raise ValueError(f"unknown policy: {policy}")
        self.policy = policy
        self.capacity = capacity
        self.decay_factor = decay_factor
        self.decay_threshold = decay_threshold
        self.cooldown_steps = cooldown_steps
        self.tier1: dict[str, dict[str, Any]] = {}
        self.tier2: dict[str, dict[str, Any]] = {}
        self.tier3: dict[str, dict[str, Any]] = {}
        self.scores: dict[str, float] = {}
        self.retrieval_count: dict[str, int] = {}
        self.last_hot_step: dict[str, int] = {}
        self.cooldown_until: dict[str, int] = {}
        self.step = 0
        self.promotion_count = 0
        self.demotion_count = 0
        self.churn = 0
        self.cold_reads = 0
        self.cold_bytes = 0
        self.blocks_accessed = 0
        self.index_probes = 0
        self.trace: list[dict[str, Any]] = []
        self.q_results: dict[str, dict[str, Any]] = {}

    def _decay(self) -> None:
        if self.policy != "oracle_utility_decay_cooldown":
            return
        for block_id in list(self.scores):
            self.scores[block_id] *= self.decay_factor
        # Demotion uses the post-decay score and respects cooldown.  The raw
        # archive remains intact, so demotion is reversible via cold fallback.
        for block_id in list(self.tier1):
            if (
                self.scores.get(block_id, 0.0) < self.decay_threshold
                and self.step >= self.cooldown_until.get(block_id, 0)
            ):
                self._demote(block_id)

    def _candidate_key(self, block_id: str) -> tuple[float, int, str]:
        if self.policy == "retrieval_count":
            protection = float(self.retrieval_count.get(block_id, 0))
        elif self.policy in {"oracle_utility", "oracle_utility_decay_cooldown"}:
            protection = self.scores.get(block_id, 0.0)
        else:
            protection = 0.0
        # Min key is evicted first; insertion step gives deterministic FIFO
        # tie-breaking for static/no-promotion controls.
        return (protection, self.last_hot_step.get(block_id, 0), block_id)

    def _evict_if_full(self, incoming_id: str) -> None:
        if incoming_id in self.tier1:
            return
        if len(self.tier1) >= self.capacity:
            victim = min(self.tier1, key=self._candidate_key)
            self._demote(victim)

    def _promote(self, block_id: str, reason: str) -> None:
        if block_id not in self.tier2:
            return
        if block_id not in self.tier1:
            self._evict_if_full(block_id)
            self.tier1[block_id] = copy.deepcopy(self.tier2[block_id])
            self.promotion_count += 1
            self.churn += 1
        self.last_hot_step[block_id] = self.step
        if self.policy == "retrieval_count":
            self.scores[block_id] = float(self.retrieval_count.get(block_id, 0))
        elif self.policy in {"oracle_utility", "oracle_utility_decay_cooldown"} and not reason.startswith("write"):
            self.scores[block_id] = max(self.scores.get(block_id, 0.0), 1.0)
            if self.policy == "oracle_utility_decay_cooldown":
                self.cooldown_until[block_id] = self.step + self.cooldown_steps
        self._record_state(
            {"type": "promotion", "block_id": block_id, "reason": reason}
        )

    def _demote(self, block_id: str) -> None:
        if block_id in self.tier1:
            del self.tier1[block_id]
            self.demotion_count += 1
            self.churn += 1
            self._record_state({"type": "demotion", "block_id": block_id})

    def write(self, block: dict[str, Any]) -> None:
        self.step += 1
        self._decay()
        block_id = block["id"]
        self.tier2[block_id] = copy.deepcopy(block)
        self.tier3[block_id] = copy.deepcopy(block)
        self.scores.setdefault(block_id, 0.0)
        self.retrieval_count.setdefault(block_id, 0)
        # New writes enter hot storage.  This makes pressure and tier capacity
        # explicit; future utility still cannot be seen at write time.
        self._promote(block_id, reason="write")
        self._record_state({"type": "write", "block_id": block_id})

    def query(self, query: dict[str, Any]) -> dict[str, Any]:
        self.step += 1
        self._decay()
        self.index_probes += 1
        evidence_ids = list(query["evidence_ids"])
        hot_ids = [block_id for block_id in evidence_ids if block_id in self.tier1]
        cold_ids = [block_id for block_id in evidence_ids if block_id not in self.tier1]
        self.blocks_accessed += len(evidence_ids)
        self.cold_reads += len(cold_ids)
        self.cold_bytes += sum(self.tier3[block_id]["raw_bytes"] for block_id in cold_ids)
        result = {
            "query_id": query["query_id"],
            "stage": query["stage"],
            "evidence_ids": evidence_ids,
            "hot_ids_before_update": hot_ids,
            "cold_ids_before_update": cold_ids,
            "hot_evidence_recall": len(hot_ids) / len(evidence_ids) if evidence_ids else 1.0,
            "evidence_recall_any": 1.0 if all(block_id in self.tier3 for block_id in evidence_ids) else 0.0,
            "cold_blocks_read": len(cold_ids),
            "cold_bytes": sum(self.tier3[block_id]["raw_bytes"] for block_id in cold_ids),
            "blocks_accessed": len(evidence_ids),
            "index_probes": 1,
            "tier1_occupancy": len(self.tier1),
        }
        self.q_results[query["query_id"]] = result
        # Retrieval-count promotion is intentionally based only on access, not
        # utility, so frequently retrieved useless distractors can win.
        if self.policy == "retrieval_count":
            for block_id in evidence_ids:
                self.retrieval_count[block_id] = self.retrieval_count.get(block_id, 0) + 1
                self.scores[block_id] = float(self.retrieval_count[block_id])
                self._promote(block_id, reason=f"retrieval:{query['query_id']}")
        self._record_state({"type": "query", **result, "query_role": query["query_role"]})
        return result

    def apply_utility(self, utility_ids: Iterable[str], *, query_id: str) -> None:
        # This method is called only after q1 by the runner.  No future query
        # labels are available here; utility is an oracle post-use label.
        if self.policy in {"oracle_utility", "oracle_utility_decay_cooldown"}:
            for block_id in utility_ids:
                self._promote(block_id, reason=f"oracle_utility:{query_id}")
        self._record_state(
            {
                "type": "utility",
                "for_query": query_id,
                "utility_ids": list(utility_ids),
            }
        )

    def _record_state(self, event: dict[str, Any]) -> None:
        self.trace.append(
            {
                **event,
                "step": self.step,
                "tier1_ids": sorted(self.tier1),
                "tier2_size": len(self.tier2),
                "tier3_size": len(self.tier3),
                "tier1_size": len(self.tier1),
            }
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "tier1_ids": sorted(self.tier1),
            "tier2_size": len(self.tier2),
            "tier3_size": len(self.tier3),
            "tier1_size": len(self.tier1),
        }

    def metrics(self, *, future_useful_ids: Iterable[str], useless_ids: Iterable[str]) -> dict[str, Any]:
        future_useful = set(future_useful_ids)
        useless = set(useless_ids)
        q = self.q_results

        def qmetric(query_id: str, key: str, default: float = 0.0) -> float:
            return float(q.get(query_id, {}).get(key, default))

        q2_q3_useful = []
        q2_q3_useless = []
        for query_id in ("q2", "q3"):
            hot = set(q.get(query_id, {}).get("hot_ids_before_update", []))
            q2_q3_useful.append(len(hot & future_useful) / len(future_useful) if future_useful else 1.0)
            q2_q3_useless.append(len(hot & useless) / len(useless) if useless else 0.0)
        promoted_nonuseful = sum(
            1
            for event in self.trace
            if event.get("type") == "promotion"
            and not event.get("reason", "").startswith("write")
            and event.get("block_id") not in future_useful
        )
        return {
            "q1_hot_evidence_recall": qmetric("q1", "hot_evidence_recall"),
            "q2_hot_evidence_recall": qmetric("q2", "hot_evidence_recall"),
            "q3_hot_evidence_recall": qmetric("q3", "hot_evidence_recall"),
            "q1_evidence_recall_any": qmetric("q1", "evidence_recall_any"),
            "q2_evidence_recall_any": qmetric("q2", "evidence_recall_any"),
            "q3_evidence_recall_any": qmetric("q3", "evidence_recall_any"),
            "q1_cold_blocks": qmetric("q1", "cold_blocks_read"),
            "q2_cold_blocks": qmetric("q2", "cold_blocks_read"),
            "q3_cold_blocks": qmetric("q3", "cold_blocks_read"),
            "q1_cold_bytes": qmetric("q1", "cold_bytes"),
            "q2_cold_bytes": qmetric("q2", "cold_bytes"),
            "q3_cold_bytes": qmetric("q3", "cold_bytes"),
            "q2_target_survival": 1.0 if "M" in q.get("q2", {}).get("hot_ids_before_update", []) else 0.0,
            "q3_target_survival": 1.0 if "M" in q.get("q3", {}).get("hot_ids_before_update", []) else 0.0,
            "useful_memory_retention": sum(q2_q3_useful) / len(q2_q3_useful),
            "useless_memory_occupancy": sum(q2_q3_useless) / len(q2_q3_useless),
            "promotion_count": self.promotion_count,
            "demotion_count": self.demotion_count,
            "churn": self.churn,
            "promotion_regret": promoted_nonuseful,
            "total_cold_reads": self.cold_reads,
            "total_cold_bytes": self.cold_bytes,
            "total_blocks_accessed": self.blocks_accessed,
            "total_index_probes": self.index_probes,
            "tier1_occupancy_q2": qmetric("q2", "tier1_occupancy"),
            "tier1_occupancy_q3": qmetric("q3", "tier1_occupancy"),
        }
