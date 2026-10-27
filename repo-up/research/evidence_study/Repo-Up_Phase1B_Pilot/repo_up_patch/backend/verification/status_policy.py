"""Shared verification policy: unavailable checks must never count as a pass."""


def is_verified_pass(test_status: str, static_pass: bool, security_pass: bool) -> bool:
    """Return True only when all required checks explicitly pass."""
    return test_status == "PASS" and static_pass and security_pass
