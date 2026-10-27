# Phase 0 Research Protocol

**Protocol ID:** `repo-up-evidence-study`  
**Version:** `0.1.0`  
**Status:** Frozen v0.1.0 as of 2026-10-25. Any methodological change must be logged as a dated amendment before it affects confirmatory data. The next phase is not started automatically.  
**Date prepared:** 2026-10-25

## 1. Working title and objective

**When Does Repair Evidence Pay Off? An Oracle-Guided Study of Evidence Selection for Python Vulnerability Repair**

The study asks whether adding structural, dependency, runtime, or test-feedback evidence to an LLM repair request improves vulnerability-repair outcomes enough to justify its additional context, execution, and inference cost. Repo-Up is the existing structural-analysis and repair infrastructure. It is not assumed to detect every benchmark CVE; official benchmark task metadata supplies the repair task, while Repo-Up supplies AST and file-level dependency context where available.

This is a Python-first empirical study. A learned controller is a conditional follow-on, not a guaranteed deliverable. If the fixed strategies show little headroom, or the task/repository count cannot support out-of-project evaluation, the appropriate result is the empirical study without a controller.

## 2. Confirmatory research questions

- **RQ1 — Oracle headroom:** How much better is a retrospective per-task choice of evidence strategy than the best single fixed strategy, when both are evaluated on the same tasks and core arms?
- **RQ2 — Predictability:** Can task/repository features available before selecting a strategy predict which fixed strategy is likely to work best on unseen repositories, if sample size supports held-out evaluation?
- **RQ3 — Marginal value:** What gain in validated repairs is associated with adding AST context, file-level dependency-graph context, pre-patch runtime observations, targeted diagnostic observations, or bounded validation feedback, and what additional cost does each incur?
- **RQ4 — False verification:** How often does an automated validator pass a patch that independent semantic review rejects?

Secondary analyses may examine whether structural features add value beyond task metadata and whether Repo-Up deterministic repairs are safe in their applicable subset. These are not grounds for expanding claims beyond the observed data.

## 3. Hypotheses and interpretation guardrails

- **H1:** At least one evidence-enriched arm may outperform the minimal-context arm on security validation, but no arm is assumed to win in advance.
- **H2:** The oracle may expose meaningful room for per-task evidence selection. The oracle is an upper-bound diagnostic, not a deployable strategy and not evidence that a controller will generalize.
- **H3:** Additional evidence may increase token use, elapsed time, or execution cost even when it does not improve repair success.
- **H4:** Some patches that pass automated validation may fail semantic review.

Null or negative findings are valid results. No hypothesis, endpoint, exclusion rule, or arm may be changed after looking at confirmatory outcomes without documenting a protocol deviation and separating affected results from the confirmatory analysis.

## 4. Benchmark and task eligibility

### Primary candidate

Use the official **PatchEval-Verified** metadata and validation environments from `https://github.com/bytedance/PatchEval`. The official project describes a 230-case verified subset and provides task metadata plus Docker-based evaluation resources. This is the candidate pool, **not** the final sample count: Phase 1 must parse the current official metadata and record exactly how many cases are Python, then test each candidate's environment. Never infer a Python count from the total.

### Per-task inclusion requirements

A task is included only if all applicable requirements below are documented in the manifest:

1. Official task metadata identifies the case as Python.
2. The official evaluation environment can be retrieved or is already available, with version/image identity recorded.
3. The clean vulnerable state can be restored reproducibly using the official reset procedure.
4. The official vulnerable-state check reproduces the benchmark-defined vulnerability, when a separate check is provided.
5. The official reference repair or documented reference-validation path can be executed and its result recorded, and that reference validation passes the official security validator. If a reference repair fails a strengthened validator, keep the case in the audit manifest as ineligible for the primary confirmatory set and record the specific failure; do not erase or silently drop it. This rule is applied before any model-generated outcome is examined.
6. Security validation can be invoked in the official environment and its return status interpreted from source/documentation.
7. No rule requires showing the model the reference patch, fixed function, hidden test source, or evaluator internals.

If a requirement cannot be checked, mark the field unknown and exclude from the primary confirmatory set with a specific reason until resolved. Do not label unknown as pass. In particular, `eligible=true` requires a Python task, a reproducible vulnerable state, a passing official reference validation, a passing clean reset, and an available official security validator.

### Exclusions

