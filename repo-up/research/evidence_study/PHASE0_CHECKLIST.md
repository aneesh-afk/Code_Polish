# Phase 0 Completion Checklist

| Requirement | Status | Verification evidence |
|---|---|---|
| Define title, RQs, hypotheses and stop/go decision | PASS | `protocol.md` sections 1–3, 15 |
| Lock primary dataset candidate and eligibility rules without inventing a sample count | PASS | `protocol.md` section 4; manifest intentionally empty pending Phase 1 audit |
| Fix the free, pretrained model family and forbid training/paid APIs | PASS | `config.yaml`; `protocol.md` section 5 |
| Define A0–A7 arms and ensure non-applicable differs from failure | PASS | `config.yaml`; `protocol.md` section 6 |
| Define security, functional, strict-verification, semantic-audit and cost outcomes | PASS | `protocol.md` sections 8–9 |
| Define randomization, isolation, leakage controls and data logging | PASS | `protocol.md` sections 10, 13 |
| Predeclare oracle analysis, paired comparisons, confidence intervals and controller gate | PASS | `protocol.md` section 11; `config.yaml` |
| Define machine-readable task/run/audit schemas | PASS | `schemas/*.schema.json`; schema validation in tests |
| Define eligibility audit CSV and shared repair prompt | PASS | `audit_schema.csv`; `prompts/repair_prompt.md` |
| Keep benchmark manifest and raw results empty until their phases | PASS | `dataset_manifest.jsonl` and `results/raw_runs.jsonl` contain zero records |
| Phase 0 protocol consistency validator | PASS | `python verify_phase0.py` |
| Automated Phase 0 tests | PASS | `python -m pytest -q tests/test_phase0.py`: 11 passed |
| Modify Repo-Up runtime/provider code in Phase 0 | NOT DONE BY DESIGN | Those implementation fixes belong to a later phase; no application source code was changed in Phase 0 |

## Gate

Phase 0 is complete. Phase 1 has **not** started. The official metadata/environment audit, final Python eligible-task count, and any environment-specific findings remain Phase 1 work.
