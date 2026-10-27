#!/usr/bin/env python3
"""Read-only consistency checks for Phase 0 research protocol artifacts."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

try:
    import yaml
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:  # pragma: no cover - exercised only in an incomplete environment
    print(
        "Missing Phase 0 validation dependency. Run: "
        "python -m pip install -r requirements-phase0.txt",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc

ROOT = Path(__file__).resolve().parent
REQUIRED_ARM_IDS = {f"A{i}" for i in range(8)}
REQUIRED_AUDIT_COLUMNS = {
    "task_id", "dataset", "benchmark_case_id", "language", "cve_id",
    "repository_url", "vulnerable_revision", "evaluator_image",
    "metadata_revision", "vulnerable_state_status", "reference_validation_status",
    "reset_status", "security_validator_available", "functional_tests_available",
    "eligible", "exclusion_reason", "auditor_id", "audit_date",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_schema(schema_path: Path) -> None:
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)


def main() -> int:
    required_files = [
        "README.md", "protocol.md", "config.yaml", "PHASE0_CHECKLIST.md", "dataset_manifest.jsonl",
        "audit_schema.csv", "verify_phase0.py", "tests/test_phase0.py",
        "prompts/repair_prompt.md", "results/README.md", "results/raw_runs.jsonl",
        "schemas/dataset_manifest.schema.json", "schemas/run_record.schema.json",
        "schemas/audit_record.schema.json",
    ]
    missing = [name for name in required_files if not (ROOT / name).is_file()]
    if missing:
        raise AssertionError(f"Missing required Phase 0 artifacts: {missing}")

    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert config["protocol"]["id"] == "repo-up-evidence-study"
    assert config["protocol"]["version"] == "0.1.0"
    assert config["protocol"]["language_scope"] == ["Python"]
    assert config["protocol"]["primary_benchmark"] == "PatchEval-Verified"
    assert config["protocol"]["status"] == "frozen_v0.1.0"

    arms = config["arms"]
    arm_ids = [arm["id"] for arm in arms]
    assert len(arm_ids) == len(set(arm_ids)), "Arm IDs must be unique"
    assert set(arm_ids) == REQUIRED_ARM_IDS, f"Expected arms {REQUIRED_ARM_IDS}, got {set(arm_ids)}"
    assert config["model"]["paid_api"] is False
    assert config["model"]["training"] is False
    assert config["model"]["fine_tuning"] is False
    assert config["model"]["revision"] == "MUST_BE_PINNED_BEFORE_PILOT"
    assert config["analysis"]["oracle_core_arms"] == ["A0", "A1", "A2", "A3"]
    assert config["analysis"]["controller_minimum_tasks"] >= 1
    assert config["analysis"]["controller_minimum_distinct_repositories"] >= 1

    protocol = (ROOT / "protocol.md").read_text(encoding="utf-8")
    for required_phrase in [
        "NOT_AVAILABLE", "reference patch", "no synthetic vulnerabilities",
        "file-level", "repository-held-out", "Phase 1", "do not begin",
    ]:
        assert required_phrase.lower() in protocol.lower(), f"Protocol missing required guardrail: {required_phrase}"

    # During Phase 0 this must stay empty: it is evidence that no eligibility decisions
    # or outcomes have been fabricated before the official dataset audit.
    manifest_lines = [
        line for line in (ROOT / "dataset_manifest.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert manifest_lines == [], "Phase 0 dataset manifest must remain empty until Phase 1"
    assert (ROOT / "results/raw_runs.jsonl").read_text(encoding="utf-8").strip() == "", (
        "Phase 0 raw run log must remain empty until an approved pilot/experiment"
    )

    with (ROOT / "audit_schema.csv").open("r", encoding="utf-8", newline="") as handle:
        columns = next(csv.reader(handle))
    assert len(columns) == len(set(columns)), "Duplicate CSV audit columns"
    missing_columns = REQUIRED_AUDIT_COLUMNS - set(columns)
    assert not missing_columns, f"Audit schema is missing required columns: {sorted(missing_columns)}"

    schema_paths = sorted((ROOT / "schemas").glob("*.schema.json"))
    assert len(schema_paths) == 3, f"Expected 3 JSON schemas, found {len(schema_paths)}"
    for schema_path in schema_paths:
        validate_schema(schema_path)

    print("PHASE 0 PROTOCOL CHECK: PASS")
    print(f"Artifacts checked: {len(required_files)} required files")
    print(f"Arms: {', '.join(arm_ids)}")
    print(f"JSON schemas: {len(schema_paths)} valid JSON Schema draft 2020-12 documents")
    print("Dataset manifest records: 0 (correct for Phase 0)")
    print("Raw experiment records: 0 (correct for Phase 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
