"""
repair_pipeline/prompt_renderer.py - Shared prompt construction and leak prevention.

Renders `prompts/repair_prompt.md` ensuring byte-identical instructions across all arms.
Only the `[EVIDENCE_BLOCK]` varies between A0–A4 (plus feedback for A5).

Critical Guardrails:
- NEVER passes official reference patch, fixed function, or hidden test source.
- Validates that no ground truth leaks into the rendered prompt.
- Computes SHA-256 hash of the rendered prompt for the run record.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from .evidence_selector import SelectedEvidence
from .task_loader import TaskMetadata

DEFAULT_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "repair_prompt.md"


class PromptLeakageError(Exception):
    """Raised if ground-truth reference fix or test contents appear in the rendered prompt."""


def render_repair_prompt(
    task: TaskMetadata,
    evidence: SelectedEvidence,
    template_path: Optional[Path | str] = None,
) -> tuple[str, str]:
    """Render the shared repair prompt for a task and evidence selection.
    
    Returns:
        tuple[rendered_prompt, prompt_sha256]
    """
    path = Path(template_path) if template_path else DEFAULT_PROMPT_PATH
    if not path.is_file():
        raise FileNotFoundError(f"Repair prompt template not found at: {path}")

    template_raw = path.read_text(encoding="utf-8")
    # The actual instruction starts after the markdown metadata divider '---'
    if "---" in template_raw:
        # Split and take the prompt body
        sections = template_raw.split("---", 2)
        if len(sections) >= 3:
            prompt_template = sections[1].strip()
        else:
            prompt_template = template_raw
    else:
        prompt_template = template_raw

    # Prepare public task fields
    cve_desc = task.cve_description.strip() or "No vulnerability description provided."
    cwe_str = ", ".join(task.cwe_ids) if task.cwe_ids else "N/A"
    target_region = task.target_region.strip() or f"Function in {task.target_file}"
    target_file = task.target_file.strip()
    evidence_block = evidence.evidence_block_text.strip()

    # Fill fields
    rendered = prompt_template.replace("[CVE_DESCRIPTION]", cve_desc)
    rendered = rendered.replace("[CWE]", cwe_str)
    rendered = rendered.replace("[TARGET_REGION]", target_region)
    rendered = rendered.replace("[TARGET_FILE]", target_file)
    rendered = rendered.replace("[EVIDENCE_BLOCK]", evidence_block)

    # Leakage check: Ensure reference patch is not present
    if task._reference_patch and len(task._reference_patch.strip()) > 15:
        # Check if the reference patch text leaked into the prompt
        ref_lines = [
            l.strip()
            for l in task._reference_patch.splitlines()
            if l.startswith("+") and len(l.strip()) > 10 and not l.startswith("+++")
        ]
        for ref_line in ref_lines:
            if ref_line[1:].strip() in rendered:
                raise PromptLeakageError(
                    f"CRITICAL LEAKAGE: Ground-truth reference patch line '{ref_line}' detected in prompt!"
                )

    if task._hidden_test_source and len(task._hidden_test_source.strip()) > 15:
        hidden_lines = [
            l.strip()
            for l in task._hidden_test_source.splitlines()
            if len(l.strip()) > 15 and "def test_" in l
        ]
        for h_line in hidden_lines:
            if h_line in rendered:
                raise PromptLeakageError(
                    f"CRITICAL LEAKAGE: Hidden test source line '{h_line}' detected in prompt!"
                )

    prompt_sha256 = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    return rendered, prompt_sha256
