"""
routes/tree.py — returns the project file tree for a given session.

Security
--------
* session_id is validated as a UUID before use in any path.
* The resolved directory must be inside TEMP_DIR only.
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


@router.get("/tree")
async def get_project_tree(session_id: str) -> dict:
    """Return the file tree for *session_id*.

    Previously accepted an arbitrary filesystem path — now locked to session dirs only.
    """
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
    temp_base = Path(TEMP_DIR).resolve()

    # Containment check
    try:
        session_dir.relative_to(temp_base)
    except ValueError:
        logging.warning("Tree path traversal attempt: session_id=%r", session_id)
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_PATH",
                    "message": "Access to that path is not permitted.",
                }
            },
        )

    if not session_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": "Session has expired or does not exist.",
                }
            },
        )

    from services.tree_service import generate_project_tree

    return {"tree": generate_project_tree(str(session_dir))}
