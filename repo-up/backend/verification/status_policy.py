"""
verification/status_policy.py - Shared verification policy.

Enforces protocol rule: unavailable checks, timeouts, errors, or un-run checks
must NEVER count as a passing verification.
"""
from typing import Optional


def is_verified_pass(test_status: str, static_pass: bool, security_pass: bool) -> bool:
    """Return True only when all required checks explicitly pass.
    
    Critical rules:
    - NOT_AVAILABLE, ERROR, TIMEOUT, and NOT_RUN must never be treated as successful verification.
    - Both static and security checks must pass.
    """
    if test_status != "PASS":
        return False
    return bool(static_pass and security_pass)


def is_security_pass(security_status: str) -> bool:
    """Check if security validation explicitly passed."""
    return security_status == "PASS"


def is_functional_pass(functional_status: str) -> bool:
    """Check if functional/regression tests explicitly passed."""
    return functional_status == "PASS"
