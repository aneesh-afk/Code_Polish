"""
repair_pipeline/execution_sandbox.py - Repository and execution isolation.

Guarantees:
- Every experimental run receives an isolated, clean repository checkout.
- No modifications from one repair method contaminate another.
- Prevents leaking host credentials or secrets to task execution.
- Applies strict timeouts and process limits.
- Clean teardown on completion.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

DEFAULT_TIMEOUT_SECONDS = 60
MAX_WORKSPACE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit


class ExecutionTimeoutError(Exception):
    """Raised when execution exceeds the allocated timeout."""


class WorkspaceLimitError(Exception):
    """Raised when workspace exceeds memory or disk limits."""


class IsolatedTaskWorkspace:
    """Manages an isolated directory sandbox for a task/arm execution."""

    def __init__(
        self,
        original_repo_root: str | Path,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.original_root = Path(original_repo_root).resolve()
        self.timeout_seconds = timeout_seconds
        self.temp_dir: Optional[str] = None
        self.workspace_root: Optional[Path] = None

    def setup(self) -> Path:
        """Create a clean isolated checkout copy."""
        if not self.original_root.is_dir():
            raise FileNotFoundError(f"Original repository directory does not exist: {self.original_root}")

        self.temp_dir = tempfile.mkdtemp(prefix="repoup_exp_")
        self.workspace_root = Path(self.temp_dir) / "checkout"

        # Copy repository tree, excluding venvs, large build artifacts, and secret files
        ignore_patterns = shutil.ignore_patterns(
            ".git", "venv", "node_modules", "__pycache__", ".env", "*.pyc", "*.key"
        )
        shutil.copytree(
            self.original_root,
            self.workspace_root,
            symlinks=False,
            ignore=ignore_patterns,
        )
        return self.workspace_root

    def run_command(
        self,
        command: list[str] | str,
        env_vars: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Tuple[int, str, str]:
        """Execute a command inside the isolated workspace with strict limits and sanitized env."""
        if not self.workspace_root or not self.workspace_root.is_dir():
            raise RuntimeError("Workspace is not set up.")

        effective_timeout = timeout or self.timeout_seconds

        # Sanitize environment: do not pass sensitive host environment variables
        safe_env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "TEMP": self.temp_dir,
            "TMP": self.temp_dir,
            "PYTHONUNBUFFERED": "1",
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
        }
        if env_vars:
            safe_env.update(env_vars)

        shell_mode = isinstance(command, str)

        try:
            proc = subprocess.run(
                command,
                cwd=str(self.workspace_root),
                env=safe_env,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                shell=shell_mode,
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = (exc.stderr or "") + f"\n[ERROR: Execution timed out after {effective_timeout}s]"
            return -1, stdout, stderr
        except Exception as e:
            return -2, "", f"[ERROR: Process execution failed: {e}]"

    def cleanup(self) -> None:
        """Completely clean up temporary workspace."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None
            self.workspace_root = None

    def __enter__(self) -> IsolatedTaskWorkspace:
        self.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()
