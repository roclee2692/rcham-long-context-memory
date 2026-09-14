#!/usr/bin/env python3
"""Question-blind compression calls against an existing local Ollama model."""
from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "configs" / "pilot.json").read_text())
RAW_OUT = ROOT / "results" / "raw"


def proxy_tokens(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9]+|[^\s]", text))


def call_ollama(prompt: str, *, num_predict: int, seed_offset: int) -> tuple[str, dict]:
    body = json.dumps({
        "model": CONFIG["model"], "prompt": prompt, "stream": False,
        "think": False,
        "options": {"temperature": CONFIG["temperature"], "seed": CONFIG["seed"] + seed_offset,
                     "num_ctx": CONFIG["num_ctx"], "num_predict": num_predict},
    }).encode()
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=CONFIG["ollama_timeout_seconds"]) as response:
        result = json.loads(response.read())
    elapsed = time.perf_counter() - start
    output = result.get("response", "")
    output = re.sub(r"<think>.*?</think>", "", output, flags=re.S).strip()
    meta = {"elapsed_seconds": elapsed, "eval_count": result.get("eval_count"),
            "prompt_eval_count": result.get("prompt_eval_count"), "model": result.get("model")}
    return output, meta


def split_sections(document: str, target_tokens: int) -> list[str]:
    sections = [x.strip() for x in document.split("\n\n") if x.strip()]
    chunks, current, current_n = [], [], 0
    for section in sections:
        n = proxy_tokens(section)
        if current and current_n + n > target_tokens:
            chunks.append("\n\n".join(current)); current, current_n = [], 0
        current.append(section); current_n += n
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def compression_prompt(text: str, level: str) -> str:
    return (
        f"You are a factual compression component. This is level {level}.\n"
        "Do not answer a question: no question is provided. Read only the source text below.\n"
        "Write a concise factual record for future readers. Preserve exact names, numbers, dates, "
        "state changes, negations, conditions, and relations. Never invent a value. If details "
        "conflict, retain the conflict instead of resolving it. Keep identifiers and answer-like "
        "strings exactly. Output only the compressed record, with no preface.\n\n"
        f"SOURCE TEXT:\n{text}"
    )


def build_compressions(document: str) -> tuple[dict, list[dict]]:
    RAW_OUT.mkdir(parents=True, exist_ok=True)
    calls: list[dict] = []
    call_path = RAW_OUT / "compression_calls.jsonl"
    call_path.write_text("")

    def run(method: str, node_id: str, prompt: str, max_output: int) -> str:
        output, meta = call_ollama(prompt, num_predict=max_output, seed_offset=len(calls) + 1)
        item = {"kind": "compression", "method": method, "node_id": node_id,
                "prompt": prompt, "response": output, **meta}
        calls.append(item)
        with call_path.open("a") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        return output

    chunks = split_sections(document, CONFIG["chunk_proxy_tokens"])
    one_shot = run("one_shot", "document", compression_prompt(document, "global"), 480)
    chunk_summaries = [run("chunk", f"chunk-{i:02d}", compression_prompt(chunk, "chunk"), 220)
                       for i, chunk in enumerate(chunks)]
    levels = [chunk_summaries]
    level = chunk_summaries
    level_number = 1
    while len(level) > 1:
        merged = []
        for i in range(0, len(level), CONFIG["hierarchy_group"]):
            group = level[i:i + CONFIG["hierarchy_group"]]
            source = "\n\n--- CHILD SUMMARY ---\n\n".join(group)
            merged.append(run("hierarchical", f"level-{level_number + 1}-node-{i // CONFIG['hierarchy_group']:02d}",
                              compression_prompt(source, f"hierarchy-{level_number + 1}"), 260))
        levels.append(merged); level = merged; level_number += 1

    artifact = {
        "model": CONFIG["model"], "temperature": CONFIG["temperature"],
        "num_ctx": CONFIG["num_ctx"], "document_proxy_tokens": proxy_tokens(document),
        "chunk_proxy_tokens_target": CONFIG["chunk_proxy_tokens"], "chunk_count": len(chunks),
        "chunks": chunks, "one_shot": one_shot, "chunk_summaries": chunk_summaries,
        "hierarchy_levels": levels, "hierarchical_final": levels[-1],
        "question_blind": True, "calls": len(calls),
    }
    (RAW_OUT / "compression_artifacts.json").write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    return artifact, calls


if __name__ == "__main__":
    document = (ROOT / "data" / "generated" / "pilot_document.txt").read_text()
    artifact, calls = build_compressions(document)
    print(json.dumps({"chunks": artifact["chunk_count"], "hierarchy_levels": [len(x) for x in artifact["hierarchy_levels"]],
                      "compression_calls": len(calls)}, ensure_ascii=False, indent=2))
