"""
tests/test_repair_pipeline.py - Comprehensive unit tests for Repo-Up repair pipeline.

Labels: All fixtures used here are SYNTHETIC UNIT FIXTURES.
Synthetic fixture results must never be pooled into benchmark research metrics.
"""
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from research.evidence_study.repair_pipeline import (
    ArmID,
    GenerationResult,
    IsolatedTaskWorkspace,
    MockRepairRunner,
    PatchResult,
    PromptLeakageError,
    RunRecord,
    TaskMetadata,
    TaskValidationError,
    VerificationReport,
    VerificationStatus,
    append_run_record,
    execute_repair_run,
    extract_ast_context,
    extract_graph_context,
    extract_runtime_evidence,
    load_task_from_dict,
    parse_and_apply_patch,
    render_repair_prompt,
    run_verification,
    select_evidence_for_arm,
    validate_run_record,
)

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "run_record.schema.json"


@pytest.fixture
def synthetic_repo(tmp_path):
    """Creates a small synthetic vulnerable repository for testing."""
    repo_dir = tmp_path / "synthetic_vuln_repo"
    repo_dir.mkdir()

    # Create target vulnerable module
    vuln_code = (
        "import os\n"
        "import sys\n\n"
        "def query_database(user_input: str):\n"
        "    # Vulnerable SQL format\n"
        "    query = f'SELECT * FROM users WHERE name = {user_input}'\n"
        "    return query\n"
    )
    (repo_dir / "db_handler.py").write_text(vuln_code, encoding="utf-8")

    # Create dependent module
    dep_code = (
        "from db_handler import query_database\n\n"
        "def handle_login(name: str):\n"
        "    return query_database(name)\n"
    )
    (repo_dir / "auth.py").write_text(dep_code, encoding="utf-8")

    return repo_dir


@pytest.fixture
def synthetic_task():
    """Returns a valid synthetic TaskMetadata object."""
    return TaskMetadata(
        task_id="SYNTH-TASK-001",
        benchmark_case_id="case_001",
        language="Python",
        repository_url="https://github.com/synthetic/repo",
        cve_id="CVE-2026-0001",
        cwe_ids=["CWE-89"],
        cve_description="SQL injection vulnerability in query_database",
        target_file="db_handler.py",
        target_region="def query_database",
        target_line=4,
        vulnerable_revision="c0ffee1",
        _reference_patch="--- a/db_handler.py\n+++ b/db_handler.py\n@@ -4,2 +4,2 @@\n-    query = f'SELECT * FROM users WHERE name = {user_input}'\n+    query = 'SELECT * FROM users WHERE name = ?', (user_input,)\n",
    )


# ---------------------------------------------------------------------------
# 1. Task Loading and Metadata Validation Tests
# ---------------------------------------------------------------------------

def test_task_metadata_validation(synthetic_task):
    """Valid Python task passes validation; required fields enforced."""
    synthetic_task.validate()
    assert synthetic_task.task_id == "SYNTH-TASK-001"
    assert synthetic_task.language == "Python"

    # Non-Python task must be rejected
    with pytest.raises(TaskValidationError, match="Python tasks only"):
        invalid_task = load_task_from_dict({
            "task_id": "T2",
            "benchmark_case_id": "c2",
            "language": "Java",
            "repository_url": "https://github.com/repo",
            "target_file": "App.java",
        })

    # Missing target_file must be rejected
    with pytest.raises(TaskValidationError, match="target_file"):
        load_task_from_dict({
            "task_id": "T3",
            "benchmark_case_id": "c3",
            "language": "Python",
            "repository_url": "https://github.com/repo",
            "target_file": "",
        })


def test_reference_patch_sequestered(synthetic_task):
    """Official reference patch and hidden tests are strictly excluded from public task context."""
    public_ctx = synthetic_task.get_public_task_statement()
    assert "_reference_patch" not in public_ctx
    assert "reference_patch" not in public_ctx
    assert "_hidden_test_source" not in public_ctx


# ---------------------------------------------------------------------------
# 2. Context Extraction Tests (AST, Dependency Graph, Runtime)
# ---------------------------------------------------------------------------

def test_ast_context_extraction(synthetic_repo):
    """AST context extracts imports and bounded source lines with line numbers."""
    ast_ctx = extract_ast_context(synthetic_repo, "db_handler.py", target_line=5)
    assert "import os" in ast_ctx.imports or "import sys" in ast_ctx.imports
    assert ast_ctx.enclosing_definition is not None
    assert "query_database" in ast_ctx.enclosing_definition
    assert "SELECT * FROM users" in ast_ctx.bounded_snippet


