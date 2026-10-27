# Repo-Up Evidence Study — Phase 0

**Working title:** *When Does Repair Evidence Pay Off? An Oracle-Guided Study of Evidence Selection for Python Vulnerability Repair*

This directory contains the Phase 0 protocol and checks only. It does not run the benchmark, download datasets, call a model, change Repo-Up's application code, or claim that any repair is verified.

## Current status

- Phase: `0 — protocol and measurement freeze`
- Protocol version: `0.1.0`
- Protocol status: `FROZEN v0.1.0`; any future methodological change must be recorded as a dated protocol amendment before it affects confirmatory data. The next phase is not started automatically.
- Primary benchmark candidate: PatchEval-Verified. Phase 1 must inspect the official metadata and environments and report the exact eligible Python count; do not assume all 230 cases are Python or eligible.
- Model: free, pretrained `Qwen/Qwen2.5-Coder-7B-Instruct`; no training or fine-tuning. Pin the exact repository revision and inference stack before the pilot/full run, then do not change them inside the confirmatory study.
- Results: `results/raw_runs.jsonl` is deliberately empty. `dataset_manifest.jsonl` is also deliberately empty until Phase 1 completes the eligibility audit.

## Layout

- `protocol.md` — research questions, outcomes, controls, analysis plan, exclusions and phase gates.
- `config.yaml` — machine-readable study choices.
- `prompts/repair_prompt.md` — shared generation prompt and evidence insertion point.
- `schemas/` — JSON Schemas for the task manifest, run records and semantic audit.
- `audit_schema.csv` — blank header/template for the Phase 1 task eligibility audit.
- `verify_phase0.py` — protocol consistency validator; read-only.
- `tests/test_phase0.py` — automated tests for the protocol artifacts.
- `results/` — placeholder for future raw runs and analysis outputs.

## Run the Phase 0 checks

From this directory:

```bash
python -m pip install -r requirements-phase0.txt
python verify_phase0.py
python -m pytest -q tests/test_phase0.py
```

Expected: validator succeeds, all Phase 0 tests pass, and no dataset/run records are present yet.

## Stop/go rule

Do not begin Phase 1 until the user confirms that Phase 0 is complete. Do not start the model pilot or use outcome data to revise the hypothesis or metrics. Any later protocol change must be written to `protocol.md` / `deviations.md`, dated, justified, and labelled as occurring before or after confirmatory runs.
