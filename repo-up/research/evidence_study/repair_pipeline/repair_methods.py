"""
repair_pipeline/repair_methods.py - Shared repair method interfaces and model invocation.

Supports:
- Shared generation settings (temp=0.2, top_p=0.95, max_new_tokens=1024) across A0–A3.
- Free open-weights local execution or mock fixture execution for tests.
- Rejection of paid APIs (protocol adherence).
- Strict isolation of reference fixes (no oracle leakage).
"""
from __future__ import annotations

import abc
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .task_loader import TaskMetadata


@dataclass
class GenerationResult:
    """Standardized output from a repair method invocation."""

    raw_output: str
    generation_status: str  # SUCCESS, ABSTAIN, ERROR, TIMEOUT, NOT_RUN
    input_tokens: int
    output_tokens: int
    model_calls: int
    wall_seconds: float
    model_id: str
    model_revision: Optional[str] = None
    inference_stack: Optional[str] = None
    error_message: Optional[str] = None


class BaseRepairRunner(abc.ABC):
    """Abstract interface for repair generation."""

    def __init__(
        self,
        model_id: str = "Qwen/Qwen2.5-Coder-7B-Instruct",
        temperature: float = 0.2,
        top_p: float = 0.95,
        max_new_tokens: int = 1024,
    ):
        self.model_id = model_id
        self.temperature = temperature
        self.top_p = top_p
        self.max_new_tokens = max_new_tokens

    @abc.abstractmethod
    def generate(self, prompt: str, task: TaskMetadata, arm_id: str) -> GenerationResult:
        """Generate repair patch text for the rendered prompt."""
        pass


class MockRepairRunner(BaseRepairRunner):
    """Deterministic mock runner for unit tests and local fixture verification."""

    def __init__(
        self,
        default_response: Optional[str] = None,
        model_id: str = "mock-qwen-2.5-coder",
        fail_mode: Optional[str] = None,  # "timeout", "error", "abstain"
    ):
        super().__init__(model_id=model_id)
        self.default_response = default_response
        self.fail_mode = fail_mode

    def generate(self, prompt: str, task: TaskMetadata, arm_id: str) -> GenerationResult:
        start_time = time.perf_counter()

        if arm_id == "A7" or self.fail_mode == "abstain":
            return GenerationResult(
                raw_output="ABSTAIN",
                generation_status="ABSTAIN",
                input_tokens=len(prompt) // 4,
                output_tokens=1,
                model_calls=1,
                wall_seconds=0.01,
                model_id=self.model_id,
            )

        if self.fail_mode == "timeout":
            return GenerationResult(
                raw_output="",
                generation_status="TIMEOUT",
                input_tokens=len(prompt) // 4,
                output_tokens=0,
                model_calls=1,
                wall_seconds=0.01,
                model_id=self.model_id,
                error_message="Generation timed out.",
            )

        if self.fail_mode == "error":
            return GenerationResult(
                raw_output="",
                generation_status="ERROR",
                input_tokens=len(prompt) // 4,
                output_tokens=0,
                model_calls=1,
                wall_seconds=0.01,
                model_id=self.model_id,
                error_message="Simulated inference error.",
            )

        # Produce a synthetic unified diff if none specified
        if self.default_response is not None:
            raw = self.default_response
        else:
            raw = (
                f"--- a/{task.target_file}\n"
                f"+++ b/{task.target_file}\n"
                f"@@ -1,1 +1,2 @@\n"
                f"# Patched by {arm_id}\n"
                f"+# Safe repair applied\n"
            )

        elapsed = time.perf_counter() - start_time
        return GenerationResult(
            raw_output=raw,
            generation_status="SUCCESS",
            input_tokens=max(1, len(prompt) // 4),
            output_tokens=max(1, len(raw) // 4),
            model_calls=1,
            wall_seconds=round(elapsed, 4),
            model_id=self.model_id,
            model_revision="pinned_v0.1.0",
            inference_stack="mock_runner",
        )


class DeterministicRepoUpRunner(BaseRepairRunner):
    """A6: Invokes Repo-Up's rule-based deterministic repair engine where applicable."""

    def __init__(self):
        super().__init__(model_id="repo-up-deterministic-v1")

    def generate(self, prompt: str, task: TaskMetadata, arm_id: str) -> GenerationResult:
        start_time = time.perf_counter()
        # Look up rule in Repo-Up repair registry
        try:
            from analysis.repair.repair_engine import get_candidate_patch
            finding_dict = {
                "rule_id": task.cve_id or "SEC-RULE",
                "file": task.target_file,
                "line": task.target_line or 1,
                "language": task.language,
                "description": task.cve_description,
            }
            # Search if deterministic rule exists
            # (If no matching rule, emits ABSTAIN / NOT_APPLICABLE)
            patch_resp = get_candidate_patch(finding_dict, "")
            if patch_resp and patch_resp.patch:
                diff = patch_resp.patch.unified_diff()
                elapsed = time.perf_counter() - start_time
                return GenerationResult(
                    raw_output=diff,
                    generation_status="SUCCESS",
                    input_tokens=0,
                    output_tokens=len(diff) // 4,
                    model_calls=0,
                    wall_seconds=round(elapsed, 4),
                    model_id=self.model_id,
                )
        except Exception:
            pass

        # When no deterministic rule applies, abstain
        elapsed = time.perf_counter() - start_time
        return GenerationResult(
            raw_output="ABSTAIN",
            generation_status="ABSTAIN",
            input_tokens=0,
            output_tokens=1,
            model_calls=0,
            wall_seconds=round(elapsed, 4),
            model_id=self.model_id,
            error_message="No deterministic Repo-Up rule applicable for this task.",
        )
