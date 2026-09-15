# RCHAM Research Closeout

> **Superseded scientific interpretation, 2026-09-15.** This remote contribution is preserved in full as the earlier closeout based on reported results. A subsequent direct audit of source and original traces found a lexical coverage scorer, constant q1 correctness, ineffective seed variation, and evidence-only metrics/gate. Full cache disagreement is 60 cells: Task 0 wins, 24 losses, 36 ties. The project STOP decision remains; the general real-model task-utility claim was not adequately tested. See [the final source-backed closeout](research_closeout.md) and its archived raw evidence. The original numbers below are historical and must not be cited without this correction.

**Date:** 2026-09-15  
**Status:** **TERMINATED AS A NOVEL ARCHITECTURE DIRECTION**  
**Reason:** the central predictive hypothesis did not survive a discriminative experiment, so the evidence does not justify implementing the full architecture.

## 1. Bottom line

The broad RCHAM idea combined local/sparse attention, historical compression, hierarchical routing, raw fallback, post-use utility, promotion/demotion, and heterogeneous KV residency.

Prior-art review showed that nearly every large component already has strong precedent. The remaining candidate contribution was narrowed to a specific feedback principle:

> After an unexpected first query `q1`, use the demonstrated task utility of retrieved historical information to decide which internal KV evidence should receive higher future retention / precision / residency for later queries `q2/q3`.

That principle was tested twice. The first test was later judged **NON-IDENTIFIABLE** because RMM-like and Task Utility produced the same retention decisions. A corrected discriminative test then forced genuine policy disagreement. In that test, Task Utility did **not** outperform the RMM-like signal; it performed substantially worse on the cases where the two policies actually disagreed.

Therefore:

> **The project does not have enough evidence to justify building the full RCHAM hierarchy, decay controller, Transformer integration, or GPU/CPU/SSD runtime.**

This is a project-level stop decision, not a universal theorem about all future memory systems.

---

## 2. Research question that survived the literature audit

After the architecture-wide prior-art audit, the broad novelty claim was rejected. The only narrow interface that remained plausible was:

```text
write history while future query is unknown
→ compress / demote while preserving raw fallback
→ q1 unexpectedly needs old evidence
→ cold/raw recall serves q1
→ observe post-use evidence from q1
→ attribute utility to specific internal KV evidence
→ change future retention / precision / residency
→ memory pressure
→ q2/q3 reuse
→ later demotion / decay
```

The important distinction was between:

- **past utility**: whether a memory helped an already observed query;
- **future usefulness**: whether that memory will matter for an unknown future query.

The experiments were designed to test whether better measurement of past task utility provides enough signal to improve future memory retention.

---

## 3. Prior-art conclusion

The literature audit found substantial prior work for each major component:

- local / sparse attention;
- KV / context compression;
- query-agnostic eviction;
- landmark and coarse-to-fine routing;
- raw fallback;
- attention-, recency-, and frequency-based retention;
- demonstrated utility and predicted future utility;
- semantic / episodic memory;
- promotion, demotion, and decay;
- GPU / CPU / SSD tiering and paging;
- lifecycle and serving-level cache management.

The audit did **not** confirm a single public method that implements the exact full closed loop above, but that was insufficient to make the architecture itself novel. The project therefore moved to a minimal falsification test instead of full implementation.

---

## 4. Phase 1 — Minimal Principle Test

### Initial hypothesis

`q1` task-level counterfactual utility would predict later useful retention better than recency, frequency, attention, or an RMM-like demonstrated signal.

### Scale

- 96 episodes
- 576 policy runs
- seeds: 7, 11, 19
- capacities: 8, 16
- pressure: 2x, 4x
- policies: Recency, Frequency, Attention, RMM-like, Task Utility, Oracle Future Reuse

### Initial aggregate result

