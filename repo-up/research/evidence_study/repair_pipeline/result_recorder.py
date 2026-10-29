"""
repair_pipeline/result_recorder.py - Record serialization and schema validation.

Validates all run records against `schemas/run_record.schema.json` (Draft 2020-12).
Ensures append-only recording and full reproducibility metadata.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "run_record.schema.json"


@dataclass
class RunRecord:
    """Represents a single experimental attempt record matching run_record.schema.json."""

    run_id: str
    task_id: str
    arm_id: str  # One of A0-A7
    repeat_index: int
    attempt_index: int
    protocol_version: str
    repo_up_revision: Optional[str]
    model_id: Optional[str]
    model_revision: Optional[str]
    prompt_sha256: str
    context_sha256: str
    applicability_status: str  # APPLICABLE, NOT_APPLICABLE
    generation_status: str     # SUCCESS, ABSTAIN, ERROR, TIMEOUT, NOT_RUN
    patch_status: str          # EMPTY, MALFORMED, NO_OP, REJECTED, APPLY_FAILED, APPLIED, NOT_APPLICABLE, NOT_RUN
    security_status: str       # PASS, FAIL, TIMEOUT, ERROR, NOT_AVAILABLE, NOT_APPLICABLE, NOT_RUN
    functional_test_status: str # PASS, FAIL, TIMEOUT, ERROR, NOT_AVAILABLE, NOT_APPLICABLE, NOT_RUN
    semantic_audit_status: str  # CORRECT, INCOMPLETE, INCORRECT, OVERFIT, REGRESSION, UNASSESSABLE, PENDING, NOT_APPLICABLE
    input_tokens: int
    output_tokens: int
    model_calls: int
    wall_seconds: float
    started_at_utc: str
    benchmark_revision: Optional[str] = None
    inference_stack: Optional[str] = None
    quantization_artifact_sha256: Optional[str] = None
    applicability_reason: Optional[str] = None
    gpu_seconds: Optional[float] = None
    runtime_seconds: Optional[float] = None
    retry_count: int = 0
    failure_category: Optional[str] = None
    patch_sha256: Optional[str] = None
    evaluator_image_digest: Optional[str] = None
    randomization_seed: Optional[int] = None
    finished_at_utc: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary, pruning None values for non-required optional fields if appropriate."""
        d = asdict(self)
        # Drop None keys that are not nullable in the schema
        cleaned = {}
        for k, v in d.items():
            if v is not None:
                cleaned[k] = v
            else:
                # Keep keys that allow null in schema
                if k in {
                    "repo_up_revision", "benchmark_revision", "model_id", "model_revision",
                    "inference_stack", "quantization_artifact_sha256", "gpu_seconds",
                    "runtime_seconds", "failure_category", "patch_sha256",
                    "evaluator_image_digest", "randomization_seed", "finished_at_utc"
                }:
                    cleaned[k] = None
        return cleaned


def get_validator() -> Optional[Draft202012Validator]:
    """Load and return the Draft202012Validator for run_record.schema.json."""
    if not Draft202012Validator:
        return None
    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError(f"Schema file not found at: {SCHEMA_PATH}")
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    return Draft202012Validator(schema)


def validate_run_record(record_dict: Dict[str, Any]) -> None:
    """Validate a run record against run_record.schema.json."""
    validator = get_validator()
    if validator:
        validator.validate(record_dict)


def append_run_record(record: RunRecord | Dict[str, Any], output_path: Path | str) -> None:
    """Append a validated run record to a JSONL file."""
    rec_dict = record.to_dict() if isinstance(record, RunRecord) else record
    validate_run_record(rec_dict)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec_dict) + "\n")
