"""
repair_pipeline/context_extractor.py - AST and dependency graph context extraction.

Integrates with Repo-Up's parsing and dependency graph infrastructure:
- AST context: imports, enclosing class/function definitions, bounded local statements.
- Dependency graph: file-level import/dependency graph using services.graph_service.
  Protocol rule: Clearly distinguish file-level dependencies from function-level call graphs.
- Pre-patch runtime evidence: sanitized summary of vulnerable-state check output.
"""
from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ASTContext:
    """Bounded AST context extracted from the vulnerable file."""

    file: str
    target_line: Optional[int]
    imports: List[str] = field(default_factory=list)
    enclosing_definition: Optional[str] = None
    local_statements: List[str] = field(default_factory=list)
    bounded_snippet: str = ""

    def format_for_prompt(self) -> str:
        parts: List[str] = []
        if self.imports:
            parts.append("### Relevant Imports in Target File:\n```python\n" + "\n".join(self.imports) + "\n```")
        if self.enclosing_definition:
            parts.append(f"### Enclosing Definition:\n{self.enclosing_definition}")
        if self.bounded_snippet:
            parts.append(f"### Surrounding Code Region:\n```python\n{self.bounded_snippet}\n```")
        return "\n\n".join(parts) if parts else "No local AST context extracted."


@dataclass
class GraphContext:
    """File-level import/dependency graph context."""

    target_file: str
    dependencies: List[str] = field(default_factory=list)  # Files imported by target_file
    dependents: List[str] = field(default_factory=list)    # Files importing target_file
    neighbor_excerpts: Dict[str, str] = field(default_factory=dict)

    def format_for_prompt(self) -> str:
        lines: List[str] = [
            "### File-Level Import/Dependency Graph Context:",
            "*(Note: Derived from Repo-Up's static file-level import dependency graph, "
            "not a function-level call/data-flow graph.)*",
            "",
            f"**Target file:** `{self.target_file}`",
        ]
        if self.dependencies:
            lines.append(f"- **Direct Dependencies (imported by target):** {', '.join(f'`{f}`' for f in self.dependencies)}")
        else:
            lines.append("- **Direct Dependencies:** None identified.")

        if self.dependents:
            lines.append(f"- **Direct Dependents (files importing target):** {', '.join(f'`{f}`' for f in self.dependents)}")
        else:
            lines.append("- **Direct Dependents:** None identified.")

        if self.neighbor_excerpts:
            lines.append("\n**Selected Dependency Excerpts:**")
            for fpath, excerpt in self.neighbor_excerpts.items():
                lines.append(f"#### Excerpt from `{fpath}`:\n```python\n{excerpt}\n```")

        return "\n".join(lines)


@dataclass
class RuntimeEvidence:
    """Sanitized summary of official vulnerable-state validation output."""

    exit_code: int
    summary: str
    sanitized_output: str

    def format_for_prompt(self) -> str:
        return (
            "### Pre-Patch Runtime Observation:\n"
            f"- Validator exit code: `{self.exit_code}` (Vulnerability Reproduced)\n"
            f"- Status summary: {self.summary}\n"
            f"```text\n{self.sanitized_output}\n```"
        )


