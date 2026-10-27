# Repo-Up Phase 1B runtime audit readiness report

**Date:** 2026-10-27  
**Input:** `/mnt/data/patcheval_verified.json` (SHA-256: `8500cbd36892c04a6211d2706bc8170ec2f84dd81469c1056da36265e0399646`)  
**Scope:** Python PatchEval-Verified metadata; runtime eligibility not yet asserted.

## Results
- Records in source JSON: 230
- Python candidates: 70
- Distinct Python repositories: 48
- Python records with image identifiers: 70/70
- Python records with patch URL(s): 70/70
- Python records with vulnerable function metadata: 70/70
- Python records with fixed function metadata: 70/70
- Cases eligible for experiments: **0 confirmed; 70 pending runtime audit**.

## Why runtime audit did not run here
- Docker executable is not installed in this execution environment (`docker: command not found`).
- No benchmark images were pulled, no benchmark container was run, and no untrusted project code was executed.
- Metadata presence and an image tag do not prove that the image can be pulled, the vulnerable state reproduces, the official reference fix passes, or reset is repeatable.

## Repo-Up graphical/tree/graph tooling
Repo-Up's project tree, AST/parser and file-level import dependency graph are useful for extracting repair context and measuring graph-informed evidence. They do **not** replace the benchmark's official vulnerability validator or isolated runtime tests. For this experiment, use Repo-Up graph/AST outputs as treatment evidence, while PatchEval's own task environment and security checks remain the outcome oracle.

## Verification correctness fix included
`repo_up_patch/backend/routes/sandbox.py` previously treated `NOT_AVAILABLE` as a passing test status. It now emits `verification_incomplete`, restores the pre-patch content, and never emits `fix_passed` unless runtime tests explicitly return `PASS` and static/security checks pass. The rule is factored into `verification/status_policy.py` and tested.

## Test status
- New status-policy tests: expected to pass (run separately).
- Existing `backend/test_verification.py`: 2 passed, 1 failed in this environment. The failing parser test returns `NOT_AVAILABLE` because Tree-sitter is not installed; this is an environment/dependency limitation, not a successful parse validation.
- Phase 1A inventory tests could not be collected from the review folder as-is because their import expects a `research` package path. Run them from the intended project/package layout.

## Next gate
Run the official PatchEval-Verified Docker workflow on a Docker-capable Linux host. For every task: pull pinned image, confirm vulnerable PoC fails as expected, apply official reference patch in a clean reset and confirm validator passes, then repeat reset/reproduction. Save logs and image digest. Only then promote individual cases from `PENDING_RUNTIME_AUDIT` to eligible.
