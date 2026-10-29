"""
repair_pipeline/pipeline.py - Master Repair Pipeline Orchestrator.

Integrates the full repair lifecycle for a task and experimental arm:
1. Validates task metadata and eligibility.
2. Spawns an isolated clean checkout sandbox.
3. Extracts AST and file-level dependency graph evidence.
4. Selects evidence and renders shared prompt (guaranteeing no reference leaks).
5. Invokes the repair method with standardized parameters.
6. Parses, validates, and applies the candidate unified diff.
7. Executes isolated fail-safe verification (security + regression).
8. Generates a reproducible, Draft 2020-12 validated RunRecord.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from .evidence_selector import ArmID, SelectedEvidence, select_evidence_for_arm
from .execution_sandbox import IsolatedTaskWorkspace
from .patch_handler import PatchResult, parse_and_apply_patch
from .prompt_renderer import render_repair_prompt
from .repair_methods import BaseRepairRunner, GenerationResult, MockRepairRunner
from .result_recorder import RunRecord, append_run_record, validate_run_record
from .task_loader import TaskMetadata
from .verifier import VerificationReport, VerificationStatus, run_verification

PROTOCOL_VERSION = "0.1.0"


def execute_repair_run(
    task: TaskMetadata,
    arm_id: str | ArmID,
    source_repo_root: str | Path,
    model_runner: Optional[BaseRepairRunner] = None,
    repeat_index: int = 1,
    attempt_index: int = 1,
    protocol_version: str = PROTOCOL_VERSION,
    repo_up_revision: Optional[str] = "git-rev-current",
    runtime_check_output: Optional[str] = None,
    runtime_check_exit_code: int = 1,
    custom_security_runner: Optional[Callable[[Path], Tuple[int, str, str]]] = None,
    custom_functional_runner: Optional[Callable[[Path], Tuple[int, str, str]]] = None,
    output_records_path: Optional[Path | str] = None,
) -> Tuple[RunRecord, VerificationReport]:
    """Execute a single controlled repair run for a task and arm."""
    start_time = time.perf_counter()
    started_at_utc = datetime.now(timezone.utc).isoformat()
    run_id = f"run_{task.task_id}_{arm_id}_rep{repeat_index}_att{attempt_index}_{uuid.uuid4().hex[:8]}"

    runner = model_runner or MockRepairRunner()
    target_arm = arm_id if isinstance(arm_id, ArmID) else ArmID(arm_id.upper())

    # Check Task Eligibility
    if not task.eligible:
        elapsed = time.perf_counter() - start_time
        finished_at_utc = datetime.now(timezone.utc).isoformat()
        rec = RunRecord(
            run_id=run_id,
            task_id=task.task_id,
            arm_id=target_arm.value,
            repeat_index=repeat_index,
            attempt_index=attempt_index,
            protocol_version=protocol_version,
            repo_up_revision=repo_up_revision,
            model_id=runner.model_id,
            model_revision="pinned_v0.1.0",
            prompt_sha256="0" * 64,
            context_sha256="0" * 64,
            applicability_status="NOT_APPLICABLE",
            applicability_reason=task.exclusion_reason or "Task marked ineligible in manifest",
            generation_status="NOT_RUN",
            patch_status="NOT_APPLICABLE",
            security_status="NOT_APPLICABLE",
            functional_test_status="NOT_APPLICABLE",
            semantic_audit_status="NOT_APPLICABLE",
            input_tokens=0,
            output_tokens=0,
            model_calls=0,
            wall_seconds=round(elapsed, 4),
            started_at_utc=started_at_utc,
            finished_at_utc=finished_at_utc,
            notes="Excluded: Task ineligible.",
        )
        report = VerificationReport(
            security_status=VerificationStatus.NOT_APPLICABLE.value,
            functional_test_status=VerificationStatus.NOT_APPLICABLE.value,
            patch_status="NOT_APPLICABLE",
            notes="Task marked ineligible.",
        )
        if output_records_path:
            append_run_record(rec, output_records_path)
        return rec, report

    # 1. Setup Isolated Sandbox Workspace
    with IsolatedTaskWorkspace(source_repo_root) as workspace:
        # 2. Select Evidence for the Arm
        evidence = select_evidence_for_arm(
            arm_id=target_arm,
            task=task,
            repo_root=workspace.workspace_root,
            runtime_output=runtime_check_output,
            runtime_exit_code=runtime_check_exit_code,
        )

        if evidence.applicability_status == "NOT_APPLICABLE":
            elapsed = time.perf_counter() - start_time
            finished_at_utc = datetime.now(timezone.utc).isoformat()
            rec = RunRecord(
                run_id=run_id,
                task_id=task.task_id,
                arm_id=target_arm.value,
                repeat_index=repeat_index,
                attempt_index=attempt_index,
                protocol_version=protocol_version,
                repo_up_revision=repo_up_revision,
                model_id=runner.model_id,
                model_revision="pinned_v0.1.0",
                prompt_sha256="0" * 64,
                context_sha256=evidence.context_sha256,
                applicability_status="NOT_APPLICABLE",
                applicability_reason=evidence.applicability_reason,
                generation_status="NOT_RUN",
                patch_status="NOT_APPLICABLE",
                security_status="NOT_APPLICABLE",
                functional_test_status="NOT_APPLICABLE",
                semantic_audit_status="NOT_APPLICABLE",
                input_tokens=0,
                output_tokens=0,
                model_calls=0,
                wall_seconds=round(elapsed, 4),
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
                notes=f"Arm not applicable: {evidence.applicability_reason}",
            )
            report = VerificationReport(
                security_status=VerificationStatus.NOT_APPLICABLE.value,
                functional_test_status=VerificationStatus.NOT_APPLICABLE.value,
                patch_status="NOT_APPLICABLE",
                notes=f"Arm not applicable: {evidence.applicability_reason}",
            )
            if output_records_path:
                append_run_record(rec, output_records_path)
            return rec, report

        # 3. Render Shared Prompt
        prompt_text, prompt_sha256 = render_repair_prompt(task, evidence)

        # 4. Generate Candidate Repair
        gen_result: GenerationResult = runner.generate(prompt_text, task, target_arm.value)

        # 5. Handle Patch Application
        if gen_result.generation_status == "SUCCESS":
            patch_res: PatchResult = parse_and_apply_patch(
                raw_output=gen_result.raw_output,
                repo_root=workspace.workspace_root,
                expected_target_file=task.target_file,
            )
        elif gen_result.generation_status == "ABSTAIN":
            patch_res = PatchResult(
                raw_output="ABSTAIN",
                patch_diff=None,
                patch_status="NOT_APPLICABLE",
                target_file=task.target_file,
                patch_sha256=None,
                error_message="Model abstained from proposing a patch.",
            )
        else:
            patch_res = PatchResult(
                raw_output=gen_result.raw_output,
                patch_diff=None,
                patch_status="NOT_RUN",
                target_file=task.target_file,
                patch_sha256=None,
                error_message=f"Generation failed: {gen_result.generation_status} ({gen_result.error_message})",
            )

        # 6. Verification
        verification_report: VerificationReport = run_verification(
            workspace=workspace,
            task=task,
            patch_result=patch_res,
            custom_security_runner=custom_security_runner,
            custom_functional_runner=custom_functional_runner,
        )

        elapsed = time.perf_counter() - start_time
        finished_at_utc = datetime.now(timezone.utc).isoformat()

        # 7. Construct and Validate Run Record
        rec = RunRecord(
            run_id=run_id,
            task_id=task.task_id,
            arm_id=target_arm.value,
            repeat_index=repeat_index,
            attempt_index=attempt_index,
            protocol_version=protocol_version,
            repo_up_revision=repo_up_revision,
            model_id=gen_result.model_id or runner.model_id,
            model_revision=gen_result.model_revision or "pinned_v0.1.0",
            inference_stack=gen_result.inference_stack,
            prompt_sha256=prompt_sha256,
            context_sha256=evidence.context_sha256,
            applicability_status="APPLICABLE",
            generation_status=gen_result.generation_status,
            patch_status=patch_res.patch_status,
            security_status=verification_report.security_status,
            functional_test_status=verification_report.functional_test_status,
            semantic_audit_status="PENDING",
            input_tokens=gen_result.input_tokens,
            output_tokens=gen_result.output_tokens,
            model_calls=gen_result.model_calls,
            wall_seconds=round(elapsed, 4),
            runtime_seconds=round(gen_result.wall_seconds, 4),
            started_at_utc=started_at_utc,
            finished_at_utc=finished_at_utc,
            patch_sha256=patch_res.patch_sha256,
            failure_category=patch_res.error_message or gen_result.error_message or None,
            notes=verification_report.notes or None,
        )

        if output_records_path:
            append_run_record(rec, output_records_path)

        return rec, verification_report