def test_dependency_graph_context_extraction(synthetic_repo):
    """File dependency graph extracts dependents and dependencies without failing."""
    graph_ctx = extract_graph_context(synthetic_repo, "db_handler.py")
    assert graph_ctx.target_file == "db_handler.py"
    # Format contains clear disclaimer that this is file-level, not call-graph
    prompt_str = graph_ctx.format_for_prompt()
    assert "file-level import dependency graph" in prompt_str.lower()
    assert "not a function-level call" in prompt_str.lower()


def test_runtime_evidence_sanitization():
    """Runtime evidence masks absolute paths and exploit keywords."""
    raw = "Traceback at /home/user/secret/path/test.py line 12: eval('payload') failed"
    ev = extract_runtime_evidence(exit_code=1, raw_output=raw)
    assert ev.exit_code == 1
    assert "/home/user/secret" not in ev.sanitized_output
    assert "[SYSTEM_PATH]" in ev.sanitized_output or "test.py" in ev.sanitized_output


# ---------------------------------------------------------------------------
# 3. Evidence Selection Across Core Methods (A0, A1, A2, A3)
# ---------------------------------------------------------------------------

def test_evidence_selection_arms(synthetic_repo, synthetic_task):
    """Verifies that evidence blocks strictly vary according to method definitions."""
    # A0: Minimal baseline
    ev_a0 = select_evidence_for_arm("A0", synthetic_task, synthetic_repo)
    assert ev_a0.arm_id == ArmID.A0
    assert "no additional ast" in ev_a0.evidence_block_text.lower()
    assert ev_a0.context_sha256 is not None

    # A1: AST enriched
    ev_a1 = select_evidence_for_arm("A1", synthetic_task, synthetic_repo)
    assert ev_a1.arm_id == ArmID.A1
    assert "relevant imports" in ev_a1.evidence_block_text.lower()
    assert ev_a1.context_sha256 != ev_a0.context_sha256

    # A2: File Graph enriched
    ev_a2 = select_evidence_for_arm("A2", synthetic_task, synthetic_repo)
    assert ev_a2.arm_id == ArmID.A2
    assert "file-level import/dependency" in ev_a2.evidence_block_text.lower()

    # A3: Runtime observation
    ev_a3 = select_evidence_for_arm(
        "A3", synthetic_task, synthetic_repo, runtime_output="Vulnerability check failed with exit 1", runtime_exit_code=1
    )
    assert ev_a3.arm_id == ArmID.A3
    assert "pre-patch runtime observation" in ev_a3.evidence_block_text.lower()

    # A7: Abstain
    ev_a7 = select_evidence_for_arm("A7", synthetic_task, synthetic_repo)
    assert ev_a7.arm_id == ArmID.A7
    assert "abstention baseline" in ev_a7.evidence_block_text.lower()


# ---------------------------------------------------------------------------
# 4. Prompt Rendering and Anti-Leakage Protection
# ---------------------------------------------------------------------------

def test_prompt_rendering_and_leak_prevention(synthetic_repo, synthetic_task):
    """Ensures prompt is properly rendered and detects any leaked reference fix."""
    ev = select_evidence_for_arm("A0", synthetic_task, synthetic_repo)
    rendered, prompt_hash = render_repair_prompt(synthetic_task, ev)

    assert "CWE-89" in rendered
    assert "SQL injection vulnerability" in rendered
    assert "db_handler.py" in rendered
    assert len(prompt_hash) == 64

    # Simulate accidental leak of reference patch
    synthetic_task._reference_patch = "+++ b/db_handler.py\n+    query = 'SELECT * FROM users WHERE name = ?', (user_input,)\n"
    # Artificially inject the leaked line into the task description to test guardrail
    synthetic_task.cve_description = "Leaked: query = 'SELECT * FROM users WHERE name = ?', (user_input,)"
    with pytest.raises(PromptLeakageError, match="CRITICAL LEAKAGE"):
        render_repair_prompt(synthetic_task, ev)


# ---------------------------------------------------------------------------
# 5. Patch Handling, Parsing, and Path Security
# ---------------------------------------------------------------------------

def test_clean_patch_application(synthetic_repo):
    """Valid unified diff applies cleanly and returns APPLIED status."""
    diff = (
        "--- a/db_handler.py\n"
        "+++ b/db_handler.py\n"
        "@@ -5,2 +5,2 @@\n"
        "-    query = f'SELECT * FROM users WHERE name = {user_input}'\n"
        "+    query = 'SELECT * FROM users WHERE name = ?', (user_input,)\n"
    )
    res = parse_and_apply_patch(diff, synthetic_repo, "db_handler.py")
    assert res.patch_status == "APPLIED"
    assert res.patch_sha256 is not None
    # Confirm file was updated
    content = (synthetic_repo / "db_handler.py").read_text(encoding="utf-8")
    assert "SELECT * FROM users WHERE name = ?" in content


