"""
repair_pipeline/patch_handler.py - Patch parsing, validation, application, and status classification.

Classifies patches strictly according to the schema:
- EMPTY: No patch content returned.
- MALFORMED: Syntax/format corrupt, invalid diff structure.
- NO_OP: Patch introduces no semantic or textual difference.
- REJECTED: Modifies unauthorized paths or attempts path traversal outside checkout.
- APPLY_FAILED: Patch could not apply cleanly to target file.
- APPLIED: Patch applies cleanly to the intended checkout.
- NOT_APPLICABLE: Arm was not applicable or abstained.
- NOT_RUN: Patch stage not executed.

Never normalizes or silently repairs malformed model output.
"""
from __future__ import annotations

import difflib
import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


@dataclass
class PatchResult:
    """Outcome of patch extraction, validation, and application."""

    raw_output: str
    patch_diff: Optional[str]
    patch_status: str  # One of: EMPTY, MALFORMED, NO_OP, REJECTED, APPLY_FAILED, APPLIED, NOT_APPLICABLE, NOT_RUN
    target_file: Optional[str]
    patch_sha256: Optional[str]
    error_message: str = ""


def extract_unified_diff(raw_text: str) -> Optional[str]:
    """Extract unified diff from model response, stripping markdown code fences if present."""
    if not raw_text or not raw_text.strip():
        return None

    cleaned = raw_text.strip()
    if cleaned == "ABSTAIN":
        return None

    # Check for markdown code fences (```diff ... ``` or ``` ...)
    fence_pattern = re.compile(r"```(?:diff)?\s*\n(.*?)\n```", re.DOTALL)
    matches = fence_pattern.findall(cleaned)
    if matches:
        # Use the first code block that looks like a diff or patch
        for m in matches:
            if "@@" in m or ("---" in m and "+++" in m) or m.startswith("+") or m.startswith("-"):
                return m.strip()
        return matches[0].strip()

    # Look for raw unified diff headers
    if "--- " in cleaned and "+++ " in cleaned:
        start_idx = cleaned.find("--- ")
        return cleaned[start_idx:].strip()

    if "@@" in cleaned:
        start_idx = cleaned.find("@@")
        return cleaned[start_idx:].strip()

    # If it is lines with + or -, could be a diff fragment
    lines = cleaned.splitlines()
    if any(l.startswith("+") or l.startswith("-") for l in lines):
        return cleaned

    return cleaned


def parse_and_apply_patch(
    raw_output: str,
    repo_root: str | Path,
    expected_target_file: Optional[str] = None,
) -> PatchResult:
    """Parse candidate patch from model output and apply it safely inside repo_root.
    
    Guarantees:
    - Path traversal attempts outside repo_root are REJECTED.
    - Malformed diffs are classified as MALFORMED.
    - Clean application produces APPLIED.
    """
    root = Path(repo_root).resolve()

    if not raw_output or not raw_output.strip():
        return PatchResult(
            raw_output="",
            patch_diff=None,
            patch_status="EMPTY",
            target_file=None,
            patch_sha256=None,
            error_message="Raw model output was empty.",
        )

    if raw_output.strip() == "ABSTAIN":
        return PatchResult(
            raw_output=raw_output,
            patch_diff=None,
            patch_status="NOT_APPLICABLE",
            target_file=None,
            patch_sha256=None,
            error_message="Model returned explicit ABSTAIN.",
        )

    extracted_diff = extract_unified_diff(raw_output)
    if not extracted_diff:
        return PatchResult(
            raw_output=raw_output,
            patch_diff=None,
            patch_status="EMPTY",
            target_file=None,
            patch_sha256=None,
            error_message="No diff could be extracted from model output.",
        )

    patch_hash = hashlib.sha256(extracted_diff.encode("utf-8")).hexdigest()

    # Identify target file from diff header or expected_target_file
    target_rel_path = None
    lines = extracted_diff.splitlines()

    for line in lines:
        if line.startswith("--- a/") or line.startswith("--- "):
            p = line[4:].strip()
            if p.startswith("a/"):
                p = p[2:]
            if p != "/dev/null":
                target_rel_path = p
        elif line.startswith("+++ b/") or line.startswith("+++ "):
            p = line[4:].strip()
            if p.startswith("b/"):
                p = p[2:]
            if p != "/dev/null":
                target_rel_path = p
                break

    if not target_rel_path and expected_target_file:
        target_rel_path = expected_target_file

    if not target_rel_path:
        return PatchResult(
            raw_output=raw_output,
            patch_diff=extracted_diff,
            patch_status="MALFORMED",
            target_file=None,
            patch_sha256=patch_hash,
            error_message="Could not determine target file from diff headers.",
        )

    # 1. Path Escape Guard: Check that target file resolves strictly inside root
    target_rel_clean = target_rel_path.replace("\\", "/").lstrip("/")
    resolved_target = (root / target_rel_clean).resolve()

    try:
        resolved_target.relative_to(root)
    except ValueError:
        return PatchResult(
            raw_output=raw_output,
            patch_diff=extracted_diff,
            patch_status="REJECTED",
            target_file=target_rel_clean,
            patch_sha256=patch_hash,
            error_message=f"Path traversal rejected: '{target_rel_path}' resolves outside repository checkout.",
        )

    if not resolved_target.is_file():
        return PatchResult(
            raw_output=raw_output,
            patch_diff=extracted_diff,
            patch_status="APPLY_FAILED",
            target_file=target_rel_clean,
            patch_sha256=patch_hash,
            error_message=f"Target file does not exist in repository: {target_rel_clean}",
        )

    # 2. Try applying the patch to the target file
    original_text = resolved_target.read_text(encoding="utf-8", errors="replace")
    original_lines = original_text.splitlines(keepends=True)

    applied_text, apply_err = _apply_unified_diff(original_lines, extracted_diff)
    if apply_err:
        return PatchResult(
            raw_output=raw_output,
            patch_diff=extracted_diff,
            patch_status=apply_err[0],  # "MALFORMED" or "APPLY_FAILED"
            target_file=target_rel_clean,
            patch_sha256=patch_hash,
            error_message=apply_err[1],
        )

    # 3. Check for NO_OP
    if applied_text == original_text:
        return PatchResult(
            raw_output=raw_output,
            patch_diff=extracted_diff,
            patch_status="NO_OP",
            target_file=target_rel_clean,
            patch_sha256=patch_hash,
            error_message="Patch produced no textual changes to target file.",
        )

    # 4. Write new source into checkout
    try:
        resolved_target.write_text(applied_text, encoding="utf-8")
    except Exception as e:
        return PatchResult(
            raw_output=raw_output,
            patch_diff=extracted_diff,
            patch_status="APPLY_FAILED",
            target_file=target_rel_clean,
            patch_sha256=patch_hash,
            error_message=f"Failed writing patched content: {e}",
        )

    return PatchResult(
        raw_output=raw_output,
        patch_diff=extracted_diff,
        patch_status="APPLIED",
        target_file=target_rel_clean,
        patch_sha256=patch_hash,
    )


