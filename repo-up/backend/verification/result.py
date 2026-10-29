"""
verification/result.py - Structured results from patch verification.
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


class VerificationStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    FAIL_STATIC = "FAIL_STATIC"
    FAIL_SECURITY = "FAIL_SECURITY"
    FAIL_PARSE = "FAIL_PARSE"
    FAIL_TEST = "FAIL_TEST"
    TIMEOUT = "TIMEOUT"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    NOT_RUN = "NOT_RUN"
    ERROR = "ERROR"


@dataclass
class VerificationResult:
    status: VerificationStatus
    parse_result: bool
    static_result: Optional[bool] = None
    security_result: Optional[bool] = None
    test_result: Optional[bool] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_verified(self) -> bool:
        """Only an explicit PASS is verified.
        
        Critical Rule: NOT_AVAILABLE, ERROR, TIMEOUT, and NOT_RUN must never
        be treated as successful verification.
        """
        return self.status == VerificationStatus.PASS

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "is_verified": self.is_verified,
            "parse_result": self.parse_result,
            "static_result": self.static_result,
            "security_result": self.security_result,
            "test_result": self.test_result,
            "message": self.message,
            "details": self.details,
        }
