# Limitations and scope

This repository is a research archive, not a validated replacement for dense or sparse Transformer attention.

- The conceptual RCHAM/H-SWM diagrams are design hypotheses, not implementation results.
- Prior-art tables reflect the documented search scope and do not prove that no identical system exists.
- Compression, hierarchy, retrieval, promotion, tiering, and related memory components have substantial prior art. The archive does not claim component-level invention.
- The synthetic experiments do not establish general behavior on real language models. In particular, the Phase 1R implementation did not provide a genuine frozen-model NLL comparison or model-generated q2/q3 answers.
- Reported historical negative results are retained for provenance, but their measurement limits must be read together with the final source audit.
- No end-to-end Transformer integration, GPU kernel, CPU/SSD offload benchmark, or production latency result is included.

The current project status is [FROZEN / ARCHIVED](research/PROJECT_STATUS.md): NOT VALIDATED and NOT FALSIFIED.
