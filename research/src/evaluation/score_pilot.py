#!/usr/bin/env python3
"""Score the Phase 1 pilot from preserved raw outputs; no manual edits."""
from __future__ import annotations

import csv
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "generated"
RAW = ROOT / "results" / "raw"
OUT = ROOT / "results" / "metrics"
FIG = ROOT / "results" / "figures"
TOKEN_RE = re.compile(r"(?:ANS|NUM|DATE|LINK|STATE|RULE|PAIR)-[A-Z0-9-]+", re.I)


def tokens(text: str) -> set[str]:
    return {x.upper() for x in TOKEN_RE.findall(text or "")}


def expected_tokens(value: str) -> set[str]:
    return {x.upper() for x in value.split("|")}


def proxy_tokens(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9]+|[^\s]", text))


def rate(values: list[bool | None]) -> float | None:
    x = [v for v in values if v is not None]
    return None if not x else sum(x) / len(x)


def svg_line_chart(points: list[tuple[float, float, str]], title: str, xlab: str, ylab: str, path: Path) -> None:
    W, H, L, T, R, B = 900, 520, 90, 70, 30, 80
    xvals = [p[0] for p in points]; yvals = [p[1] for p in points]
    xmin, xmax = min(xvals), max(xvals); ymin, ymax = 0.0, 1.0
    def X(x): return L + (x - xmin) / max(xmax - xmin, 1e-9) * (W-L-R)
    def Y(y): return H-B - (y-ymin)/(ymax-ymin) * (H-T-B)
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">',
         f'<rect width="100%" height="100%" fill="#f7f8fb"/>',
         f'<text x="{L}" y="35" font-size="24" font-family="sans-serif" font-weight="bold">{title}</text>',
         f'<line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="#29364d"/>',
         f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="#29364d"/>']
    for y in [0,.25,.5,.75,1]:
        yy=Y(y); svg += [f'<line x1="{L}" y1="{yy}" x2="{W-R}" y2="{yy}" stroke="#d9dee8"/>', f'<text x="18" y="{yy+5}" font-size="14" font-family="sans-serif">{y:.0%}</text>']
    svg += [f'<text x="{W//2-80}" y="{H-20}" font-size="16" font-family="sans-serif">{xlab}</text>', f'<text x="14" y="{(H+T)//2}" transform="rotate(-90 14 {(H+T)//2})" font-size="16" font-family="sans-serif">{ylab}</text>']
    for i,(x,y,label) in enumerate(points):
        color=f"hsl({(i*65)%360},55%,42%)"; svg.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="6" fill="{color}"/>')
        svg.append(f'<text x="{X(x)+8}" y="{Y(y)-8}" font-size="13" font-family="sans-serif" fill="{color}">{label}</text>')
    path.write_text("\n".join(svg+["</svg>"]) + "\n")


