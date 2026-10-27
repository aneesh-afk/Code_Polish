from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


def load_schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def test_phase0_validator_passes():
    import importlib.util

    spec = importlib.util.spec_from_file_location("verify_phase0", ROOT / "verify_phase0.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert module.main() == 0


def test_configuration_has_eight_unique_arms_and_no_paid_model():
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    arms = config["arms"]
    assert [arm["id"] for arm in arms] == [f"A{i}" for i in range(8)]
    assert config["model"]["paid_api"] is False
    assert config["model"]["training"] is False
    assert config["model"]["fine_tuning"] is False


def test_manifest_schema_accepts_well_formed_eligible_record():
    record = {
        "task_id": "candidate-0001",
        "dataset": "PatchEval-Verified",
        "benchmark_case_id": "case-0001",
        "language": "Python",
        "cve_id": "CVE-2024-0001",
        "repository_url": "https://example.invalid/repo",
        "vulnerable_revision": "abc123",
        "evaluator_image": "example/image:tag",
        "metadata_revision": "def456",
        "vulnerable_state_status": "PASS",
        "reference_validation_status": "PASS",
        "reset_status": "PASS",
        "security_validator_available": True,
        "functional_tests_available": True,
        "eligible": True,
        "exclusion_reason": "",
        "audit_date": "2026-10-25",
    }
    validator = Draft202012Validator(load_schema("dataset_manifest.schema.json"), format_checker=FormatChecker())
    assert list(validator.iter_errors(record)) == []


def test_manifest_schema_rejects_eligible_record_with_unresolved_reference_validation():
    record = {
        "task_id": "candidate-0001",
        "dataset": "PatchEval-Verified",
        "benchmark_case_id": "case-0001",
        "language": "Python",
        "cve_id": None,
        "repository_url": "https://example.invalid/repo",
        "vulnerable_revision": None,
        "evaluator_image": None,
        "metadata_revision": None,
        "vulnerable_state_status": "NOT_AVAILABLE",
        "reference_validation_status": "UNKNOWN",
        "reset_status": "PASS",
        "security_validator_available": False,
        "functional_tests_available": False,
        "eligible": True,
        "exclusion_reason": "reference validation unresolved",
    }
    validator = Draft202012Validator(load_schema("dataset_manifest.schema.json"), format_checker=FormatChecker())
    errors = list(validator.iter_errors(record))
    assert errors, "Manifest schema must reject eligible records with unresolved required verification"


def test_manifest_schema_rejects_unavailable_verification_marked_eligible():
    record = {
        "task_id": "candidate-0002",
        "dataset": "PatchEval-Verified",
        "benchmark_case_id": "case-0002",
        "language": "Python",
        "cve_id": None,
        "repository_url": "https://example.invalid/repo",
        "vulnerable_revision": "abc123",
        "evaluator_image": "example/image:tag",
        "metadata_revision": "def456",
        "vulnerable_state_status": "PASS",
        "reference_validation_status": "NOT_AVAILABLE",
        "reset_status": "PASS",
        "security_validator_available": True,
        "functional_tests_available": False,
        "eligible": True,
        "exclusion_reason": "",
    }
    validator = Draft202012Validator(load_schema("dataset_manifest.schema.json"), format_checker=FormatChecker())
    errors = list(validator.iter_errors(record))
    assert errors, "NOT_AVAILABLE reference validation must never satisfy eligibility"


def test_run_record_requires_explicit_verification_statuses():
    schema = load_schema("run_record.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    record = {
        "run_id": "run-1", "task_id": "candidate-0001", "arm_id": "A0",
        "repeat_index": 1, "attempt_index": 1, "protocol_version": "0.1.0",
        "repo_up_revision": "abc", "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "model_revision": "revision-sha", "prompt_sha256": "a" * 64,
        "context_sha256": "b" * 64, "applicability_status": "APPLICABLE",
        "applicability_reason": "", "generation_status": "SUCCESS", "patch_status": "APPLIED",
        "security_status": "NOT_AVAILABLE", "functional_test_status": "NOT_AVAILABLE",
        "semantic_audit_status": "PENDING", "input_tokens": 100, "output_tokens": 200,
        "model_calls": 1, "wall_seconds": 3.5, "started_at_utc": "2026-10-25T10:00:00Z",
    }
    assert list(validator.iter_errors(record)) == []
    record["security_status"] = "PASS"
    # Status is explicitly supplied; tests ensure NOT_AVAILABLE remains a distinct allowed state.
    assert list(validator.iter_errors(record)) == []


def test_audit_csv_columns_are_unique_and_include_eligibility_decision():
    with (ROOT / "audit_schema.csv").open("r", encoding="utf-8", newline="") as handle:
        columns = next(csv.reader(handle))
    assert len(columns) == len(set(columns))
    for field in ["eligible", "exclusion_reason", "reference_validation_status", "reset_status"]:
        assert field in columns


def test_phase0_has_no_fabricated_dataset_or_run_records():
    manifest_rows = [x for x in (ROOT / "dataset_manifest.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    run_rows = [x for x in (ROOT / "results/raw_runs.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    assert not manifest_rows
    assert not run_rows


def test_audit_schema_accepts_complete_blinded_review_record():
    record = {
        "run_id": "run-1",
        "reviewer_id": "reviewer-a",
        "initial_label": "CORRECT",
        "second_reviewer_label": "INCORRECT",
        "adjudicated_label": "INCOMPLETE",
        "rationale_category": "root_cause_partially_addressed",
        "rationale_notes": "Illustrative test record only.",
        "reference_patch_revealed_after_initial_review": False,
        "audit_date": "2026-10-25",
    }
    validator = Draft202012Validator(load_schema("audit_record.schema.json"), format_checker=FormatChecker())
    assert list(validator.iter_errors(record)) == []


def test_manifest_schema_rejects_eligible_record_missing_security_validator_field():
    record = {
        "task_id": "candidate-0003",
        "dataset": "PatchEval-Verified",
        "benchmark_case_id": "case-0003",
        "language": "Python",
        "cve_id": None,
        "repository_url": "https://example.invalid/repo",
        "vulnerable_revision": "abc123",
        "evaluator_image": "example/image:tag",
        "metadata_revision": "def456",
        "vulnerable_state_status": "PASS",
        "reference_validation_status": "PASS",
        "reset_status": "PASS",
        "functional_tests_available": False,
        "eligible": True,
        "exclusion_reason": "",
    }
    validator = Draft202012Validator(load_schema("dataset_manifest.schema.json"), format_checker=FormatChecker())
    assert list(validator.iter_errors(record)), "Missing security-validator availability must not pass eligibility"


def test_unknown_run_status_is_rejected():
    record = {
        "run_id": "run-2", "task_id": "candidate-0001", "arm_id": "A0",
        "repeat_index": 1, "attempt_index": 1, "protocol_version": "0.1.0",
        "repo_up_revision": "abc", "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "model_revision": "revision-sha", "prompt_sha256": "a" * 64,
        "context_sha256": "b" * 64, "applicability_status": "APPLICABLE",
        "applicability_reason": "", "generation_status": "SUCCESS", "patch_status": "APPLIED",
        "security_status": "SUCCESS", "functional_test_status": "NOT_AVAILABLE",
        "semantic_audit_status": "PENDING", "input_tokens": 100, "output_tokens": 200,
        "model_calls": 1, "wall_seconds": 3.5, "started_at_utc": "2026-10-25T10:00:00Z",
    }
    validator = Draft202012Validator(load_schema("run_record.schema.json"), format_checker=FormatChecker())
    assert list(validator.iter_errors(record)), "Arbitrary labels such as SUCCESS must not replace the explicit PASS state"