Exclude cases with unsupported languages, irreproducible setup, unavailable official validator, irrecoverable environment, or unresolved reference validation according to the rules above. Keep excluded cases in the manifest with `eligible=false` and a controlled reason. Exclude only for pre-outcome environment or eligibility reasons; do not exclude a task because the model fails, outputs malformed changes, times out, or performs poorly.

The main confirmatory dataset contains no synthetic vulnerabilities. Repo-Up's existing synthetic fixtures may be used only for unit tests of the harness, never pooled into research outcome metrics.

### Secondary dataset

BugsInPy may be used as a separately labelled external-validity study or as a fallback only after a dated protocol amendment made before confirmatory model outcomes are examined. It is a general Python bug benchmark, not a substitute for the primary security dataset. Never pool its results with PatchEval-Verified security-repair rates.

## 5. Model and compute policy

Use one free, pretrained open-weight model: `Qwen/Qwen2.5-Coder-7B-Instruct` (model card identifies the Apache-2.0 license). No paid hosted API, training, or fine-tuning is allowed in this study. In Phase 2, perform a smoke test on the actually available free GPU and pin the immutable model revision, tokenizer revision, quantization format/artifact hash, inference library versions, generation settings, and hardware. The chosen setup must be frozen before the pilot and never switched during the confirmatory run. A hardware incompatibility must be handled by a dated protocol amendment before confirmatory outcomes, not by changing models mid-run.

Initial generation settings are temperature `0.2`, top-p `0.95`, maximum new tokens `1024`, and prompt budget `8192` tokens. Run three stochastic repeats per task/arm where the arm applies and resources permit. If three repeats prove infeasible during the engineering pilot, stop before the confirmatory run, amend the protocol, and state the reduced repetition plan; do not selectively reduce repetitions for difficult tasks.

Record input/output token counts, calls, wall-clock duration, GPU time when available, retries, and the reason for any incomplete run. There is no paid API monetary cost; report compute/token cost rather than inventing dollar costs. Inference may run on Kaggle or another free GPU runtime. The official Docker benchmark evaluation must run on a Docker-capable host; do not assume Kaggle supports a nested Docker daemon.

## 6. Experimental arms

Every applicable arm receives the same task statement, common prompt, model settings, and output budget. Only the specified evidence block or repair-feedback policy changes. Store the rendered prompt and evidence hash per run. An arm marked `NOT_APPLICABLE` is not counted as a failed repair and must include a predeclared applicability reason.

| Arm | Strategy | Controlled difference |
|---|---|---|
| A0 | LLM with minimal context | CVE description, CWE if available, benchmark-provided vulnerable function/region. No Repo-Up AST or dependency-graph evidence. |
| A1 | LLM + AST context | A0 plus relevant imports, enclosing definitions, bounded local AST/statement context. |
| A2 | LLM + file dependency-graph context | A0 plus relevant code selected from Repo-Up's **file-level import/dependency graph**. Do not call this a function-level call/data-flow graph. |
| A3 | LLM + pre-patch runtime evidence | A0 plus a sanitized summary of output/status from the official vulnerable-state validator, when available. Never disclose test source or exploit implementation. |
| A4 | LLM + targeted diagnostic probes | A0 plus bounded, sanitized observations from existing benchmark inputs/tests where a predeclared safe probe is applicable. No model-generated tests and no hidden test source. If no safe probe is available, mark not applicable. |
| A5 | Bounded iterative repair with test feedback | A0 starts the attempt; after a failed official validation, provide only a sanitized feedback summary and allow retries up to three total patch attempts. Do not expose hidden tests or reference patches. |
| A6 | Repo-Up deterministic repair only | Apply an existing deterministic repair only when a predeclared rule-to-task mapping makes it applicable. Applicability must be established without observing LLM outcomes. Report its applicable denominator separately. |
| A7 | Abstain / no patch | Produce no patch. This is a risk/coverage reference, not a repair success. |

The core oracle comparison uses A0–A3 on the same tasks where all four are applicable. A4–A6 use separate, clearly reported applicable subsets unless a fully matched subset exists. Do not compare rates with different denominators without labelling the denominator. An expanded, per-applicability oracle is exploratory and must not replace the core comparison.

## 7. Common prompt and patch handling

`prompts/repair_prompt.md` defines the shared instruction. The only intended per-arm variation is the content of the evidence block and, for A5, the predeclared bounded feedback stage. The model must not receive benchmark ground-truth patches, fixed functions, hidden tests, test source, validation implementation, environment secrets, or outcome labels. Do not include unrelated repository files by default.

