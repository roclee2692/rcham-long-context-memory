#!/usr/bin/env python3
"""Generate a deterministic natural-language document and ground-truth questions."""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "configs" / "pilot.json").read_text())
OUT = ROOT / "data" / "generated"
RAW = ROOT / "data" / "raw"

VOCAB = [
    "inspection", "river", "sensor", "maintenance", "district", "reading", "schedule",
    "report", "operator", "channel", "control", "rainfall", "warning", "pump", "station",
    "archive", "measurement", "calibration", "procedure", "monitoring", "record", "review",
]


def proxy_tokens(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9]+|[^\s]", text))


def make_filler(rng: random.Random, count: int) -> str:
    words = [rng.choice(VOCAB) for _ in range(count)]
    return " ".join(words) + "."


def opaque(rng: random.Random, prefix: str) -> str:
    """Create an answer token whose value cannot be derived from the question index."""
    return f"{prefix}-" + "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(8))


def main() -> None:
    rng = random.Random(CONFIG["seed"])
    facts = []
    types = [
        "simple_fact", "numeric_fact", "temporal_fact", "entity_relation",
        "state_update", "negation", "cross_chunk_relation",
    ]
    for i in range(1, CONFIG["facts"] + 1):
        kind = types[(i - 1) % len(types)]
        answer = f"ANS-{i:03d}-" + "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
        if kind == "simple_fact":
            text = f"The maintenance record identifies the responsible unit for station {i:03d} as {answer}."
            question = f"Which unit is responsible for station {i:03d}?"
        elif kind == "numeric_fact":
            answer = opaque(rng, "NUM")
            text = f"The calibrated flow reading for gauge {i:03d} is {answer} cubic meters per hour."
            question = f"What is the calibrated flow reading for gauge {i:03d}?"
        elif kind == "temporal_fact":
            answer = opaque(rng, "DATE")
            text = f"The scheduled inspection for sensor {i:03d} is on {answer}."
            question = f"When is the scheduled inspection for sensor {i:03d}?"
        elif kind == "entity_relation":
            answer = opaque(rng, "LINK")
            text = f"Technician {answer} is assigned to monitor reservoir station {i:03d}."
            question = f"Which technician monitors reservoir station {i:03d}?"
        elif kind == "state_update":
            previous = opaque(rng, "STATE")
            answer = opaque(rng, "STATE")
            text = f"The gate state changed from {previous} to {answer} after the evening inspection."
            question = f"What was the final gate state for station {i:03d}?"
        elif kind == "negation":
            answer = opaque(rng, "RULE")
            text = f"During the flood warning, automatic restart at station {i:03d} is {answer}; manual review is required."
            question = f"During the flood warning, is automatic restart at station {i:03d} permitted?"
        else:
            first = opaque(rng, "PAIR")
            answer = opaque(rng, "PAIR")
            text = f"The report first names channel {i:03d} as {first} and later states that its downstream control mode is {answer}."
            question = f"What downstream control mode belongs to channel {i:03d}?"
        facts.append({"fact_id": f"FACT-{i:03d}", "type": kind, "answer": answer, "question": question, "text": text})

    sections = []
    for fact in facts:
        filler = make_filler(rng, CONFIG["filler_words_per_fact"])
        sections.append(f"Section {fact['fact_id']}\n{filler}\n{fact['text']}\n{filler}")
    document = "\n\n".join(sections)
    questions = []
    chosen = [0, 8, 16, 25, 34, 43, 52, 59]
    for idx in chosen:
        fact = facts[idx]
        questions.append({"question_id": f"Q-{len(questions)+1:02d}", "fact_id": fact["fact_id"],
                          "type": fact["type"], "question": fact["question"], "answer": fact["answer"]})
    # Add a deliberately multi-evidence question to test cross-chunk reasoning.
    questions[-1]["fact_id"] = None
    questions[-1]["question"] = "Which technician monitors reservoir station 053, and what is the final gate state for station 033?"
    questions[-1]["answer"] = facts[52]["answer"] + "|" + facts[32]["answer"]
    questions[-1]["fact_ids"] = ["FACT-053", "FACT-033"]
    questions[-1]["type"] = "multi_evidence"

    OUT.mkdir(parents=True, exist_ok=True); RAW.mkdir(parents=True, exist_ok=True)
    (OUT / "pilot_document.txt").write_text(document)
    (OUT / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=2) + "\n")
    (OUT / "questions.json").write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n")
    manifest = {
        "seed": CONFIG["seed"], "facts": len(facts), "questions": len(questions),
        "document_chars": len(document), "document_proxy_tokens": proxy_tokens(document),
        "fact_types": sorted({f["type"] for f in facts}),
        "question_ids": [q["question_id"] for q in questions],
        "generation": "Deterministic templates plus seeded filler; no language model used.",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
