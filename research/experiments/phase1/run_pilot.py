#!/usr/bin/env python3
"""Run Phase 1 natural-language compression, routing, and QA pilot."""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from src.datasets.generate_pilot import proxy_tokens, main as generate_data  # noqa: E402
from src.compression.ollama_compress import build_compressions  # noqa: E402

CONFIG = json.loads((ROOT / "configs" / "pilot.json").read_text())
DATA = ROOT / "data" / "generated"
RAW = ROOT / "results" / "raw"


def call_model(prompt: str, seed_offset: int) -> tuple[str, dict]:
    body = json.dumps({
        "model": CONFIG["model"], "prompt": prompt, "stream": False, "think": False,
        "options": {"temperature": CONFIG["temperature"], "seed": CONFIG["seed"] + 1000 + seed_offset,
                     "num_ctx": CONFIG["num_ctx"], "num_predict": 96},
    }).encode()
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=CONFIG["ollama_timeout_seconds"]) as response:
        result = json.loads(response.read())
    elapsed = time.perf_counter() - started
    output = re.sub(r"<think>.*?</think>", "", result.get("response", ""), flags=re.S).strip()
    return output, {"elapsed_seconds": elapsed, "eval_count": result.get("eval_count"),
                    "prompt_eval_count": result.get("prompt_eval_count"), "model": result.get("model")}


def answer_prompt(context: str, question: str, task: str) -> str:
    return (
        "You are a strict factual question answering component.\n"
        f"Task: {task}.\n"
        "Use only the supplied context. Do not guess or use outside knowledge.\n"
        "Return only the exact answer token or tokens requested. For two requested facts, return both exact tokens separated by |.\n\n"
        f"CONTEXT:\n{context}\n\nQUESTION:\n{question}\nANSWER:"
    )


def lexical_route(question: str, summaries: list[str], top_k: int) -> list[int]:
    stop = {"the", "what", "which", "when", "is", "are", "for", "and", "does", "during", "the", "as", "to"}
    q_words = set(re.findall(r"[a-z0-9-]+", question.lower())) - stop
    scores = []
    for i, summary in enumerate(summaries):
        words = set(re.findall(r"[a-z0-9-]+", summary.lower()))
        scores.append((len(q_words & words), -i, i))
    return [x[2] for x in sorted(scores, reverse=True)[:top_k]]


def main() -> None:
    if not (DATA / "pilot_document.txt").exists():
        generate_data()
    document = (DATA / "pilot_document.txt").read_text()
    questions = json.loads((DATA / "questions.json").read_text())
    artifact, compression_calls = build_compressions(document)
    chunks = artifact["chunks"]
    summaries = artifact["chunk_summaries"]
    contexts = {
        "raw_context": document,
        "one_shot_summary": artifact["one_shot"],
        "chunk_summary": "\n\n--- CHUNK SUMMARY ---\n\n".join(summaries),
        "hierarchical_summary": "\n\n--- HIERARCHICAL SUMMARY ---\n\n".join(artifact["hierarchical_final"]),
    }
    rows, raw_answers = [], []
    call_index = 0
    for q in questions:
        for method, context in contexts.items():
            call_index += 1
            answer, meta = call_model(answer_prompt(context, q["question"], "direct answer from this representation"), call_index)
            row = {"question_id": q["question_id"], "method": method, "stage": "A_direct",
                   "question": q["question"], "expected_answer": q["answer"], "context_proxy_tokens": proxy_tokens(context),
                   "answer": answer, **meta}
            rows.append(row); raw_answers.append({"kind": "answer", "stage": "A_direct", "method": method,
                                                  "question_id": q["question_id"], "prompt": answer_prompt(context, q["question"], "direct answer from this representation"),
                                                  "response": answer, **meta})

        if q["question_id"] != "Q-08":
            for method in ["chunk_summary", "hierarchical_summary"]:
                selected = lexical_route(q["question"], summaries, CONFIG["retrieval_top_chunks"])
                selected_context = "\n\n--- RETRIEVED ORIGINAL CHUNK ---\n\n".join(chunks[i] for i in selected)
                call_index += 1
                answer, meta = call_model(answer_prompt(selected_context, q["question"], "answer after reading retrieved original text"), call_index)
                rows.append({"question_id": q["question_id"], "method": method, "stage": "B_route_C_answer",
                             "question": q["question"], "expected_answer": q["answer"], "selected_chunks": selected,
                             "routing_proxy_tokens": sum(proxy_tokens(summaries[i]) for i in selected),
                             "retrieved_context_proxy_tokens": proxy_tokens(selected_context), "answer": answer, **meta})
                raw_answers.append({"kind": "answer", "stage": "B_route_C_answer", "method": method,
                                    "question_id": q["question_id"], "selected_chunks": selected,
                                    "prompt": answer_prompt(selected_context, q["question"], "answer after reading retrieved original text"),
                                    "response": answer, **meta})
        else:
            # The multi-evidence question is deliberately not silently treated as a one-chunk test.
            rows.append({"question_id": q["question_id"], "method": "chunk_summary", "stage": "B_route_C_answer",
                         "question": q["question"], "expected_answer": q["answer"], "selected_chunks": [],
                         "routing_proxy_tokens": 0, "retrieved_context_proxy_tokens": 0,
                         "answer": "SKIPPED_MULTI_EVIDENCE_ROUTER", "skip_reason": "Pilot lexical router is single-block top-k; multi-evidence retained for Phase 1 expansion."})
            rows.append({"question_id": q["question_id"], "method": "hierarchical_summary", "stage": "B_route_C_answer",
                         "question": q["question"], "expected_answer": q["answer"], "selected_chunks": [],
                         "routing_proxy_tokens": 0, "retrieved_context_proxy_tokens": 0,
                         "answer": "SKIPPED_MULTI_EVIDENCE_ROUTER", "skip_reason": "Pilot lexical router is single-block top-k; multi-evidence retained for Phase 1 expansion."})
    RAW.mkdir(parents=True, exist_ok=True)
    with (RAW / "pilot_answers.jsonl").open("w") as f:
        for item in raw_answers: f.write(json.dumps(item, ensure_ascii=False) + "\n")
    (RAW / "pilot_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    manifest = {"experiment_id": "PHASE1-PILOT-001", "model": CONFIG["model"], "temperature": CONFIG["temperature"],
                "questions": len(questions), "answer_calls": len(raw_answers), "compression_calls": len(compression_calls),
                "compression_question_blind": artifact["question_blind"], "document_proxy_tokens": proxy_tokens(document),
                "started_at_local": time.strftime("%Y-%m-%d %H:%M:%S %z"),
                "note": "Pilot only; multi-evidence route stage intentionally skipped rather than silently mis-scored."}
    (RAW / "pilot_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
