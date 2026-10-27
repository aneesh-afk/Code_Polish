"""Phase 1A: Benchmark metadata inventory generator.

Reads official benchmark metadata (e.g. PatchEval-Verified) and generates:
- metadata_inventory.json (overall dataset summary and language breakdown)
- python_candidates.csv (deterministic inventory of Python candidate cases)
- metadata_issues.jsonl (detailed logging of any schema/validation anomalies)

STRICT SECURITY & PROTOCOL GUARDRAILS:
- Never exports reference patches or fix_func contents.
- Never treats missing information as valid.
- Operates deterministically without network calls or Docker operations.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from urllib.parse import urlparse
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


IMAGE_URL_PATTERN = re.compile(r"^[a-zA-Z0-9._\-/]+:[a-zA-Z0-9._\-]+$")


def validate_cve_id(cve_id: Any) -> Tuple[bool, Optional[str]]:
    if not isinstance(cve_id, str) or not cve_id.strip():
        return False, "CVE ID is missing or not a string"
    if not re.match(r"^CVE-\d{4}-\d{4,}$", cve_id.strip(), re.IGNORECASE):
        return False, f"CVE ID '{cve_id}' has non-standard format"
    return True, None


def validate_image_url(image_url: Any) -> Tuple[bool, Optional[str]]:
    if not isinstance(image_url, str) or not image_url.strip():
        return False, "Docker image URL is missing or empty"
    if not IMAGE_URL_PATTERN.match(image_url.strip()):
        return False, f"Docker image URL '{image_url}' does not match expected name:tag syntax"
    return True, None


def validate_repo_url(repo_url: Any) -> Tuple[bool, Optional[str]]:
    """Validate that a repository reference is an absolute HTTP(S) URL."""
    if not isinstance(repo_url, str) or not repo_url.strip():
        return False, "Repository URL is missing or empty"
    parsed = urlparse(repo_url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False, f"Repository reference '{repo_url}' is not an absolute HTTP(S) URL"
    return True, None


def extract_cwe_ids(cwe_info: Any) -> List[str]:
    """Extract list of sorted CWE IDs from dictionary or list."""
    if isinstance(cwe_info, dict):
        return sorted([str(k).strip() for k in cwe_info.keys() if str(k).strip()])
    if isinstance(cwe_info, list):
        cwes = []
        for item in cwe_info:
            if isinstance(item, str):
                cwes.append(item.strip())
            elif isinstance(item, dict):
                cwes.extend([str(k).strip() for k in item.keys() if str(k).strip()])
        return sorted(list(set(cwes)))
    return []


def audit_metadata(
    raw_data: Any,
    source_path: str,
    source_commit: str = "unknown",
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Audit parsed metadata and return (inventory, python_candidates, issues)."""
    issues: List[Dict[str, Any]] = []
    
    if not isinstance(raw_data, list):
        issue = {
            "record_index": None,
            "cve_id": None,
            "field": None,
            "issue_type": "INVALID_ROOT_CONTAINER",
            "message": f"Expected JSON array at root, got {type(raw_data).__name__}",
        }
        issues.append(issue)
        inventory = {
            "source_path": source_path,
            "source_commit": source_commit,
            "total_records": 0,
            "valid_records": 0,
            "language_counts": {},
            "python_candidates_count": 0,
            "duplicate_cve_ids": [],
            "issues_count": len(issues),
        }
        return inventory, [], issues

    total_records = len(raw_data)
    language_counter: Counter[str] = Counter()
    cve_seen: Dict[str, List[int]] = {}
    python_candidates: List[Dict[str, Any]] = []

    for idx, record in enumerate(raw_data):
        if not isinstance(record, dict):
            issues.append({
                "record_index": idx,
                "cve_id": None,
                "field": None,
                "issue_type": "MALFORMED_RECORD",
                "message": f"Record at index {idx} is not an object",
            })
            continue

        raw_cve = record.get("cve_id")
        cve_str = str(raw_cve).strip() if raw_cve is not None else ""
        cve_valid, cve_err = validate_cve_id(cve_str)
        if not cve_valid:
            issues.append({
                "record_index": idx,
                "cve_id": cve_str or None,
                "field": "cve_id",
                "issue_type": "INVALID_CVE_ID",
                "message": cve_err,
            })
        else:
            cve_seen.setdefault(cve_str, []).append(idx)

        # Track language
        raw_lang = record.get("programming_language")
        lang_str = str(raw_lang).strip() if raw_lang is not None else ""
        if not lang_str:
            issues.append({
                "record_index": idx,
                "cve_id": cve_str or None,
                "field": "programming_language",
                "issue_type": "MISSING_LANGUAGE",
                "message": "programming_language field is missing or empty",
            })
            norm_lang = "Unknown"
        else:
            norm_lang = lang_str.title() if lang_str.lower() in ("python", "javascript", "go") else lang_str
        language_counter[norm_lang] += 1

        # Check required fields
        cve_desc = record.get("cve_description")
        has_desc = bool(cve_desc and isinstance(cve_desc, str) and cve_desc.strip())
        if not has_desc:
            issues.append({
                "record_index": idx,
                "cve_id": cve_str or None,
                "field": "cve_description",
                "issue_type": "MISSING_DESCRIPTION",
                "message": "cve_description is empty or missing",
            })

        cwe_info = record.get("cwe_info")
        cwe_list = extract_cwe_ids(cwe_info)
        has_cwe = len(cwe_list) > 0
        if not has_cwe:
            issues.append({
                "record_index": idx,
                "cve_id": cve_str or None,
                "field": "cwe_info",
                "issue_type": "MISSING_CWE",
                "message": "cwe_info is empty, missing, or has no valid CWE keys",
            })

        repo_url = record.get("repo")
        repo_valid, repo_err = validate_repo_url(repo_url)
        has_repo = repo_valid
        if not repo_valid:
            issues.append({
                "record_index": idx,
                "cve_id": cve_str or None,
                "field": "repo",
                "issue_type": "INVALID_REPO_URL",
                "message": repo_err,
            })

        vul_func = record.get("vul_func")
        has_vul_func = bool(vul_func and isinstance(vul_func, list) and len(vul_func) > 0)
        vul_func_count = len(vul_func) if isinstance(vul_func, list) else 0
        if not has_vul_func:
            issues.append({
                "record_index": idx,
                "cve_id": cve_str or None,
                "field": "vul_func",
                "issue_type": "MISSING_VUL_FUNC",
                "message": "vul_func list is empty or missing",
            })

        # Check reference patch and fix_func metadata presence (WITHOUT saving their code contents)
        patch_url = record.get("patch_url")
        has_patch_url = bool(patch_url and ((isinstance(patch_url, list) and len(patch_url) > 0) or (isinstance(patch_url, str) and patch_url.strip())))

        fix_func = record.get("fix_func")
        has_fix_func_meta = bool(fix_func and isinstance(fix_func, list) and len(fix_func) > 0)
        fix_func_count = len(fix_func) if isinstance(fix_func, list) else 0

        image_url = record.get("image_url")
        img_valid, img_err = validate_image_url(image_url)
        if not img_valid:
            issues.append({
                "record_index": idx,
                "cve_id": cve_str or None,
                "field": "image_url",
                "issue_type": "INVALID_IMAGE_URL",
                "message": img_err,
            })

        # If language is Python, create candidate metadata entry
        if lang_str.lower() == "python":
            candidate = {
                "cve_id": cve_str,
                "programming_language": "Python",
                "repo": str(repo_url).strip() if repo_url else "",
                "image_url": str(image_url).strip() if image_url else "",
                "cwe_ids": ";".join(cwe_list),
                "has_description": has_desc,
                "vul_func_count": vul_func_count,
                "has_patch_url": has_patch_url,
                "has_fix_func_metadata": has_fix_func_meta,
                "fix_func_count": fix_func_count,
                "image_url_valid": img_valid,
                "metadata_complete": (cve_valid and has_desc and has_cwe and has_repo and has_vul_func and has_patch_url and has_fix_func_meta and img_valid),
            }
            python_candidates.append(candidate)

    # Detect duplicates
    duplicate_cve_ids = sorted([cve for cve, indices in cve_seen.items() if len(indices) > 1])
    for dup_cve in duplicate_cve_ids:
        indices = cve_seen[dup_cve]
        issues.append({
            "record_index": indices[0],
            "cve_id": dup_cve,
            "field": "cve_id",
            "issue_type": "DUPLICATE_CVE_ID",
            "message": f"Duplicate CVE ID found at indices {indices}",
        })

    # Sort python candidates deterministically by cve_id
    python_candidates.sort(key=lambda x: x["cve_id"])

    inventory = {
        "source_path": source_path,
        "source_commit": source_commit,
        "total_records": total_records,
        "language_counts": dict(sorted(language_counter.items())),
        "python_candidates_count": len(python_candidates),
        "python_distinct_repositories": len(set(c["repo"] for c in python_candidates if c["repo"])),
        "duplicate_cve_count": len(duplicate_cve_ids),
        "duplicate_cve_ids": duplicate_cve_ids,
        "issues_count": len(issues),
    }

    return inventory, python_candidates, issues