def _apply_unified_diff(original_lines: list[str], diff_text: str) -> Tuple[Optional[str], Optional[Tuple[str, str]]]:
    """Applies a unified diff hunk by hunk to original lines.
    
    Returns:
        (new_text, None) on success
        (None, (status_code, error_message)) on failure
    """
    diff_lines = diff_text.splitlines(keepends=False)
    hunk_pattern = re.compile(r"^@@\s*-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s*@@")

    hunks = []
    current_hunk = None

    for line in diff_lines:
        match = hunk_pattern.match(line)
        if match:
            if current_hunk:
                hunks.append(current_hunk)
            orig_start = int(match.group(1))
            orig_len = int(match.group(2)) if match.group(2) else 1
            new_start = int(match.group(3))
            new_len = int(match.group(4)) if match.group(4) else 1
            current_hunk = {
                "orig_start": orig_start,
                "orig_len": orig_len,
                "new_start": new_start,
                "new_len": new_len,
                "lines": [],
            }
        elif current_hunk:
            current_hunk["lines"].append(line)

    if current_hunk:
        hunks.append(current_hunk)

    if not hunks:
        # If no standard @@ hunks found, attempt simple replacement if old/new blocks can be inferred
        return None, ("MALFORMED", "No valid unified diff hunks (@@ ... @@) found.")

    # Apply hunks sequentially from bottom to top so line shifts don't disrupt earlier hunks
    hunks.sort(key=lambda h: h["orig_start"], reverse=True)
    working_lines = list(original_lines)

    for h in hunks:
        orig_start = h["orig_start"]
        expected_old = []
        replacement_new = []

        for hl in h["lines"]:
            if hl.startswith("-"):
                expected_old.append(hl[1:])
            elif hl.startswith("+"):
                replacement_new.append(hl[1:])
            elif hl.startswith(" "):
                expected_old.append(hl[1:])
                replacement_new.append(hl[1:])

        # Locate the match region in working_lines near orig_start (1-indexed)
        target_idx = max(0, orig_start - 1)
        # Verify match with tolerance
        matched_idx = None
        # Check exact position first
        if _matches_at(working_lines, target_idx, expected_old):
            matched_idx = target_idx
        else:
            # Search within a +/- 10 line window
            for offset in range(1, 15):
                if target_idx - offset >= 0 and _matches_at(working_lines, target_idx - offset, expected_old):
                    matched_idx = target_idx - offset
                    break
                if target_idx + offset < len(working_lines) and _matches_at(working_lines, target_idx + offset, expected_old):
                    matched_idx = target_idx + offset
                    break

        if matched_idx is None:
            return None, ("APPLY_FAILED", f"Hunk at line {orig_start} failed to match file context.")

        # Replace matching lines
        rep_with_newlines = [l if l.endswith("\n") else l + "\n" for l in replacement_new]
        working_lines[matched_idx : matched_idx + len(expected_old)] = rep_with_newlines

    return "".join(working_lines), None


def _matches_at(file_lines: list[str], start_idx: int, pattern_lines: list[str]) -> bool:
    """Check if pattern_lines match file_lines starting at start_idx."""
    if start_idx + len(pattern_lines) > len(file_lines):
        return False
    for i, pl in enumerate(pattern_lines):
        fl = file_lines[start_idx + i].rstrip("\r\n")
        if fl != pl.rstrip("\r\n"):
            return False
    return True
