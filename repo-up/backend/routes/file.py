"""
routes/file.py — serves individual source file content for the CodeViewer.

Security
--------
* session_id is validated as a UUID before being used in any path.
* The resolved file path must be inside the session directory
  (commonpath check — guards against ../traversal).
* Files are read with errors="replace" so binary or non-UTF-8 content
  returns a placeholder rather than a 500.
* Content is capped to avoid enormous responses.
"""

import os
import re
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter()

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

TEMP_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp")

# Maximum bytes returned to the browser (~1 MB is plenty for a code viewer).
MAX_RESPONSE_BYTES: int = 1 * 1024 * 1024


@router.get("/file-content")
async def get_file_content(session_id: str, path: str) -> dict:
    """Return the raw text content of *path* within *session_id*.

    Raises structured errors for all failure modes.
    """
    # --- Validate session_id -------------------------------------------------
    if not session_id or not _UUID_RE.match(session_id):
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_PATH",
                    "message": "Invalid session identifier.",
                }
            },
        )

    session_dir = Path(os.path.join(TEMP_DIR, session_id)).resolve()

    if not session_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": "Session has expired or does not exist. Please re-analyse the project.",
                }
            },
        )

    # --- Validate file path --------------------------------------------------
    if not path:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_PATH",
                    "message": "No file path supplied.",
                }
            },
        )

    try:
        file_path = (session_dir / path).resolve()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_PATH",
                    "message": "Invalid file path.",
                }
            },
        )

    # Containment check: file_path must be inside session_dir
    try:
        file_path.relative_to(session_dir)
    except ValueError:
        logging.warning(
            "Path traversal attempt: session=%s path=%r", session_id, path
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_PATH",
                    "message": "Access to that path is not permitted.",
                }
            },
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "FILE_NOT_FOUND",
                    "message": "File not found in this session.",
                }
            },
        )

    # --- Read file -----------------------------------------------------------
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read(MAX_RESPONSE_BYTES)

        # If the file is larger than the cap, add a truncation notice.
        actual_size = file_path.stat().st_size
        if actual_size > MAX_RESPONSE_BYTES:
            content += "\n\n[… file truncated — showing first 1 MB …]"

        return {"content": content}
    except Exception:
        logging.exception("Error reading file session=%s path=%r", session_id, path)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "ANALYSIS_FAILED",
                    "message": "Could not read file content.",
                }
            },
        )