Patches must be saved exactly as generated and separately classified as empty, unparsable, unappliable, applied, or rejected. Never silently normalize a malformed patch into success. The official evaluator is authoritative for the benchmark's automated security-validation result. Repo-Up's own static re-analysis is supplementary and must not replace the official check.

## 8. Outcomes and definitions

### Primary outcome

**Security-validation pass rate:** proportion of eligible attempted task-arm runs for which the official benchmark security validator returns its documented pass result. A nonzero exit, timeout, evaluator error, patch-application error, unavailable validator, or missing result must remain a distinct non-pass status; never convert `NOT_AVAILABLE` to pass.

### Other outcomes

- **Functional-test pass rate:** among cases with official unit/regression tests, proportion passing all required tests. Report the test-availability denominator.
- **Strict verified repair rate:** only for cases with both security validation and official functional tests, a patch counts as successful only if (a) security validation passes, (b) all required functional tests pass, and (c) independent semantic audit labels it `CORRECT`. Report separately from tasks without functional tests.
- **Security-only + semantic correctness:** for tasks without functional tests, report security-validation pass and semantic-audit correctness separately; do not call these fully functionally verified repairs.
- **False-verified rate:** among patches that pass the specified automated validation and receive semantic audit, fraction rejected as incomplete, incorrect, overfit, or regressive. Also report audit coverage and confidence intervals.
- **Cost:** prompt/input tokens, output tokens, model calls, wall time, GPU time if available, probe/runtime time, attempts and retries.
- **Patch failure categories:** generation failure, malformed output, patch application failure, parse/build failure, security validation failure, functional test failure, timeout, infrastructure error, not applicable, or abstention.

`PASS`, `FAIL`, `TIMEOUT`, `ERROR`, `NOT_AVAILABLE`, and `NOT_APPLICABLE` are distinct states. Missing output is never an inferred pass.

## 9. Semantic audit

Use two independent reviewers if feasible. Give reviewers the task description, original target code, generated patch, validation outcomes and relevant non-hidden functional context, but hide the arm name/model strategy when practical. Reviewers must not see the reference patch before making an initial judgement. Label each patch:

- `CORRECT` — addresses the actual root cause and is consistent with expected behavior based on available evidence.
- `INCOMPLETE` — reduces symptoms but leaves a material vulnerability path or root cause.
- `INCORRECT` — does not correctly solve the task.
- `OVERFIT` — tailored to a known test/output while not repairing the underlying issue.
- `REGRESSION` — introduces material behavior breakage or unrelated damage.
- `UNASSESSABLE` — evidence is insufficient; explain why and exclude only from the semantic-audit denominator, never silently turn into correct.