def test_path_traversal_rejection(synthetic_repo):
    """Patches attempting path traversal outside checkout are strictly REJECTED."""
    escape_diff = (
        "--- a/../../../../etc/passwd\n"
        "+++ b/../../../../etc/passwd\n"
        "@@ -1,1 +1,1 @@\n"
        "-root:x:0:0\n"
        "+malicious:x:0:0\n"
    )
    res = parse_and_apply_patch(escape_diff, synthetic_repo)
    assert res.patch_status == "REJECTED"
    assert "outside repository" in res.error_message


def test_malformed_diff_handling(synthetic_repo):
    """Malformed diffs with no valid hunks are categorized as MALFORMED."""
    bad_diff = "Just a casual explanation with no diff headers or hunks."
    res = parse_and_apply_patch(bad_diff, synthetic_repo, "db_handler.py")
    assert res.patch_status == "MALFORMED"


def test_apply_failed_on_mismatched_context(synthetic_repo):
    """Diffs that do not match file content result in APPLY_FAILED."""
    mismatched_diff = (
        "--- a/db_handler.py\n"
        "+++ b/db_handler.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-nonexistent code line that does not exist in file\n"
        "+replacement line\n"
    )
    res = parse_and_apply_patch(mismatched_diff, synthetic_repo, "db_handler.py")
    assert res.patch_status == "APPLY_FAILED"


def test_no_op_diff(synthetic_repo):
    """Diff that replaces text with identical text is classified as NO_OP."""
    no_op_diff = (
        "--- a/db_handler.py\n"
        "+++ b/db_handler.py\n"
        "@@ -1,2 +1,2 @@\n"
        " import os\n"
        " import sys\n"
    )
    res = parse_and_apply_patch(no_op_diff, synthetic_repo, "db_handler.py")
    assert res.patch_status == "NO_OP"


# ---------------------------------------------------------------------------
# 6. Sandbox Isolation and Clean State Separation
# ---------------------------------------------------------------------------

def test_workspace_isolation_and_no_cross_contamination(synthetic_repo):
    """Modifications inside an isolated workspace never affect the original repo."""
    orig_content = (synthetic_repo / "db_handler.py").read_text(encoding="utf-8")

    with IsolatedTaskWorkspace(synthetic_repo) as ws1:
        # Modify file inside ws1
        (ws1.workspace_root / "db_handler.py").write_text("MODIFIED_BY_ARM_A", encoding="utf-8")
        assert (ws1.workspace_root / "db_handler.py").read_text(encoding="utf-8") == "MODIFIED_BY_ARM_A"

    # Original repo remains clean and untouched
    assert (synthetic_repo / "db_handler.py").read_text(encoding="utf-8") == orig_content

    # Second isolated workspace is completely clean
    with IsolatedTaskWorkspace(synthetic_repo) as ws2:
        assert (ws2.workspace_root / "db_handler.py").read_text(encoding="utf-8") == orig_content


# ---------------------------------------------------------------------------
# 7. Fail-Safe Verification Critical Rules Tests
# ---------------------------------------------------------------------------

def test_critical_rules_non_passing_statuses(synthetic_task, synthetic_repo):
    """Rule 1: NOT_AVAILABLE, ERROR, TIMEOUT, and NOT_RUN must never be verified."""
    for bad_status in ["NOT_AVAILABLE", "ERROR", "TIMEOUT", "NOT_RUN", "FAIL"]:
        report = VerificationReport(
            security_status=bad_status,
            functional_test_status="PASS",
            patch_status="APPLIED",
        )
        assert report.is_security_verified is False, f"{bad_status} must not be security verified"
        assert report.is_strict_verified is False, f"{bad_status} must not be strictly verified"


def test_security_pass_does_not_prove_functional_correctness():
    """Rule 2: Passing security test alone does not prove general functional correctness."""
    report = VerificationReport(
        security_status="PASS",
        functional_test_status="NOT_AVAILABLE",
        patch_status="APPLIED",
    )
    assert report.is_security_verified is True
    assert report.is_functional_verified is False
    assert report.is_strict_verified is False  # Strict requires both!


def test_functional_pass_does_not_prove_security_fixed():
    """Rule 3: Passing regression suite alone does not prove vulnerability is fixed."""
    report = VerificationReport(
        security_status="FAIL",
        functional_test_status="PASS",
        patch_status="APPLIED",
    )
    assert report.is_security_verified is False
    assert report.is_functional_verified is True
    assert report.is_strict_verified is False


