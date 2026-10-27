import asyncio
import json
import logging
import os
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.upload_service import SESSION_STORE
from analysis.finding import Finding
from analysis.repair.repair_engine import get_candidate_patch
from verification.sandbox import VerificationSandbox
from verification.runner import discover_and_run_tests
from analysis.rules.smells.smell_engine import run_smell_engine
from analysis.rules.security.security_engine import run_security_engine
from services.tree_service import generate_project_tree
from services.graph_service import build_dependency_graph, serialize_graph

router = APIRouter()
log = logging.getLogger(__name__)

class SandboxRunRequest(BaseModel):
    session_id: str
    findings: List[Dict[str, Any]]

async def stream_sandbox_run(session_id: str, findings: List[Dict[str, Any]]):
    session = SESSION_STORE.get(session_id)
    if not session:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Session not found or expired'})}\n\n"
        return

    project_root = session.get("project_path", "")
    if not project_root or not os.path.isdir(project_root):
        yield f"data: {json.dumps({'type': 'error', 'message': 'Project path missing'})}\n\n"
        return

    yield f"data: {json.dumps({'type': 'sandbox_created'})}\n\n"
    
    with VerificationSandbox(project_root) as sandbox:
        # Initial graph
        yield f"data: {json.dumps({'type': 'parse_started'})}\n\n"
        await asyncio.sleep(1.0)
        tree = generate_project_tree(sandbox.sandbox_root)
        graph = build_dependency_graph(sandbox.sandbox_root)
        graph_data = serialize_graph(graph)
        yield f"data: {json.dumps({'type': 'graph_updated', 'graph': graph_data})}\n\n"
        await asyncio.sleep(1.0)

        for idx, finding_dict in enumerate(findings):
            finding = Finding.from_dict(finding_dict)
            if not finding.autofix_available:
                continue

            yield f"data: {json.dumps({'type': 'fix_started', 'fix_idx': idx, 'finding': finding_dict})}\n\n"
            await asyncio.sleep(1.5)  # Simulate patch generation time

            response = get_candidate_patch(finding_dict, sandbox.sandbox_root)
            patch = response.patch

            if not patch:
                yield f"data: {json.dumps({'type': 'fix_blocked', 'fix_idx': idx, 'message': 'No patch generated'})}\n\n"
                continue

            # Backup file
            target_file = os.path.join(sandbox.sandbox_root, patch.file)
            backup_content = None
            if os.path.exists(target_file):
                with open(target_file, "r", encoding="utf-8") as f:
                    backup_content = f.read()

            try:
                # Patch Applied
                sandbox.apply_patch(patch)
                yield f"data: {json.dumps({'type': 'patch_applied', 'fix_idx': idx, 'patch': patch.to_dict()})}\n\n"
                await asyncio.sleep(1.0)

                # Parse & Graph Update
                yield f"data: {json.dumps({'type': 'parse_started', 'fix_idx': idx})}\n\n"
                tree = generate_project_tree(sandbox.sandbox_root)
                graph = build_dependency_graph(sandbox.sandbox_root)
                graph_data = serialize_graph(graph)
                yield f"data: {json.dumps({'type': 'parse_completed', 'fix_idx': idx})}\n\n"
                await asyncio.sleep(0.5)
                yield f"data: {json.dumps({'type': 'graph_updated', 'graph': graph_data})}\n\n"
                await asyncio.sleep(1.0)

                # Static Analysis
                yield f"data: {json.dumps({'type': 'analysis_started', 'fix_idx': idx})}\n\n"
                new_smells, _ = run_smell_engine(sandbox.sandbox_root)
                yield f"data: {json.dumps({'type': 'analysis_completed', 'fix_idx': idx})}\n\n"
                await asyncio.sleep(1.0)

                # Security Analysis
                yield f"data: {json.dumps({'type': 'security_check', 'fix_idx': idx})}\n\n"
                new_security, _ = run_security_engine(sandbox.sandbox_root)
                await asyncio.sleep(1.0)

                # Tests
                yield f"data: {json.dumps({'type': 'test_started', 'fix_idx': idx})}\n\n"
                test_status, test_out, test_err = discover_and_run_tests(sandbox.sandbox_root)
                await asyncio.sleep(1.5)
                yield f"data: {json.dumps({'type': 'test_completed', 'fix_idx': idx, 'test_status': test_status})}\n\n"
                await asyncio.sleep(1.0)

                # Verify finding is gone
                static_pass = True
                for s in new_smells:
                    if s.get("rule_id") == finding.rule_id and s.get("file") == finding.file:
                        if patch.start_line <= (s.get("line") or 0) <= patch.start_line + 5:
                            static_pass = False
                            break
                security_pass = True
                for s in new_security:
                    if s.get("rule_id") == finding.rule_id and s.get("file") == finding.file:
                        if patch.start_line <= (s.get("line") or 0) <= patch.start_line + 5:
                            security_pass = False
                            break
                            
                # Unavailable tests are not evidence of success. Only an explicit PASS
                # can satisfy the runtime-verification part of this workflow.
                test_pass = test_status == "PASS"
                pass_verification = is_verified_pass(test_status, static_pass, security_pass)

                if pass_verification:
                    yield f"data: {json.dumps({'type': 'fix_passed', 'fix_idx': idx})}\n\n"
                elif test_status == "NOT_AVAILABLE":
                    yield f"data: {json.dumps({'type': 'verification_incomplete', 'fix_idx': idx, 'message': 'Runtime tests unavailable; patch is not verified.'})}\n\n"
                    # Restore the original content so an unverified patch is not retained
                    # as if it had passed the verification workflow.
                    if backup_content is not None:
                        with open(target_file, "w", encoding="utf-8") as f:
                            f.write(backup_content)
                else:
                    msg = "Tests failed" if not test_pass else "Finding still present"
                    yield f"data: {json.dumps({'type': 'regression_detected', 'fix_idx': idx, 'message': msg})}\n\n"
                    # Rollback
                    if backup_content is not None:
                        with open(target_file, "w", encoding="utf-8") as f:
                            f.write(backup_content)
                    
            except Exception as e:
                log.exception("Error applying patch in sandbox")
                yield f"data: {json.dumps({'type': 'fix_failed', 'fix_idx': idx, 'message': str(e)})}\n\n"
                # Rollback
                if backup_content is not None:
                    with open(target_file, "w", encoding="utf-8") as f:
                        f.write(backup_content)

        yield f"data: {json.dumps({'type': 'sandbox_completed'})}\n\n"

@router.post("/sandbox/run")
async def request_sandbox_run(body: SandboxRunRequest):
    return StreamingResponse(
        stream_sandbox_run(body.session_id, body.findings),
        media_type="text/event-stream"
    )
