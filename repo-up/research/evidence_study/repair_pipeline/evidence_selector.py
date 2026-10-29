"""
repair_pipeline/evidence_selector.py - Controlled evidence selection for repair arms.

Implements the four agreed repair methods defined in Protocol v0.1.0:
- A0 (llm_minimal_context): CVE description, CWE, vulnerable function/region.
- A1 (llm_plus_ast_context): A0 + relevant imports, enclosing definitions, bounded AST statements.
- A2 (llm_plus_file_graph_context): A0 + file-level import dependency neighborhood.
- A3 (llm_plus_pre_patch_runtime_evidence): A0 + sanitized official pre-patch runtime summary.

Secondary/controlled arms:
- A4 (llm_plus_targeted_diagnostic_probes): A0 + bounded benchmark probe observations.
- A5 (bounded_iterative_repair_with_test_feedback): A0 + iterative sanitized test feedback.
- A6 (repo_up_deterministic_repair_only): Repo-Up rule-based deterministic repair.
- A7 (abstain_no_patch): Emits ABSTAIN, empty evidence.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .context_extractor import (
    ASTContext,
    GraphContext,
    RuntimeEvidence,
    extract_ast_context,
    extract_graph_context,
    extract_runtime_evidence,
)
from .task_loader import TaskMetadata


class ArmID(str, Enum):
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"
    A5 = "A5"
    A6 = "A6"
    A7 = "A7"


ARM_NAMES: Dict[ArmID, str] = {
    ArmID.A0: "llm_minimal_context",
    ArmID.A1: "llm_plus_ast_context",
    ArmID.A2: "llm_plus_file_graph_context",
    ArmID.A3: "llm_plus_pre_patch_runtime_evidence",
    ArmID.A4: "llm_plus_targeted_diagnostic_probes",
    ArmID.A5: "bounded_iterative_repair_with_test_feedback",
    ArmID.A6: "repo_up_deterministic_repair_only",
    ArmID.A7: "abstain_no_patch",
}


@dataclass
class SelectedEvidence:
    """The evidence selected for a specific arm attempt."""

    arm_id: ArmID
    arm_name: str
    evidence_block_text: str
    context_sha256: str
    applicability_status: str = "APPLICABLE"
    applicability_reason: str = ""
    ast_context: Optional[ASTContext] = None
    graph_context: Optional[GraphContext] = None
    runtime_evidence: Optional[RuntimeEvidence] = None
    extra_feedback: Optional[str] = None


def select_evidence_for_arm(
    arm_id: str | ArmID,
    task: TaskMetadata,
    repo_root: str | Path,
    runtime_output: Optional[str] = None,
    runtime_exit_code: int = 1,
    iteration_feedback: Optional[str] = None,
) -> SelectedEvidence:
    """Select and package evidence strictly according to the specified arm definition."""
    if isinstance(arm_id, str):
        try:
            arm_id = ArmID(arm_id.upper())
        except ValueError:
            raise ValueError(f"Unknown arm ID: {arm_id}. Valid arms: {[a.value for a in ArmID]}")

    arm_name = ARM_NAMES[arm_id]
    root = Path(repo_root)

    # Base minimal evidence block (A0 has no additional Repo-Up AST/Graph evidence)
    if arm_id == ArmID.A0:
        evidence_text = (
            "*(No additional AST, dependency-graph, or runtime evidence provided for this baseline arm.)*"
        )
        context_hash = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
        return SelectedEvidence(
            arm_id=arm_id,
            arm_name=arm_name,
            evidence_block_text=evidence_text,
            context_sha256=context_hash,
        )

    elif arm_id == ArmID.A1:
        # A1: A0 + relevant imports, enclosing definitions, bounded local AST context
        ast_ctx = extract_ast_context(root, task.target_file, task.target_line)
        evidence_text = ast_ctx.format_for_prompt()
        context_hash = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
        return SelectedEvidence(
            arm_id=arm_id,
            arm_name=arm_name,
            evidence_block_text=evidence_text,
            context_sha256=context_hash,
            ast_context=ast_ctx,
        )

    elif arm_id == ArmID.A2:
        # A2: A0 + relevant code selected from Repo-Up's file-level import/dependency graph
        graph_ctx = extract_graph_context(root, task.target_file)
        evidence_text = graph_ctx.format_for_prompt()
        context_hash = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
        return SelectedEvidence(
            arm_id=arm_id,
            arm_name=arm_name,
            evidence_block_text=evidence_text,
            context_sha256=context_hash,
            graph_context=graph_ctx,
        )

    elif arm_id == ArmID.A3:
        # A3: A0 + sanitized summary of output/status from the official vulnerable-state validator
        if runtime_output is None:
            # Check if pre-patch output is available
            evidence_text = (
                "*(Pre-patch runtime observation: Vulnerability reproduction check was not available for this run.)*"
            )
            context_hash = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
            return SelectedEvidence(
                arm_id=arm_id,
                arm_name=arm_name,
                evidence_block_text=evidence_text,
                context_sha256=context_hash,
                applicability_status="NOT_APPLICABLE",
                applicability_reason="Pre-patch runtime observation unavailable",
            )
        rt_ev = extract_runtime_evidence(runtime_exit_code, runtime_output)
        evidence_text = rt_ev.format_for_prompt()
        context_hash = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
        return SelectedEvidence(
            arm_id=arm_id,
            arm_name=arm_name,
            evidence_block_text=evidence_text,
            context_sha256=context_hash,
            runtime_evidence=rt_ev,
        )

    elif arm_id == ArmID.A4:
        # A4: Targeted diagnostic probes (predeclared safe probe)
        # If no probe available, mark NOT_APPLICABLE per protocol
        evidence_text = "*(Targeted diagnostic probe: No safe predeclared probe applicable.)*"
        context_hash = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
        return SelectedEvidence(
            arm_id=arm_id,
            arm_name=arm_name,
            evidence_block_text=evidence_text,
            context_sha256=context_hash,
            applicability_status="NOT_APPLICABLE",
            applicability_reason="No predeclared diagnostic probe applicable for this task",
        )

    elif arm_id == ArmID.A5:
        # A5: Bounded iterative repair with test feedback
        if iteration_feedback:
            evidence_text = (
                f"### Previous Attempt Feedback:\n"
                f"- Validation failed with status: `FAIL`\n"
                f"- Sanitized feedback summary: {iteration_feedback}"
            )
        else:
            evidence_text = "*(Initial attempt of iterative repair; no prior test feedback.)*"
        context_hash = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
        return SelectedEvidence(
            arm_id=arm_id,
            arm_name=arm_name,
            evidence_block_text=evidence_text,
            context_sha256=context_hash,
            extra_feedback=iteration_feedback,
        )

    elif arm_id == ArmID.A6:
        # A6: Repo-Up deterministic repair only
        evidence_text = "*(Deterministic repair execution via Repo-Up rule registry.)*"
        context_hash = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
        return SelectedEvidence(
            arm_id=arm_id,
            arm_name=arm_name,
            evidence_block_text=evidence_text,
            context_sha256=context_hash,
        )

    elif arm_id == ArmID.A7:
        # A7: Abstain / no patch
        evidence_text = "*(Abstention baseline: model must produce no patch.)*"
        context_hash = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
        return SelectedEvidence(
            arm_id=arm_id,
            arm_name=arm_name,
            evidence_block_text=evidence_text,
            context_sha256=context_hash,
        )

    raise ValueError(f"Unhandled arm ID: {arm_id}")
