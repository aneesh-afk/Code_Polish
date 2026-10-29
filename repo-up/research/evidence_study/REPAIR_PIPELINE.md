# Repo-Up Repair Pipeline and Evidence Selection Integration

**Protocol ID:** `repo-up-evidence-study`  
**Protocol Version:** `0.1.0`  
**Role:** Teammate 2 — Implementation Engineer (Repo-Up Integration and Repair Methods)  
**Date:** 2026-10-29

---

## 1. Overview and Architecture

The **Repo-Up Repair Pipeline** (`research.evidence_study.repair_pipeline`) provides a controlled, reproducible execution harness for comparing repository-level vulnerability repair methods under **Protocol v0.1.0**.

It integrates Repo-Up's static AST parsing, file-level dependency analysis, and isolated workspace sandboxing to evaluate whether enrichment with structural or runtime evidence pays off compared to a minimal baseline.

```
+-----------------------------------------------------------------------------------------------------+
|                                        REPAIR PIPELINE LIFECYCLE                                    |
+-----------------------------------------------------------------------------------------------------+
|                                                                                                     |
|  1. Task Loading (task_loader.py)                                                                   |
|     - Validates required fields, Python language scope, and target paths.                           |
|     - Sequesters reference patches and evaluator internals (no prompt leakage).                    |
|                                         |                                                           |
|                                         v                                                           |
|  2. Workspace Isolation (execution_sandbox.py)                                                      |
|     - Creates a dedicated copy of repo in a fresh temporary sandbox per task/arm.                   |
|     - Sanitizes environment variables (strips host secrets/credentials).                            |
|                                         |                                                           |
|                                         v                                                           |
|  3. Context Extraction (context_extractor.py)                                                       |
|     - AST: imports, enclosing class/function definitions, bounded local statements.                 |
|     - Dependency Graph: file-level import graph from services.graph_service (not call/data-flow).   |
|     - Runtime Evidence: sanitized official pre-patch validation output.                             |
|                                         |                                                           |
|                                         v                                                           |
|  4. Evidence Selection (evidence_selector.py)                                                       |
|     - Packages evidence for agreed arms: A0, A1, A2, A3 (plus A4-A7).                               |
|     - Computes context SHA-256 digest for reproducibility.                                          |
|                                         |                                                           |
|                                         v                                                           |
|  5. Prompt Rendering (prompt_renderer.py)                                                           |
|     - Injects public task fields and evidence block into prompts/repair_prompt.md.                  |
|     - Verifies byte-identical instruction framing across all arms.                                  |
|     - Actively scans for ground-truth leakage and computes prompt SHA-256 digest.                   |
|                                         |                                                           |
|                                         v                                                           |
|  6. Repair Execution (repair_methods.py)                                                            |
|     - Invokes model with shared generation budget (temp 0.2, top-p 0.95, max_new_tokens 1024).      |
|     - Local open-weights / mock runners; zero paid API usage.                                       |
|                                         |                                                           |
|                                         v                                                           |
|  7. Patch Parsing & Application (patch_handler.py)                                                  |
|     - Extracts unified diff, rejects path traversals outside checkout.                              |
|     - Applies diff hunk-by-hunk; classifies into APPLIED, APPLY_FAILED, MALFORMED, REJECTED, NO_OP. |
|                                         |                                                           |
|                                         v                                                           |
|  8. Fail-Safe Verification (verifier.py & backend/verification/status_policy.py)                    |
|     - Runs official security validator and regression tests independently.                          |
|     - Distinguishes PASS, FAIL, TIMEOUT, ERROR, NOT_AVAILABLE, NOT_RUN.                             |
|     - Enforces: NOT_AVAILABLE/ERROR/TIMEOUT/NOT_RUN can NEVER be verified success.                  |
|                                         |                                                           |
|                                         v                                                           |
|  9. Result Serialization (result_recorder.py)                                                       |
|     - Validates record against schemas/run_record.schema.json (Draft 2020-12).                      |
|     - Appends immutable run record to output JSONL.                                                 |
+-----------------------------------------------------------------------------------------------------+
```

---

## 2. The Four Agreed Repair Methods

All core methods share the identical task manifest, identical initial vulnerable repository state, identical model/generation settings, identical patch application rules, and identical evaluation criteria. **Only the evidence selection strategy varies.**

| Arm | Method Name | Protocol Definition & Controlled Difference |
|---|---|---|
| **A0** | `llm_minimal_context` | CVE description, CWE (if available), benchmark-provided vulnerable function/region, target file. No Repo-Up AST or dependency graph evidence. |
| **A1** | `llm_plus_ast_context` | **A0 plus** relevant imports in the file, enclosing class/function definitions, and bounded local AST/source statements (+/- 15 lines). |
| **A2** | `llm_plus_file_graph_context` | **A0 plus** relevant code selected from Repo-Up's **file-level import/dependency graph**. *(Explicitly noted in prompts that this is a file-level import graph, not a function-level call graph or data-flow graph).* |
| **A3** | `llm_plus_pre_patch_runtime_evidence` | **A0 plus** a sanitized summary of output/status from the official benchmark vulnerable-state validator. Never discloses test source or exploit payload. |

### Secondary / Controlled Arms (Included in Pipeline)
- **A4 (`llm_plus_targeted_diagnostic_probes`)**: A0 + bounded observations from existing benchmark inputs. Emits `NOT_APPLICABLE` when no safe probe exists.
- **A5 (`bounded_iterative_repair_with_test_feedback`)**: A0 starts the attempt; up to 3 bounded retry attempts with sanitized validator feedback.
- **A6 (`repo_up_deterministic_repair_only`)**: Applies Repo-Up rule-based deterministic repair only where a predeclared rule matches; otherwise abstains.
- **A7 (`abstain_no_patch`)**: Emits `ABSTAIN` (risk/coverage reference arm).