| Policy | Future retention | q2 accuracy | q3 accuracy |
|---|---:|---:|---:|
| Attention | 0.000 | 0.000 | 0.000 |
| Recency / Frequency | 0.000 | 0.000 | 0.000 |
| RMM-like | 0.458 | 0.375 | 0.500 |
| Task Utility | 0.458 | 0.375 | 0.500 |
| Oracle Future Reuse | 0.823 | 1.000 | 1.000 |

This initially looked like a NO-GO because Task Utility added no benefit over RMM-like.

### Audit correction

A post-hoc audit showed that the benchmark could not actually distinguish the two policies:

- score vectors differed in 36/96 episode-budget units;
- mean Pearson correlation: 0.9218;
- mean Spearman correlation: 0.9990;
- Top-1 / Top-2 / Top-K Jaccard: 1.0 for all 96 units;
- retained-set disagreement: 0/96;
- different eviction decisions: 0/4,152;
- rank reversal `RMM A>B, Task B>A`: 0;
- downstream q2/q3 disagreement: 0.

The cause was structural:

1. the RMM-like score was effectively `attention_weight × answer_correct`, with `answer_correct=True` throughout;
2. the original Task Utility proxy was evidence-coverage based rather than a real counterfactual answer loss;
3. both policies promoted the same positive-evidence set;
4. the answer proxy was binary and could not expose score-magnitude differences.

Verdict for this stage: **B. NON-IDENTIFIABLE**.

---

## 5. Phase 1R — Discriminative Principle Test

Phase 1R was the one permitted redesign. Its purpose was to make the two policies genuinely disagree before drawing a conclusion.

### Corrections

- Task Utility used a fixed answer scorer and per-block masking:

```text
utility(block_i, q1) = logp(full) - logp(masked_i)
```

- RMM-like used `q1 attention × frozen-model correctness` as a block-level adaptation; this was explicitly not claimed to be the original token-level fixed-lag RMM implementation.
- All policies shared the same q1 candidate set, capacity, and `capacity // 2` admission budget.
- Recency, Frequency, and Attention received the same post-q1 admission/update opportunity.
- A pre-flight disagreement gate required real policy disagreement before the formal run.

### Pre-flight / identifiability result

| Metric | Result |
|---|---:|
| episode-budget units | 108 |
| score vectors different | 108/108 |
| retained-set disagreement | 24/108 = 22.2% |
| eviction decision disagreement | 60/108 |
| mean Pearson | 0.2596 |
| mean Spearman | 0.2000 |
| rank-reversal units | 12 |
| mean Top-K Jaccard | 1.000 |

The retained-set disagreement threshold exceeded the required 20%, so the discriminative test was allowed to proceed.

### Final result on the 24 disagreement units

| Policy | Future retention | q2 accuracy | q3 accuracy |
|---|---:|---:|---:|
| RMM-like | **0.833** | **1.000** | **1.000** |
| Task Utility | 0.083 | 0.000 | 0.000 |

Conditional win rate for Task Utility:

- future-retention wins: **0/24**
- q2/q3 accuracy wins: **0/24**

### Aggregate result across all 108 units

| Policy | Future retention | q2 accuracy | q3 accuracy |
|---|---:|---:|---:|
| RMM-like | **0.556** | **0.556** | **0.667** |
| Task Utility | 0.389 | 0.333 | 0.444 |

### Observed failure modes

- `cross_event`: the lexical answer scorer could treat one block as already containing enough answer signal, driving another block's counterfactual utility toward zero;
- `redundant_evidence`: if two blocks can each answer q1 independently, leave-one-out utility does not tell which copy will matter for q2;
- `obsolete_information`: a block can be genuinely useful for q1 and still be the wrong block to keep for q2/q3.

### Verdict

**NO-GO.**

The corrected experiment did not merely fail to show an advantage. On the actual disagreement cases, task-level post-use counterfactual utility was systematically worse than the RMM-like signal in this synthetic lifecycle.

---

## 6. Central falsified assumption

The architecture depended on a bridge from past demonstrated importance to future retention value:

```text
important for q1
→ therefore deserves more future cache resources
```