def main() -> None:
    questions = {q["question_id"]: q for q in json.loads((DATA / "questions.json").read_text())}
    document = (DATA / "pilot_document.txt").read_text()
    artifact = json.loads((RAW / "compression_artifacts.json").read_text())
    rows = json.loads((RAW / "pilot_rows.json").read_text())
    contexts = {"raw_context": document, "one_shot_summary": artifact["one_shot"],
                "chunk_summary": "\n".join(artifact["chunk_summaries"]),
                "hierarchical_summary": "\n".join(artifact["hierarchical_final"])}
    all_source_tokens = tokens(document)
    summary_unknown = {}
    for method, context in contexts.items():
        method_tokens = tokens(context)
        summary_unknown[method] = sorted(method_tokens - all_source_tokens)

    scored = []
    for row in rows:
        q = questions[row["question_id"]]; answer = row.get("answer", "")
        expected = expected_tokens(row["expected_answer"])
        found = tokens(answer)
        scored_row = dict(row)
        scored_row["expected_all_present"] = expected.issubset(found)
        scored_row["hallucinated_answer_token"] = bool(found - all_source_tokens)
        scored_row["contradictory_known_token"] = bool((found & all_source_tokens) - expected)
        if row["stage"] == "A_direct":
            scored_row["fact_retained_in_representation"] = expected.issubset(tokens(contexts[row["method"]]))
            scored_row["compression_ratio"] = proxy_tokens(contexts[row["method"]]) / proxy_tokens(document)
        elif row["stage"] == "B_route_C_answer":
            if row.get("skip_reason"):
                scored_row["evidence_recall"] = None
                scored_row["c_answer_correct"] = None
                scored_row["c_grounded_qa_correct"] = None
                scored_row["c_hallucinated_answer_token"] = None
                scored.append(scored_row)
                continue
            selected = row.get("selected_chunks", [])
            needed = set(q.get("fact_ids", [q["fact_id"]]))
            selected_text = "\n".join(artifact["chunks"][i] for i in selected)
            scored_row["evidence_recall"] = all(fid in selected_text for fid in needed)
            scored_row["c_answer_correct"] = expected.issubset(found) if selected else None
            # A correct-looking token from a wrong retrieved block is not evidence-grounded.
            scored_row["c_grounded_qa_correct"] = (expected.issubset(found) and scored_row["evidence_recall"]) if selected else None
            scored_row["c_hallucinated_answer_token"] = bool(found - all_source_tokens) if selected else None
        scored.append(scored_row)

    summaries = []
    for method in ["raw_context", "one_shot_summary", "chunk_summary", "hierarchical_summary"]:
        x = [r for r in scored if r["stage"] == "A_direct" and r["method"] == method]
        summaries.append({"method": method, "compression_ratio": x[0]["compression_ratio"],
                          "proxy_tokens": x[0]["context_proxy_tokens"], "questions": len(x),
                          "A_direct_qa_accuracy": rate([r["expected_all_present"] for r in x]),
                          "fact_retention_rate": rate([r["fact_retained_in_representation"] for r in x]),
                          "hallucination_rate": rate([r["hallucinated_answer_token"] for r in x]),
                          "contradiction_rate": rate([r["contradictory_known_token"] for r in x]),
                          "unknown_summary_tokens": summary_unknown[method]})
    # The current pilot's hierarchy B/C rows reuse the chunk-summary lexical
    # router. They remain in raw outputs as a diagnostic, but are excluded from
    # the independent routing result until hierarchy child pointers are tested.
    for method in ["chunk_summary"]:
        x = [r for r in scored if r["stage"] == "B_route_C_answer" and r["method"] == method]
        evaluated = [r for r in x if r.get("evidence_recall") is not None]
        summaries.append({"method": method, "stage": "B_route_C_answer", "questions": len(x),
                          "evaluated_questions": len(evaluated),
                          "B_evidence_recall": rate([r.get("evidence_recall") for r in evaluated]),
                          "C_retrieved_qa_accuracy": rate([r.get("c_answer_correct") for r in evaluated]),
                          "C_grounded_qa_accuracy": rate([r.get("c_grounded_qa_correct") for r in evaluated]),
                          "C_hallucination_rate": rate([r.get("c_hallucinated_answer_token") for r in evaluated]),
                          "mean_retrieved_context_proxy_tokens": statistics.mean([r["retrieved_context_proxy_tokens"] for r in evaluated]),
                          "mean_routing_proxy_tokens": statistics.mean([r["routing_proxy_tokens"] for r in evaluated]),
                          "skipped_multi_evidence": sum(r.get("skip_reason") is not None for r in x)})

    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    (OUT / "pilot_metrics.json").write_text(json.dumps({"experiment_id": "PHASE1-PILOT-001", "document_proxy_tokens": proxy_tokens(document),
        "summaries": summaries, "scored_rows": scored}, ensure_ascii=False, indent=2) + "\n")
    with (OUT / "pilot_summary.csv").open("w", newline="") as f:
        cols = [k for s in summaries for k in s.keys()]; cols = list(dict.fromkeys(cols)); w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(summaries)
    svg_line_chart([(s["compression_ratio"], s["A_direct_qa_accuracy"], s["method"]) for s in summaries if "compression_ratio" in s],
                   "Compression ratio vs direct QA accuracy", "compressed / original proxy tokens", "QA accuracy", FIG / "compression_ratio_vs_qa.svg")
    svg_line_chart([(s["compression_ratio"], s["fact_retention_rate"], s["method"]) for s in summaries if "compression_ratio" in s],
                   "Compression ratio vs fact retention", "compressed / original proxy tokens", "fact retention", FIG / "compression_ratio_vs_retention.svg")
    print(json.dumps({"summary_csv": str(OUT / "pilot_summary.csv"), "methods": len(summaries), "scored_rows": len(scored)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