---

## 3. Fail-Safe Verification Semantics

Per Section 4 of the protocol and Teammate 1 runtime audit findings, verification results are treated as distinct states, not a single Boolean.

### Status Categorization
- `PASS`: Check ran and verified expected behavior.
- `FAIL`: Check ran and detected vulnerability or functional breakage.
- `TIMEOUT`: Execution exceeded allocated timeout limit.
- `ERROR`: Process crashed, infrastructure fault, or bad exit.
- `NOT_AVAILABLE`: Test suite or environment was unavailable.
- `NOT_APPLICABLE`: Arm or task not applicable.
- `NOT_RUN`: Patch failed to apply cleanly; tests were not executed.

### Critical Rules Enforced in Code
1. `NOT_AVAILABLE`, `ERROR`, `TIMEOUT`, and `NOT_RUN` **must never** be treated as successful verification (`is_verified == False`).
2. A passing security test **does not** prove general functional correctness.
3. A passing regression suite **does not** automatically prove that the intended vulnerability is fixed.
4. A patch that does not apply cleanly (`APPLY_FAILED`, `MALFORMED`, `REJECTED`) is marked `NOT_RUN` and **cannot** be reported as verified.
5. Missing tests are recorded explicitly as `NOT_AVAILABLE`.
6. A model's self-assertion that its patch is correct is completely disregarded.

---

## 4. Anti-Leakage & Ground-Truth Sequestering

To prevent data leakage:
- Task loader stores `_reference_patch` and `_hidden_test_source` as internal attributes that are excluded from `get_public_task_statement()`.
- `prompt_renderer.py` performs active substring checking: if any ground-truth patch line appears in the rendered prompt, it raises `PromptLeakageError` immediately.
- Sanitizer strips exploit payloads and local file paths from runtime evidence.

---

## 5. File Inventory & Integration Summary

### Pipeline Package (`research/evidence_study/repair_pipeline/`)
- [`__init__.py`](file:///e:/Mini_project/repo-up/research/evidence_study/repair_pipeline/__init__.py): Exposes clean public API.
- [`task_loader.py`](file:///e:/Mini_project/repo-up/research/evidence_study/repair_pipeline/task_loader.py): Task metadata loading, schema validation, reference patch sequestration.
- [`context_extractor.py`](file:///e:/Mini_project/repo-up/research/evidence_study/repair_pipeline/context_extractor.py): AST parsing, file-level dependency graph extraction, runtime output sanitization.
- [`evidence_selector.py`](file:///e:/Mini_project/repo-up/research/evidence_study/repair_pipeline/evidence_selector.py): Evidence packaging for A0–A7, context SHA-256 hashing.
- [`prompt_renderer.py`](file:///e:/Mini_project/repo-up/research/evidence_study/repair_pipeline/prompt_renderer.py): Prompt rendering with `repair_prompt.md`, leakage guardrails, prompt SHA-256 hashing.
- [`patch_handler.py`](file:///e:/Mini_project/repo-up/research/evidence_study/repair_pipeline/patch_handler.py): Unified diff extraction, path escape rejection, hunk application, status classification.
- [`execution_sandbox.py`](file:///e:/Mini_project/repo-up/research/evidence_study/repair_pipeline/execution_sandbox.py): Temp sandbox isolation, process timeouts, credential stripping.
- [`verifier.py`](file:///e:/Mini_project/repo-up/research/evidence_study/repair_pipeline/verifier.py): Independent security and regression test evaluation.
- [`repair_methods.py`](file:///e:/Mini_project/repo-up/research/evidence_study/repair_pipeline/repair_methods.py): Model runners (local open-weights / mock / deterministic).
- [`result_recorder.py`](file:///e:/Mini_project/repo-up/research/evidence_study/repair_pipeline/result_recorder.py): JSONL serialization and `run_record.schema.json` Draft 2020-12 validation.
- [`pipeline.py`](file:///e:/Mini_project/repo-up/research/evidence_study/repair_pipeline/pipeline.py): Master lifecycle orchestrator (`execute_repair_run`).

### Backend Core Fixes (`backend/`)
- [`backend/verification/status_policy.py`](file:///e:/Mini_project/repo-up/backend/verification/status_policy.py): Added shared fail-safe status policy (`is_verified_pass`).
- [`backend/verification/result.py`](file:///e:/Mini_project/repo-up/backend/verification/result.py): Added `TIMEOUT`, `NOT_RUN`, `FAIL`, and fail-safe `is_verified` property.
- [`backend/routes/sandbox.py`](file:///e:/Mini_project/repo-up/backend/routes/sandbox.py): Fixed bug where `NOT_AVAILABLE` was treated as passing; now emits `verification_incomplete` and rolls back unverified changes.
- [`backend/test_status_policy.py`](file:///e:/Mini_project/repo-up/backend/test_status_policy.py): Regression unit tests for verification status policy.

### Tests Added
- [`research/evidence_study/tests/test_repair_pipeline.py`](file:///e:/Mini_project/repo-up/research/evidence_study/tests/test_repair_pipeline.py): 19 comprehensive unit tests covering all failure modes, isolation, anti-leakage, diff patching, and schema serialization.

---

## 6. How to Run Tests

```bash
# Set PYTHONPATH to include repo-up and backend
$env:PYTHONPATH="E:\Mini_project\repo-up:E:\Mini_project\repo-up\backend"

# Run Phase 0 protocol consistency checks
python research/evidence_study/verify_phase0.py

# Run all evidence study tests
python -m pytest research/evidence_study/tests

# Run all backend unit tests
python -m pytest backend
```