def extract_ast_context(
    repo_root: str | Path,
    target_file: str,
    target_line: Optional[int] = None,
    max_context_lines: int = 30,
) -> ASTContext:
    """Extract AST-informed context from the target file."""
    root = Path(repo_root)
    file_path = root / target_file

    if not file_path.is_file():
        return ASTContext(file=target_file, target_line=target_line, bounded_snippet="Target file not found in checkout.")

    try:
        source_text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return ASTContext(file=target_file, target_line=target_line, bounded_snippet=f"Failed to read file: {e}")

    lines = source_text.splitlines()
    total_lines = len(lines)

    imports: List[str] = []
    enclosing_def: Optional[str] = None
    bounded_snippet = ""

    # 1. Parse using Python AST
    try:
        tree = ast.parse(source_text, filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                names = ", ".join(a.name for a in node.names)
                imports.append(f"from {mod} import {names}")

        # If target_line is specified, locate enclosing class/function
        if target_line is not None and 1 <= target_line <= total_lines:
            candidate_def = None
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    start = getattr(node, "lineno", None)
                    end = getattr(node, "end_lineno", None)
                    if start is not None and end is not None:
                        if start <= target_line <= end:
                            kind = "Class" if isinstance(node, ast.ClassDef) else "Function"
                            candidate_def = f"`{kind} {node.name}` (lines {start}-{end})"
            enclosing_def = candidate_def

    except Exception:
        # Fallback regex import extraction if AST parse fails on partial Python
        for line in lines:
            trimmed = line.strip()
            if trimmed.startswith("import ") or trimmed.startswith("from "):
                imports.append(trimmed)

    # 2. Extract bounded snippet around target_line or target region
    if target_line is not None and 1 <= target_line <= total_lines:
        half_window = max_context_lines // 2
        start_idx = max(0, target_line - 1 - half_window)
        end_idx = min(total_lines, target_line - 1 + half_window)
        numbered_lines = [
            f"{i + 1:4d}: {lines[i]}" for i in range(start_idx, end_idx)
        ]
        bounded_snippet = "\n".join(numbered_lines)
    else:
        # First N lines if target_line is unspecified
        end_idx = min(total_lines, max_context_lines)
        numbered_lines = [f"{i + 1:4d}: {lines[i]}" for i in range(end_idx)]
        bounded_snippet = "\n".join(numbered_lines)

    return ASTContext(
        file=target_file,
        target_line=target_line,
        imports=imports[:15],  # bounded to top 15 relevant imports
        enclosing_definition=enclosing_def,
        bounded_snippet=bounded_snippet,
    )


def extract_graph_context(
    repo_root: str | Path,
    target_file: str,
    max_neighbor_lines: int = 25,
) -> GraphContext:
    """Extract file-level import dependency graph context using Repo-Up graph_service."""
    root = str(Path(repo_root).resolve())
    norm_target = target_file.replace("\\", "/").lstrip("/")

    dependencies: List[str] = []
    dependents: List[str] = []
    neighbor_excerpts: Dict[str, str] = {}

    try:
        from services.graph_service import build_dependency_graph
        graph = build_dependency_graph(root)

        # Match target_file in graph nodes (normalizing paths)
        matched_node = None
        for node in graph.nodes:
            norm_node = node.replace("\\", "/").lstrip("/")
            if norm_node == norm_target or norm_node.endswith("/" + norm_target):
                matched_node = node
                break

        if matched_node:
            # Out-edges: files imported by target
            for succ in graph.successors(matched_node):
                clean_succ = succ.replace("\\", "/")
                dependencies.append(clean_succ)

            # In-edges: files importing target
            for pred in graph.predecessors(matched_node):
                clean_pred = pred.replace("\\", "/")
                dependents.append(clean_pred)

            # Extract bounded excerpt from the top dependency if available
            all_neighbors = (dependencies + dependents)[:2]
            for n_path in all_neighbors:
                abs_n = os.path.join(root, n_path)
                if os.path.isfile(abs_n):
                    try:
                        with open(abs_n, "r", encoding="utf-8", errors="replace") as nf:
                            n_lines = nf.readlines()[:max_neighbor_lines]
                        neighbor_excerpts[n_path] = "".join(n_lines)
                    except Exception:
                        pass

    except Exception:
        # If graph service fails or networkx graph is empty, return empty neighbor list safely
        pass

    return GraphContext(
        target_file=norm_target,
        dependencies=dependencies[:10],
        dependents=dependents[:10],
        neighbor_excerpts=neighbor_excerpts,
    )


def sanitize_runtime_output(raw_output: str, max_lines: int = 20) -> str:
    """Sanitize runtime output to avoid disclosing hidden evaluator tests or exploits."""
    if not raw_output:
        return "[No output produced]"

    # Mask potential token/secret/path leaks
    text = re.sub(r'(/home/[^\s:]+|C:\\[^\s:]+)', '[SYSTEM_PATH]', raw_output)
    # Mask raw exploit payloads if identified
    text = re.sub(r'(?i)(eval\(|exec\(|<script.*?>|UNION\s+SELECT)', '[REDACTED_PAYLOAD]', text)

    lines = text.strip().splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... [truncated {len(lines) - max_lines} lines]"]
    return "\n".join(lines)


def extract_runtime_evidence(exit_code: int, raw_output: str) -> RuntimeEvidence:
    """Construct sanitized pre-patch runtime evidence."""
    sanitized = sanitize_runtime_output(raw_output)
    summary = (
        "Official pre-patch security check failed as expected, confirming vulnerable behavior."
        if exit_code != 0
        else "Check exited with 0 (warning: vulnerable state check inconclusive)."
    )
    return RuntimeEvidence(
        exit_code=exit_code,
        summary=summary,
        sanitized_output=sanitized,
    )