def run_inventory(
    input_file: Path,
    output_dir: Path,
    source_commit: str = "unknown",
) -> Tuple[Dict[str, Any], int, int]:
    """Process metadata file and write Phase 1A inventory artifacts."""
    # Parse before creating or changing output files. Malformed JSON must not
    # produce a partial inventory that could be mistaken for a successful run.
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid JSON metadata input '{input_file}': {exc}") from exc

    output_dir.mkdir(parents=True, exist_ok=True)

    inventory, candidates, issues = audit_metadata(
        raw_data,
        source_path=str(input_file),
        source_commit=source_commit,
    )

    # 1. metadata_inventory.json
    inventory_path = output_dir / "metadata_inventory.json"
    with open(inventory_path, "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2, sort_keys=True)

    # 2. python_candidates.csv
    csv_path = output_dir / "python_candidates.csv"
    csv_fields = [
        "cve_id",
        "programming_language",
        "repo",
        "image_url",
        "cwe_ids",
        "has_description",
        "vul_func_count",
        "has_patch_url",
        "has_fix_func_metadata",
        "fix_func_count",
        "image_url_valid",
        "metadata_complete",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for cand in candidates:
            writer.writerow(cand)

    # 3. metadata_issues.jsonl
    issues_path = output_dir / "metadata_issues.jsonl"
    with open(issues_path, "w", encoding="utf-8") as f:
        for issue in issues:
            f.write(json.dumps(issue, sort_keys=True) + "\n")

    return inventory, len(candidates), len(issues)


def main():
    parser = argparse.ArgumentParser(description="Generate Phase 1A metadata inventory")
    parser.add_argument("--input", required=True, type=Path, help="Path to patcheval_verified.json")
    parser.add_argument("--output-dir", required=True, type=Path, help="Output directory for inventory files")
    parser.add_argument("--commit", default="unknown", help="Source repository commit hash")
    args = parser.parse_args()

    inventory, cand_count, issue_count = run_inventory(
        input_file=args.input,
        output_dir=args.output_dir,
        source_commit=args.commit,
    )
    print(f"Phase 1A Inventory Complete:")
    print(f"  Total records: {inventory['total_records']}")
    print(f"  Languages: {inventory['language_counts']}")
    print(f"  Python candidates: {cand_count}")
    print(f"  Distinct Python repos: {inventory['python_distinct_repositories']}")
    print(f"  Issues recorded: {issue_count}")


if __name__ == "__main__":
    main()