Record reviewer IDs as pseudonyms, independent labels, adjudicated label, rationale category, and whether the reference patch was revealed after initial review. Report agreement (Cohen's kappa or another suitable statistic for the actual number of reviewers) and adjudication policy. If only one reviewer is available, disclose this limitation and avoid implying independent agreement.

## 10. Execution controls and leakage prevention

- Reset each task to the clean vulnerable revision before every task/arm/repeat. Verify reset success before prompt construction.
- Randomize arm order within each task/repeat using a saved seed. Save the seed and ordered run list.
- Run official validation in a constrained container: non-root user, network disabled when supported, CPU/memory/PID/time limits, read-only reference artifacts, no credentials or unrelated host directories mounted. Record any sandbox limitation.
- Never make a generated patch or benchmark repository available to the model through logs that include reference fixes or hidden validation code.
- Use separate write-protected storage for benchmark reference artifacts. Prompts may include only approved task metadata and evidence. Record prompt/context hashes, not just file paths.
- Keep benchmark evaluator logs intact and preserve failures. Re-running is allowed only with a fresh reset and a linked run record.

## 11. Analysis plan

1. Report flow: official task count → language candidates → environment audit → eligible Python cases → exclusions by reason → attempted runs → valid outputs → audited outputs.
2. Report each arm's denominator, security pass rate, functional-test pass rate where available, strict verified repair rate on the proper subset, false-verified rate, and cost.
3. Use paired per-task comparisons for A1 vs A0, A2 vs A0, and A3 vs A0. Apply Holm correction across this predeclared primary contrast family. Report effect sizes and 95% confidence intervals, not p-values alone.
4. Use a repository-cluster bootstrap for uncertainty when the number of repositories permits it. If there are too few independent repositories for stable clustering, report that and include task-level intervals only as a clearly qualified sensitivity analysis.
5. Oracle headroom on the common A0–A3 task set: for task i and arm a, let `y[i,a]` be the binary security-validation outcome (strict correctness can be analysed separately only on its eligible subset). `R_fixed = max_a mean_i(y[i,a])`; `R_oracle = mean_i(max_a y[i,a])`; `H = R_oracle - R_fixed`. The oracle sees all outcomes retrospectively and is not a deployable policy.
6. RQ2 predictive work is permitted only if there are at least 50 eligible tasks across at least five distinct repositories and a repository-held-out design can be used. Use only features available before strategy selection. No random task-level split that puts the same repository in both training and held-out data. If the threshold is unmet, report descriptive associations only.
7. A controller is justified only if estimated core oracle headroom is at least 5 percentage points, the 95% repository-bootstrap confidence interval's lower bound is above zero, and a simple selector improves over the best fixed strategy on held-out repositories without leakage. Otherwise, do not build or claim a generalizing controller; publish the descriptive empirical result or a transparent feasibility conclusion.
8. Include sensitivity analyses for missing functional tests, model-generation failures, non-applicable arms, reference-validation uncertainty, and reviewer disagreement. No synthetic cases in the confirmatory estimates.

## 12. Planned features for RQ2

Allowed pre-selection features include task metadata (CWE, description length, supplied vulnerable-region length), AST counts/depth/import counts/local definitions/identifier counts, file-graph in/out degree and neighbourhood size, whether official runtime evidence and functional tests exist, and context/token estimates. All features must be derived from the vulnerable version or official metadata before the selected repair attempt. Do not use the selected arm's outcome, post-patch information, hidden test artifacts, or a feature that cannot be computed at actual decision time. For sequential policies, feedback from a prior attempt may be used only after that attempt is genuinely executed within its predeclared budget.

## 13. Reproducibility and artifacts

Before the confirmatory run, save and hash: this protocol, `config.yaml`, the eligible manifest, Repo-Up commit/hash, official benchmark metadata revision, prompt template, model revision/tokenizer and quantization hashes, dependency lockfile, evaluator image digests, randomization seed, and analysis code commit. Store one append-only JSONL record per task/arm/repeat/attempt. Use stable task IDs and do not write secret values or hidden test source into outputs.

All published tables/figures must be generated from recorded raw outputs by scripts. Report protocol deviations, excluded records and reasons, run failures, and limits to reproducibility. Do not claim the paper proves the model repairs all vulnerabilities or that Repo-Up itself detects all benchmark CVEs.

## 14. Current project constraints to carry forward

The inspected Repo-Up source has a `DummyProvider` as the current `get_provider()` result and its runtime test runner returns `NOT_AVAILABLE` instead of executing tests. The sandbox route currently treats `NOT_AVAILABLE` as a test pass. These facts make verification repair a prerequisite before any confirmatory experiment. They are recorded here but are not fixed in Phase 0. The current dependency graph is file-level and import-based, not a function call/data-flow graph. The current synthetic evaluation is not the confirmatory dataset and is not evidence of real-world security-repair accuracy.

## 15. Phase gates

- **Phase 0 (this phase):** protocol, machine config, templates/schemas, empty manifest, audit CSV and protocol-validation tests are consistent.
- **Phase 1:** audit official PatchEval-Verified metadata and environments, produce eligible/excluded manifest with evidence and exact eligible Python count; stop for review.
- **Phase 2:** repair/verify status semantics and real-model smoke test, with tests proving that unavailable verification cannot be success.
- **Pilot:** small, predeclared engineering pilot to validate infrastructure; its results are not confirmatory. Freeze model, prompts, evaluator and run settings after the pilot.
- **Confirmatory run:** do not begin before dataset, software, model, prompt and protocol hashes are frozen.
- **Next phase rule:** no Phase 1 work begins until the user explicitly agrees Phase 0 is done.

## References

1. ByteDance, **PatchEval** repository and PatchEval-Verified update: https://github.com/bytedance/PatchEval (official metadata path: `patcheval/datasets/patcheval_verified.json`; verify the actual checkout/revision in Phase 1).
2. ByteDance, **PatchEval** dataset card: https://huggingface.co/datasets/ByteDance/PatchEval
3. Qwen, **Qwen2.5-Coder-7B-Instruct** model card (Apache-2.0): https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct
4. BugsInPy, **A Database of Real Bugs for Python Programs**: https://github.com/soarsmu/BugsInPy