The experiment did not support this bridge.

The stronger conclusion supported by the project is:

```text
Past utility != future usefulness
```

More precisely:

> When future queries are unknown, improving the measurement of how much an item helped a previous answer is not, by itself, enough to identify which information should receive scarce future KV resources.

This is why the project should not continue by adding hierarchy, decay, or hardware tiers around the failed predictor.

---

## 7. Cache-locality interpretation

Classic cache policies rely heavily on locality assumptions:

- **temporal locality**: recently used items are more likely to be used again soon;
- **spatial locality**: nearby items tend to be accessed together.

For long-context semantic memory with unknown future queries, these assumptions are not a sufficient organizing principle. A future query may target an old rare fact and ignore the information that was most recently or most strongly useful.

This project therefore does **not** claim that temporal or spatial locality never exists in LLM workloads. The narrower supported conclusion is:

> **Temporal / spatial cache locality is insufficient to determine future semantic importance under unknown future queries.**

Likewise, post-use task utility is also insufficient on its own.

---

## 8. What is terminated

The following are closed as active research directions in this repository unless a genuinely new hypothesis is approved:

- RCHAM as a novel end-to-end architecture claim;
- task-level q1 counterfactual utility as the central future-retention signal;
- implementing hierarchy, decay, promotion/demotion, or GPU/CPU/SSD tiering merely to rescue that failed signal;
- full Transformer integration or kernel work based on the current hypothesis.

Do not restart these by changing only a scoring function or adding more system components.

---

## 9. What remains reusable

The following artifacts remain useful for future projects:

- architecture-wide prior-art methodology;
- paper evidence ledger and publication-status checks;
- lifecycle timeline discipline: write → q1 → post-use observation → pressure → q2/q3;
- synthetic benchmark generator;
- equal-budget policy harness;
- raw-trace-first evaluation;
- disagreement pre-flight checks;
- GO / NO-GO gates;
- negative-result preservation.

The most important methodological lesson is that a benchmark must first demonstrate that competing mechanisms make different decisions before their downstream performance can be interpreted.

---

## 10. Claims that must NOT be made

This project does **not** prove:

- that task-level utility is useless for all real LLMs;
- that RMM is universally superior;
- that no future query can ever be predicted;
- that temporal locality never exists in LLM serving;
- that hierarchical memory cannot work;
- that the broad architecture is impossible to engineer.

The Phase 1R result used a synthetic lifecycle and a frozen answer scorer. It is sufficient to reject the current project hypothesis and stop further engineering investment, but not to establish a universal impossibility theorem.

---

## 11. Reactivation rule

This research line may be reopened only if a new hypothesis supplies evidence unavailable to the failed design, for example a new observable signal that targets **future reuse** directly rather than merely measuring past utility, and only after a new prior-art audit.

A restart must be treated as a **new research project**, not Phase 2 of RCHAM.

---

## 12. Repository / provenance note

The GitHub remote visible during closeout was still at commit:

```text
b4548d418e0fba3c17db58bd8a822701abccfb80
research: freeze phase0.5 memory semantics
```

Later experiment work was reported from local commits, including:

```text
e54fe8a167149a3c59ce0fcaed713fcc27abd398  architecture-wide prior-art audit
ff9606587ffb18bfe7b19adcb5ce851347ac3365  Phase 0-B lifecycle gap falsification
9a57f30991525171ed56a5f601b49af920340363  Phase 1 minimal principle test
49182716122da1c9182d544c1e958de9fd30f4fa  Phase 1 audit / NON-IDENTIFIABLE finding
c9b8b19                                      Phase 1R discriminative test / NO-GO
```

Those later commits were not visible through the connected GitHub remote at closeout time. Therefore this document preserves the reported scientific conclusions but does **not** claim that all local code, 19 MB raw traces, manifests, or exact local report files have already been pushed to GitHub.

Before deleting or archiving the local workspace, push or otherwise preserve those local artifacts separately.
