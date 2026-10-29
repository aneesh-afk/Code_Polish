"""
repair_pipeline - Repo-Up repair pipeline and evidence selection framework.

Supports controlled, reproducible comparison of vulnerability-repair methods
under Protocol v0.1.0:
- A0: llm_minimal_context
- A1: llm_plus_ast_context
- A2: llm_plus_file_graph_context
- A3: llm_plus_pre_patch_runtime_evidence
"""

from .task_loader import TaskMetadata, TaskValidationError, load_task_from_dict, load_tasks_from_manifest
from .context_extractor import (
    ASTContext,
    GraphContext,
    RuntimeEvidence,
    extract_ast_context,
    extract_graph_context,
    extract_runtime_evidence,
)
from .evidence_selector import ArmID, ARM_NAMES, SelectedEvidence, select_evidence_for_arm
from .prompt_renderer import render_repair_prompt, PromptLeakageError
from .patch_handler import PatchResult, parse_and_apply_patch, extract_unified_diff
from .execution_sandbox import IsolatedTaskWorkspace
from .verifier import VerificationReport, VerificationStatus, run_verification
from .repair_methods import BaseRepairRunner, MockRepairRunner, DeterministicRepoUpRunner, GenerationResult
from .result_recorder import RunRecord, append_run_record, validate_run_record
from .pipeline import execute_repair_run

__version__ = "0.1.0"

__all__ = [
    "TaskMetadata",
    "TaskValidationError",
    "load_task_from_dict",
    "load_tasks_from_manifest",
    "ASTContext",
    "GraphContext",
    "RuntimeEvidence",
    "extract_ast_context",
    "extract_graph_context",
    "extract_runtime_evidence",
    "ArmID",
    "ARM_NAMES",
    "SelectedEvidence",
    "select_evidence_for_arm",
    "render_repair_prompt",
    "PromptLeakageError",
    "PatchResult",
    "parse_and_apply_patch",
    "extract_unified_diff",
    "IsolatedTaskWorkspace",
    "VerificationReport",
    "VerificationStatus",
    "run_verification",
    "BaseRepairRunner",
    "MockRepairRunner",
    "DeterministicRepoUpRunner",
    "GenerationResult",
    "RunRecord",
    "append_run_record",
    "validate_run_record",
    "execute_repair_run",
]
