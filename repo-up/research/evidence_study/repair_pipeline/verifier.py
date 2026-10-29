"""
repair_pipeline/verifier.py - Fail-safe verification engine and status evaluation.

Enforces Section 4 Critical Rules:
1. NOT_AVAILABLE, ERROR, TIMEOUT, and NOT_RUN must NEVER be treated as successful verification.
2. A passing security test does not prove general functional correctness.
3. A passing regression suite does not automatically prove that the intended vulnerability is fixed.
4. A patch that does not apply cleanly must not be reported as verified.
5. Missing tests must be recorded explicitly as NOT_AVAILABLE.
6. A model's assertion that its patch is correct is not verification evidence.

Independently records:
- security_status: PASS, FAIL, TIMEOUT, ERROR, NOT_AVAILABLE, NOT_APPLICABLE, NOT_RUN
- functional_test_status: PASS, FAIL, TIMEOUT, ERROR, NOT_AVAILABLE, NOT_APPLICABLE, NOT_RUN
- patch_status: APPLIED, APPLY_FAILED, REJECTED, etc.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from .execution_sandbox import IsolatedTaskWorkspace
from .patch_handler import PatchResult
from .task_loader import TaskMetadata


class VerificationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_RUN = "NOT_RUN"


NON_PASSING_STATUSES = {
    VerificationStatus.NOT_AVAILABLE,
    VerificationStatus.ERROR,
    VerificationStatus.TIMEOUT,
    VerificationStatus.NOT_RUN,
    VerificationStatus.FAIL,
    VerificationStatus.NOT_APPLICABLE,
}


@dataclass
class VerificationReport:
    """Comprehensive verification outcome separating security from regression."""

    security_status: str
    functional_test_status: str
    patch_status: str
    security_stdout: str = ""
    security_stderr: str = ""
    functional_stdout: str = ""
    functional_stderr: str = ""
    notes: str = ""

    @property
    def is_security_verified(self) -> bool:
        """Rule 1 & 4: Patch must be APPLIED and security validation must explicitly PASS."""
        if self.patch_status != "APPLIED":
            return False
        return self.security_status == VerificationStatus.PASS.value

    @property
    def is_functional_verified(self) -> bool:
        """Rule 1 & 4: Patch must be APPLIED and functional tests must explicitly PASS."""
        if self.patch_status != "APPLIED":
            return False
        return self.functional_test_status == VerificationStatus.PASS.value

    @property
    def is_strict_verified(self) -> bool:
        """Strict verified repair requires BOTH security and functional validation to PASS.
        
        Rule 2: Passing security test alone does not prove general functional correctness.
        Rule 3: Passing regression suite alone does not prove vulnerability is fixed.
        """
        return self.is_security_verified and self.is_functional_verified

    def to_dict(self) -> Dict[str, Any]:
        return {
            "security_status": self.security_status,
            "functional_test_status": self.functional_test_status,
            "patch_status": self.patch_status,
            "is_security_verified": self.is_security_verified,
            "is_functional_verified": self.is_functional_verified,
            "is_strict_verified": self.is_strict_verified,
            "notes": self.notes,
        }


def run_verification(
    workspace: IsolatedTaskWorkspace,
    task: TaskMetadata,
    patch_result: PatchResult,
    custom_security_runner: Optional[Callable[[Path], Tuple[int, str, str]]] = None,
    custom_functional_runner: Optional[Callable[[Path], Tuple[int, str, str]]] = None,
) -> VerificationReport:
    """Execute isolated verification and return a strictly categorized report.
    
    If the patch did not apply cleanly, verification is marked NOT_RUN per Rule 4.
    """
    # Rule 4: A patch that does not apply cleanly must not be reported as verified.
    if patch_result.patch_status != "APPLIED":
        return VerificationReport(
            security_status=VerificationStatus.NOT_RUN.value,
            functional_test_status=VerificationStatus.NOT_RUN.value,
            patch_status=patch_result.patch_status,
            notes=f"Verification not run: patch status is {patch_result.patch_status} ({patch_result.error_message})",
        )

    root = workspace.workspace_root
    if not root:
        return VerificationReport(
            security_status=VerificationStatus.ERROR.value,
            functional_test_status=VerificationStatus.ERROR.value,
            patch_status=patch_result.patch_status,
            notes="Workspace directory missing during verification.",
        )

    # 1. Run Security Validation
    sec_status = VerificationStatus.NOT_AVAILABLE.value
    sec_out, sec_err = "", ""

    if custom_security_runner:
        try:
            code, sec_out, sec_err = custom_security_runner(root)
            if code == 0:
                sec_status = VerificationStatus.PASS.value
            elif code == -1:
                sec_status = VerificationStatus.TIMEOUT.value
            elif code == -2:
                sec_status = VerificationStatus.ERROR.value
            else:
                sec_status = VerificationStatus.FAIL.value
        except Exception as e:
            sec_status = VerificationStatus.ERROR.value
            sec_err = f"Security runner exception: {e}"
    elif task.security_validator_available:
        # Check if local security check command exists
        # In a benchmark run, this delegates to the container runner;
        # on host or synthetic fixture, look for known test entry points
        test_file = root / "test_security.py"
        if test_file.is_file():
            code, sec_out, sec_err = workspace.run_command(["python", "-m", "pytest", "test_security.py"])
            if code == 0:
                sec_status = VerificationStatus.PASS.value
            elif code == -1:
                sec_status = VerificationStatus.TIMEOUT.value
            else:
                sec_status = VerificationStatus.FAIL.value
        else:
            sec_status = VerificationStatus.NOT_AVAILABLE.value
            sec_err = "Official security validator script not present in task directory."
    else:
        sec_status = VerificationStatus.NOT_AVAILABLE.value
        sec_err = "Task metadata marks security validator as unavailable."

    # 2. Run Functional / Regression Tests
    func_status = VerificationStatus.NOT_AVAILABLE.value
    func_out, func_err = "", ""

    if custom_functional_runner:
        try:
            code, func_out, func_err = custom_functional_runner(root)
            if code == 0:
                func_status = VerificationStatus.PASS.value
            elif code == -1:
                func_status = VerificationStatus.TIMEOUT.value
            elif code == -2:
                func_status = VerificationStatus.ERROR.value
            else:
                func_status = VerificationStatus.FAIL.value
        except Exception as e:
            func_status = VerificationStatus.ERROR.value
            func_err = f"Functional runner exception: {e}"
    elif task.functional_tests_available:
        test_dir = root / "tests"
        if test_dir.is_dir():
            code, func_out, func_err = workspace.run_command(["python", "-m", "pytest", "tests"])
            if code == 0:
                func_status = VerificationStatus.PASS.value
            elif code == -1:
                func_status = VerificationStatus.TIMEOUT.value
            else:
                func_status = VerificationStatus.FAIL.value
        else:
            func_status = VerificationStatus.NOT_AVAILABLE.value
            func_err = "Functional test directory not found."
    else:
        # Rule 5: Missing tests must be recorded explicitly.
        func_status = VerificationStatus.NOT_AVAILABLE.value
        func_err = "Official functional tests unavailable for this task."

    return VerificationReport(
        security_status=sec_status,
        functional_test_status=func_status,
        patch_status=patch_result.patch_status,
        security_stdout=sec_out,
        security_stderr=sec_err,
        functional_stdout=func_out,
        functional_stderr=func_err,
    )
