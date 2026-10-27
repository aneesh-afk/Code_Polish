from verification.status_policy import is_verified_pass


def test_only_explicit_runtime_pass_can_verify():
    assert is_verified_pass("PASS", True, True) is True
    assert is_verified_pass("NOT_AVAILABLE", True, True) is False
    assert is_verified_pass("FAIL", True, True) is False
    assert is_verified_pass("TIMEOUT", True, True) is False


def test_static_or_security_failure_prevents_verification():
    assert is_verified_pass("PASS", False, True) is False
    assert is_verified_pass("PASS", True, False) is False
