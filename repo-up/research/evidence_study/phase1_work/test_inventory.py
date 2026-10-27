"""Automated test suite for Phase 1A metadata inventory."""

import json
import tempfile
import hashlib
from pathlib import Path

import pytest

from research.evidence_study.phase1_work.inventory_metadata import (
    audit_metadata,
    run_inventory,
    validate_cve_id,
    validate_image_url,
    validate_repo_url,
)


def test_validate_cve_id():
    valid, err = validate_cve_id("CVE-2021-1234")
    assert valid is True
    assert err is None

    valid, err = validate_cve_id("CVE-2020-123456")
    assert valid is True

    valid, err = validate_cve_id("INVALID-123")
    assert valid is False
    assert "non-standard format" in err

    valid, err = validate_cve_id("")
    assert valid is False


def test_validate_image_url():
    valid, err = validate_image_url("ghcr.io/patcheval-cve/patcheval-cve:cve-2020-26215")
    assert valid is True
    assert err is None

    valid, err = validate_image_url("invalid_no_tag")
    assert valid is False
    assert "does not match expected" in err

    valid, err = validate_image_url("")
    assert valid is False


def test_empty_input():
    inventory, candidates, issues = audit_metadata([], "test.json")
    assert inventory["total_records"] == 0
    assert inventory["python_candidates_count"] == 0
    assert candidates == []
    assert issues == []


def test_malformed_root():
    inventory, candidates, issues = audit_metadata({"not": "a list"}, "test.json")
    assert inventory["total_records"] == 0
    assert len(issues) == 1
    assert issues[0]["issue_type"] == "INVALID_ROOT_CONTAINER"


def test_duplicate_cve_detection():
    data = [
        {
            "cve_id": "CVE-2021-0001",
            "programming_language": "Python",
            "cve_description": "desc",
            "cwe_info": {"CWE-79": {}},
            "repo": "https://github.com/org/repo1",
            "image_url": "reg.io/img:tag1",
            "patch_url": ["url"],
            "vul_func": [{"snippet": "x"}],
            "fix_func": [{"snippet": "y"}],
        },
        {
            "cve_id": "CVE-2021-0001",
            "programming_language": "Python",
            "cve_description": "desc2",
            "cwe_info": {"CWE-79": {}},
            "repo": "https://github.com/org/repo2",
            "image_url": "reg.io/img:tag2",
            "patch_url": ["url"],
            "vul_func": [{"snippet": "x"}],
            "fix_func": [{"snippet": "y"}],
        },
    ]
    inventory, candidates, issues = audit_metadata(data, "test.json")
    assert inventory["duplicate_cve_count"] == 1
    assert inventory["duplicate_cve_ids"] == ["CVE-2021-0001"]
    dup_issues = [i for i in issues if i["issue_type"] == "DUPLICATE_CVE_ID"]
    assert len(dup_issues) == 1


def test_missing_fields_recording():
    data = [
        {
            "cve_id": "CVE-2021-0002",
            "programming_language": "Python",
            "cve_description": "",  # missing
            "cwe_info": {},  # missing
            "repo": None,  # missing
            "image_url": "bad_img",  # invalid
            "vul_func": [],  # missing
            "patch_url": [],
            "fix_func": [],
        }
    ]
    inventory, candidates, issues = audit_metadata(data, "test.json")
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand["metadata_complete"] is False
    assert cand["has_description"] is False
    assert cand["image_url_valid"] is False

    issue_types = {i["issue_type"] for i in issues}
    assert "MISSING_DESCRIPTION" in issue_types
    assert "MISSING_CWE" in issue_types
    assert "INVALID_REPO_URL" in issue_types
    assert "MISSING_VUL_FUNC" in issue_types
    assert "INVALID_IMAGE_URL" in issue_types


def test_mixed_language_capitalization():
    data = [
        {"cve_id": "CVE-2021-0003", "programming_language": "python", "repo": "r1"},
        {"cve_id": "CVE-2021-0004", "programming_language": "PYTHON", "repo": "r2"},
        {"cve_id": "CVE-2021-0005", "programming_language": "JavaScript", "repo": "r3"},
    ]
    inventory, candidates, issues = audit_metadata(data, "test.json")
    assert inventory["language_counts"]["Python"] == 2
    assert inventory["language_counts"]["Javascript"] == 1
    assert inventory["python_candidates_count"] == 2


