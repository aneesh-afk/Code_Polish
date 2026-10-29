"""
repair_pipeline/task_loader.py - Stable task loading and validation interface.

Loads task metadata from:
- dataset_manifest.jsonl (official schema)
- PatchEval verified source JSON
- In-memory dictionaries / synthetic fixtures for testing

Enforces Protocol v0.1.0 eligibility rules:
- Language must be Python.
- Required fields must be non-empty and well-typed.
- Reference patch information is sequestered and NEVER accessible to the repair prompt.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


class TaskValidationError(Exception):
    """Raised when task metadata is missing required fields or violates protocol rules."""


@dataclass
class TaskMetadata:
    """Validated task metadata for a repair run."""

    task_id: str
    benchmark_case_id: str
    language: str
    repository_url: str
    cve_id: Optional[str] = None
    cwe_ids: List[str] = field(default_factory=list)
    cve_description: str = ""
    target_file: str = ""
    target_region: str = ""
    target_line: Optional[int] = None
    vulnerable_revision: Optional[str] = None
    evaluator_image: Optional[str] = None
    evaluator_image_digest: Optional[str] = None
    dataset: str = "PatchEval-Verified"
    metadata_revision: Optional[str] = None
    vulnerable_state_status: str = "UNKNOWN"
    reference_validation_status: str = "UNKNOWN"
    reset_status: str = "UNKNOWN"
    security_validator_available: bool = True
    functional_tests_available: bool = False
    eligible: bool = True
    exclusion_reason: str = ""
    # Oracle / Ground-truth fields: strictly sequestered from repair prompt
    _reference_patch: Optional[str] = field(default=None, repr=False)
    _hidden_test_source: Optional[str] = field(default=None, repr=False)

    def validate(self) -> None:
        """Validate task metadata against protocol requirements."""
        if not self.task_id or not isinstance(self.task_id, str):
            raise TaskValidationError("Task must have a non-empty string task_id.")
        if not self.benchmark_case_id or not isinstance(self.benchmark_case_id, str):
            raise TaskValidationError("Task must have a non-empty string benchmark_case_id.")
        if not self.language or self.language.strip().lower() != "python":
            raise TaskValidationError(
                f"Protocol requires Python tasks only. Got language: {self.language!r}"
            )
        if not self.repository_url or not isinstance(self.repository_url, str):
            raise TaskValidationError("Task must specify a valid repository_url.")
        if not self.target_file:
            raise TaskValidationError("Task must specify target_file.")

    def get_public_task_statement(self) -> Dict[str, Any]:
        """Returns safe task information for prompt generation.
        
        Guarantees that reference_patch and hidden test sources are excluded.
        """
        return {
            "task_id": self.task_id,
            "cve_id": self.cve_id or "N/A",
            "cwe_ids": list(self.cwe_ids),
            "cve_description": self.cve_description or "No description provided.",
            "target_file": self.target_file,
            "target_region": self.target_region or "Target function/region specified by task.",
            "target_line": self.target_line,
        }


def load_task_from_dict(data: Dict[str, Any], validate: bool = True) -> TaskMetadata:
    """Construct a TaskMetadata instance from a raw dictionary."""
    # Normalize cwe_ids
    cwe_raw = data.get("cwe_ids") or data.get("cwe") or []
    if isinstance(cwe_raw, str):
        cwe_ids = [cwe_raw] if cwe_raw.strip() else []
    elif isinstance(cwe_raw, list):
        cwe_ids = [str(x) for x in cwe_raw if x]
    else:
        cwe_ids = []

    # Target file and region resolution
    target_file = data.get("target_file") or data.get("file") or ""
    target_region = (
        data.get("target_region")
        or data.get("vulnerable_function")
        or data.get("vuln_func")
        or ""
    )
    if not target_file and "vulnerable_location" in data:
        loc = str(data["vulnerable_location"])
        if ":" in loc:
            target_file = loc.split(":")[0]

    task = TaskMetadata(
        task_id=str(data.get("task_id") or data.get("id") or ""),
        benchmark_case_id=str(data.get("benchmark_case_id") or data.get("case_id") or data.get("task_id") or ""),
        language=str(data.get("language") or "Python"),
        repository_url=str(data.get("repository_url") or data.get("repo_url") or data.get("repo") or ""),
        cve_id=data.get("cve_id") or data.get("cve"),
        cwe_ids=cwe_ids,
        cve_description=str(data.get("cve_description") or data.get("description") or ""),
        target_file=target_file,
        target_region=target_region,
        target_line=data.get("target_line") or data.get("line"),
        vulnerable_revision=data.get("vulnerable_revision") or data.get("commit"),
        evaluator_image=data.get("evaluator_image") or data.get("docker_image"),
        evaluator_image_digest=data.get("evaluator_image_digest"),
        dataset=str(data.get("dataset") or "PatchEval-Verified"),
        metadata_revision=data.get("metadata_revision"),
        vulnerable_state_status=str(data.get("vulnerable_state_status") or "UNKNOWN"),
        reference_validation_status=str(data.get("reference_validation_status") or "UNKNOWN"),
        reset_status=str(data.get("reset_status") or "UNKNOWN"),
        security_validator_available=bool(data.get("security_validator_available", True)),
        functional_tests_available=bool(data.get("functional_tests_available", False)),
        eligible=bool(data.get("eligible", True)),
        exclusion_reason=str(data.get("exclusion_reason") or ""),
        _reference_patch=data.get("reference_patch") or data.get("patch"),
        _hidden_test_source=data.get("hidden_test_source") or data.get("test_patch"),
    )

    if validate:
        task.validate()

    return task


def load_tasks_from_manifest(manifest_path: Path | str, validate_all: bool = True) -> List[TaskMetadata]:
    """Load tasks from a dataset_manifest.jsonl file."""
    path = Path(manifest_path)
    if not path.is_file():
        raise FileNotFoundError(f"Manifest not found: {path}")

    tasks: List[TaskMetadata] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                raw = json.loads(line_str)
                task = load_task_from_dict(raw, validate=validate_all)
                tasks.append(task)
            except Exception as e:
                raise TaskValidationError(f"Invalid record on line {line_no} of {path}: {e}") from e

    return tasks
