"""A deterministic frozen answer model used for counterfactual utility.

This is deliberately not a learned language model.  It is a fixed lexical
answer scorer: every gold-answer token gets a high log-probability when at
least one unmasked context block supports it, and a low log-probability
otherwise.  Removing one block and recomputing the gold-answer log
probability therefore gives a real counterfactual signal rather than a
hand-written 1/n coverage label.
"""

from __future__ import annotations

import math
import re
from typing import Any, Iterable


TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class FrozenAnswerModel:
    """Fixed, training-free scorer for synthetic gold-answer likelihood."""

    def __init__(self, *, supported_logit: float = 3.0, unsupported_logit: float = -3.0) -> None:
        self.supported_logit = supported_logit
        self.unsupported_logit = unsupported_logit

    @staticmethod
    def _log_sigmoid(logit: float) -> float:
        # Stable log(sigmoid(x)).
        if logit >= 0:
            return -math.log1p(math.exp(-logit))
        return logit - math.log1p(math.exp(logit))

    def gold_log_probability(
        self,
        query: dict[str, Any],
        blocks: dict[str, dict[str, Any]],
        masked_ids: Iterable[str] = (),
    ) -> float:
        masked = set(masked_ids)
        context_ids = query.get("answer_context_ids", query["evidence_ids"])
        available_tokens: set[str] = set()
        for block_id in context_ids:
            if block_id in masked or block_id not in blocks:
                continue
            available_tokens.update(tokenize(str(blocks[block_id]["payload"])))
        gold_tokens = tokenize(str(query["gold_answer"]))
        if not gold_tokens:
            return 0.0
        return sum(
            self._log_sigmoid(self.supported_logit if token in available_tokens else self.unsupported_logit)
            for token in gold_tokens
        )

    def counterfactual_utility(
        self,
        query: dict[str, Any],
        blocks: dict[str, dict[str, Any]],
        block_id: str,
    ) -> float:
        """Gold log-probability difference: full context minus block removed."""
        full = self.gold_log_probability(query, blocks)
        removed = self.gold_log_probability(query, blocks, masked_ids=[block_id])
        return max(0.0, full - removed)

    def answer_correct(self, query: dict[str, Any], blocks: dict[str, dict[str, Any]]) -> bool:
        full = self.gold_log_probability(query, blocks)
        masked_all = self.gold_log_probability(query, blocks, masked_ids=query.get("answer_context_ids", []))
        # The synthetic full context is correct iff every gold token is
        # supported.  This is computed, never passed as a constant label.
        return full > masked_all + 0.5