def test_reference_patch_exclusion_guardrail():
    """Ensure candidate output NEVER exports fix_func or patch snippet code."""
    data = [
        {
            "cve_id": "CVE-2021-0006",
            "programming_language": "Python",
            "cve_description": "desc",
            "cwe_info": {"CWE-89": {}},
            "repo": "https://github.com/org/repo",
            "image_url": "reg.io/img:tag",
            "patch_url": ["https://commit"],
            "vul_func": [{"snippet": "vulnerable_code()"}],
            "fix_func": [{"snippet": "SECRET_FIX_DO_NOT_LEAK()"}],
        }
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_in = Path(tmpdir) / "input.json"
        tmp_out = Path(tmpdir) / "out"
        with open(tmp_in, "w") as f:
            json.dump(data, f)

        run_inventory(tmp_in, tmp_out)

        csv_content = (tmp_out / "python_candidates.csv").read_text(encoding="utf-8")
        assert "SECRET_FIX_DO_NOT_LEAK" not in csv_content
        assert "vulnerable_code" not in csv_content

        inv_content = (tmp_out / "metadata_inventory.json").read_text(encoding="utf-8")
        assert "SECRET_FIX_DO_NOT_LEAK" not in inv_content


def test_deterministic_output():
    data = [
        {"cve_id": "CVE-2021-0002", "programming_language": "Python"},
        {"cve_id": "CVE-2021-0001", "programming_language": "Python"},
    ]
    _, cands1, _ = audit_metadata(data, "test.json")
    _, cands2, _ = audit_metadata(list(reversed(data)), "test.json")
    assert [c["cve_id"] for c in cands1] == ["CVE-2021-0001", "CVE-2021-0002"]
    assert [c["cve_id"] for c in cands2] == ["CVE-2021-0001", "CVE-2021-0002"]


def test_validate_repo_url():
    assert validate_repo_url("https://github.com/org/repo")[0] is True
    assert validate_repo_url("http://github.com/org/repo")[0] is True
    assert validate_repo_url("github.com/org/repo")[0] is False
    assert validate_repo_url("file:///tmp/repo")[0] is False
    assert validate_repo_url("not a url")[0] is False
    assert validate_repo_url(None)[0] is False


def test_malformed_json_fails_without_creating_output(tmp_path):
    input_file = tmp_path / "broken.json"
    output_dir = tmp_path / "out"
    input_file.write_text('{"not valid":', encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON metadata input"):
        run_inventory(input_file, output_dir)
    assert not output_dir.exists()


def test_malformed_optional_cwe_is_reported():
    data = [{
        "cve_id": "CVE-2021-9911",
        "programming_language": "Python",
        "cve_description": "desc",
        "cwe_info": "not-an-object",
        "repo": "https://github.com/org/repo",
        "image_url": "ghcr.io/org/image:tag",
        "patch_url": ["https://github.com/org/repo/commit/abc"],
        "vul_func": [{"file_path": "x.py"}],
        "fix_func": [{"file_path": "x.py"}],
    }]
    inventory, candidates, issues = audit_metadata(data, "test.json")
    assert candidates[0]["metadata_complete"] is False
    assert any(i["issue_type"] == "MISSING_CWE" for i in issues)


def test_deterministic_generated_files(tmp_path):
    data = [
        {"cve_id": "CVE-2021-0002", "programming_language": "Python",
         "repo": "https://github.com/org/b", "cve_description": "desc",
         "cwe_info": {"CWE-79": {}}, "image_url": "ghcr.io/org/img:tag",
         "patch_url": ["https://github.com/org/b/commit/abc"],
         "vul_func": [{"file_path": "b.py"}], "fix_func": [{"file_path": "b.py"}]},
        {"cve_id": "CVE-2021-0001", "programming_language": "Python",
         "repo": "https://github.com/org/a", "cve_description": "desc",
         "cwe_info": {"CWE-89": {}}, "image_url": "ghcr.io/org/img:tag",
         "patch_url": ["https://github.com/org/a/commit/abc"],
         "vul_func": [{"file_path": "a.py"}], "fix_func": [{"file_path": "a.py"}]},
    ]
    source = tmp_path / "input.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    out1, out2 = tmp_path / "out1", tmp_path / "out2"
    run_inventory(source, out1, "abc123")
    run_inventory(source, out2, "abc123")
    for filename in ("metadata_inventory.json", "python_candidates.csv", "metadata_issues.jsonl"):
        assert (out1 / filename).read_bytes() == (out2 / filename).read_bytes()


def test_non_url_repository_is_reported():
    data = [{
        "cve_id": "CVE-2021-9912", "programming_language": "Python",
        "cve_description": "desc", "cwe_info": {"CWE-79": {}},
        "repo": "org/repo", "image_url": "ghcr.io/org/image:tag",
        "patch_url": ["url"], "vul_func": [{"file_path": "x.py"}],
        "fix_func": [{"file_path": "x.py"}],
    }]
    inventory, candidates, issues = audit_metadata(data, "test.json")
    assert candidates[0]["metadata_complete"] is False
    assert any(i["issue_type"] == "INVALID_REPO_URL" for i in issues)
