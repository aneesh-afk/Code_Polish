# Shared Repair Prompt — Protocol v0.1.0

The runner must fill each bracketed field with escaped/serialized content. The `EVIDENCE_BLOCK` is the only field intended to vary between A0–A4. A5 adds only the feedback step defined in the protocol. Keep the common instruction byte-identical across arms.

---

You are assisting with a narrowly scoped Python security repair task.

## Task
- Vulnerability description: `[CVE_DESCRIPTION]`
- CWE (if available): `[CWE]`
- Target function or vulnerable region: `[TARGET_REGION]`
- Repository-relative target file: `[TARGET_FILE]`

## Additional permitted evidence
`[EVIDENCE_BLOCK]`

## Instructions
1. Propose the smallest defensible code change that addresses the underlying vulnerability while preserving intended behavior.
2. Do not claim that a patch has been tested or verified.
3. Do not invent repository files, APIs, dependencies, or test results. State uncertainty through the patch rationale field only if the runner's structured output supports it.
4. Do not produce exploit code, attack payloads, or test source. Do not request or reproduce hidden evaluator information.
5. Return exactly one unified diff that applies to the vulnerable checkout. If you cannot propose a defensible patch, return the literal `ABSTAIN`.
6. Do not include explanatory prose before or after the diff.

---

Runner requirements: preserve exact raw model output; classify `ABSTAIN`, malformed output, no-op diff, failed application, and valid application separately. Do not automatically repair malformed model output into a valid patch. The template is not a substitute for the official evaluator.