def test_unappliable_patch_is_never_verified(synthetic_task, synthetic_repo):
    """Rule 4: A patch that does not apply cleanly must never be reported as verified."""
    failed_patch = PatchResult(
        raw_output="bad",
        patch_diff=None,
        patch_status="APPLY_FAILED",
        target_file="db_handler.py",
        patch_sha256=None,
        error_message="Hunk failed",
    )
    with IsolatedTaskWorkspace(synthetic_repo) as ws:
        report = run_verification(ws, synthetic_task, failed_patch)
        assert report.patch_status == "APPLY_FAILED"
        assert report.security_status == "NOT_RUN"
        assert report.functional_test_status == "NOT_RUN"
        assert report.is_security_verified is False
        assert report.is_strict_verified is False


# ---------------------------------------------------------------------------
# 8. Result Schema Serialization and Draft 2020-12 Validation
# ---------------------------------------------------------------------------

def test_run_record_schema_validation():
    """RunRecord conforms strictly to schemas/run_record.schema.json."""
    record = RunRecord(
        run_id="run_001_A0_rep1_att1",
        task_id="SYNTH-TASK-001",
        arm_id="A0",
        repeat_index=1,
        attempt_index=1,
        protocol_version="0.1.0",
        repo_up_revision="abc1234",
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct",
        model_revision="pinned_v0.1.0",
        prompt_sha256="a" * 64,
        context_sha256="b" * 64,
        applicability_status="APPLICABLE",
        generation_status="SUCCESS",
        patch_status="APPLIED",
        security_status="PASS",
        functional_test_status="NOT_AVAILABLE",
        semantic_audit_status="PENDING",
        input_tokens=250,
        output_tokens=60,
        model_calls=1,
        wall_seconds=1.45,
        started_at_utc="2026-10-29T10:00:00Z",
        patch_sha256="c" * 64,
    )

    rec_dict = record.to_dict()
    validate_run_record(rec_dict)  # Will raise if schema invalid

    # Test appending to file
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        tmp_jsonl = f.name

    try:
        append_run_record(record, tmp_jsonl)
        with open(tmp_jsonl, "r", encoding="utf-8") as rf:
            lines = rf.readlines()
        assert len(lines) == 1
        loaded = json.loads(lines[0])
        assert loaded["run_id"] == "run_001_A0_rep1_att1"
        assert loaded["security_status"] == "PASS"
    finally:
        if os.path.exists(tmp_jsonl):
            os.remove(tmp_jsonl)


# ---------------------------------------------------------------------------
# 9. End-to-End Pipeline Run (All 4 Core Arms)
# ---------------------------------------------------------------------------

def test_end_to_end_repair_pipeline_core_arms(synthetic_repo, synthetic_task, tmp_path):
    """Executes full end-to-end pipeline across A0, A1, A2, A3 with mock runner and custom verifier."""
    output_jsonl = tmp_path / "results_test.jsonl"

    # Define mock verifier that passes only when safe replacement is in place
    def mock_security_checker(workspace_root: Path):
        code = (workspace_root / "db_handler.py").read_text(encoding="utf-8")
        if "SELECT * FROM users WHERE name = ?" in code:
            return 0, "Security check PASS: SQL injection resolved.", ""
        return 1, "Security check FAIL: SQL injection still present.", ""

    # Safe patch generator
    mock_runner = MockRepairRunner(
        default_response=(
            "--- a/db_handler.py\n"
            "+++ b/db_handler.py\n"
            "@@ -5,2 +5,2 @@\n"
            "-    query = f'SELECT * FROM users WHERE name = {user_input}'\n"
            "+    query = 'SELECT * FROM users WHERE name = ?', (user_input,)\n"
        )
    )

    core_arms = ["A0", "A1", "A2", "A3"]
    records = []

    for arm in core_arms:
        rec, report = execute_repair_run(
            task=synthetic_task,
            arm_id=arm,
            source_repo_root=synthetic_repo,
            model_runner=mock_runner,
            custom_security_runner=mock_security_checker,
            runtime_check_output="Simulated pre-patch failure: syntax error near user_input",
            runtime_check_exit_code=1,
            output_records_path=output_jsonl,
        )
        records.append(rec)
        assert rec.arm_id == arm
        assert rec.generation_status == "SUCCESS"
        assert rec.patch_status == "APPLIED"
        assert rec.security_status == "PASS"
        assert report.is_security_verified is True
        assert len(rec.prompt_sha256) == 64
        assert len(rec.context_sha256) == 64

    # Verify all records were appended and validated against Draft 2020-12 schema
    with open(output_jsonl, "r", encoding="utf-8") as f:
        saved_lines = f.readlines()
    assert len(saved_lines) == 4
    for line in saved_lines:
        parsed = json.loads(line)
        Draft202012Validator(json.load(SCHEMA_PATH.open())).validate(parsed)
