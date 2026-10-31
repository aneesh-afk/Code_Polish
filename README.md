# Repo-Up

**Repo-Up** is a web-based code quality analysis tool. Upload a ZIP of any codebase and get a
structured dashboard showing dependency relationships, CK-style software metrics, security findings,
and an ISO/IEC 25010-aligned readiness score — all streamed live to the browser.

---

## What is implemented

### Ingestion
- ZIP file upload (up to 50 MB compressed, 300 MB uncompressed)
- Zip-slip protection, symlink rejection, file-count and size limits
- Per-session scoped temp directories with 2-hour auto-cleanup

### Language support (via Tree-sitter AST parsing)
- **Python** (`.py`)
- **JavaScript** (`.js`, `.jsx`)
- **TypeScript** (`.ts`, `.tsx`)
- **Java** (`.java`)
- **C++** (`.cpp`, `.cc`, `.cxx`, `.hpp`, `.h`)

### Dependency graph
- File-level import resolution for all supported languages
- Directed graph built with NetworkX
- Live streaming of nodes/edges to the browser via SSE (Server-Sent Events)
- Interactive D3 force-directed graph explorer in the UI

### Analysis rules
| Rule | Severity |
|---|---|
| Missing README | High |
| No `src/` folder | Medium |
| No `tests/` folder | High |
| No dependency file (`requirements.txt` / `package.json`) | High |
| No `.env.example` | Medium |
| Committed `.env` file | High |
| Hardcoded secrets (AWS key pattern, generic API key/token regex) | High |
| `eval()` / `exec()` / `system()` usage | High |
| I/O or network import without any `try/catch` | Medium |
| Circular dependency (Tarjan's SCC) | High |
| High CBO — file with many in+out edges (≥ 5) | Medium |

### Metrics (CK-style proxies)
| Metric | What is actually measured |
|---|---|
| COF (Coupling Factor) | edges / (n² − n) over the file graph |
| Afferent Couplings (avg) | average in-degree per file |
| WMC proxy (avg public methods) | average public method count per class |
| Public fields (avg) | average public field count per class (JS/TS) |
| DIT (avg) | average depth of inheritance tree |
| LCOM proxy | average (methods − 1) per class |

Thresholds from: Ferreira et al. (2012), *Journal of Systems and Software* 85(2), 244-257.

### Auto-Fix Engine (Phase 5)
- Rule-based resolution engine providing candidate patches for supported findings.
- **Tier 1 (Deterministic Auto-Fix)**: Safely generates patches for `yaml.safe_load` and weak cryptographic hashes.
- **Tier 2/3 (Suggested/Explanation)**: Provides actionable guidance for unsafe deserialization, dangerous exec, missing exception handling, and unsafe asserts using LLM generation.
- Strict 5-step patch validation: path escape protection, line bounds checking, exact old-text matching, non-empty result guard, and Tree-sitter parseability check.

### Sandbox Verification (Phase 6)
- **Isolated Testing Pipeline**: Creates an ephemeral sandbox directory to safely apply candidate patches.
- **Validation**: Performs strict 4-step validation: AST parsing, static analysis regression checks, security regression checks, and unit testing.
- **Rollback**: Automatically reverts the file state if any validation step fails.
- **Dynamic Frontend**: Animated dashboard with Server-Sent Events (SSE) streaming real-time verification progress and an Optimistic Scoring Engine that dynamically recalculates ISO scores as fixes pass.

### Scoring (ISO/IEC 25010)
```
final_score = 0.50 × metrics_score + 0.30 × structural_score + 0.20 × security_score
```
Sub-characteristics mapped: **Modularity**, **Analysability**, **Modifiability**, **Testability**.

### Frontend
- React 19 + TypeScript + Vite + Tailwind CSS
- Framer Motion animations, Lucide React icons
- Monaco editor–based code viewer (opens on clicking a finding, with issue markers)
- Findings filterable by category (Structural / Metrics / Security)
- Full dependency graph explorer with node focus panel and "View Source Code" button
- "Suggested Fix" UI rendering Unified Diffs and before/after comparisons for auto-fixable findings.
- **Sandbox Verification Dashboard**: An SSE-powered UI queue tracking fix applications, animated code changes, and dynamic scoring increases.
- JSON report export

### API
All errors return `{"error": {"code": "...", "message": "..."}}`.

**SSE event stream (POST `/analyze`)**
```
data: {"type": "file",  "path": "src/foo.py"}
data: {"type": "edge",  "source": "src/foo.py", "target": "src/bar.py"}
data: {"type": "done",  "result": { ... }}
data: {"type": "error", "error": {"code": "ANALYSIS_FAILED", "message": "..."}}
```

**Final result shape**
```json
{
  "language": "Python",
  "framework": "FastAPI",
  "files": 42,
  "folders": 8,
  "score": 71,
  "issues": [{"category","title","description","severity","file?","line?"}],
  "tree": ["src/", "  foo.py"],
  "rubric": {
    "final_score": 71.0,
    "structural_score": 85,
    "security_score": 80,
    "metrics_score": 60.0,
    "category_breakdown": {"modularity","analysability","modifiability","testability"},
    "metric_ratings": {"cof","afferent_couplings","public_fields","public_methods","dit","lcom"}
  },
  "graph": {"nodes": [{"id","label"}], "edges": [{"source","target"}]},
  "session_id": "uuid"
}
```

Error codes: `INVALID_FILE_TYPE`, `INVALID_ARCHIVE`, `ARCHIVE_TOO_LARGE`, `SESSION_NOT_FOUND`, `FILE_NOT_FOUND`, `INVALID_PATH`, `ANALYSIS_FAILED`.

**Repair Request (POST `/repair`)**
Input: `{"session_id": "uuid", "finding": {...}}`
Returns candidate patch data (unified diff, verification status, explanation) if a repair is available for the finding.

**Sandbox Run Request (POST `/sandbox/run`)**
Input: `{"session_id": "uuid", "findings": [{...}]}`
Streams sandbox execution steps (`fix_started`, `parse_started`, `test_completed`, `fix_passed`, `fix_failed`, etc.) using Server-Sent Events.

---

## Not implemented / future scope

The following appear in planning documents but are **not yet in the code**:

- GitHub URL ingestion (UI tab present, not functional)
- Paste-code input
- Clone / duplication detection
- Halstead metrics or Maintainability Index
- Threshold cross-validation against non-Java corpora
- C-language (`.c`) support
- PostgreSQL session metadata storage
- User accounts / history

---

## Setup and run

### Prerequisites
- **Node.js ≥ 18** and **npm**
- **Python 3.10+**

### Frontend

```powershell
# From repo-up/
npm install
npm run dev
# Opens at http://localhost:5173
```

### Backend (Windows PowerShell)

```powershell
# From repo-up/backend/
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Backend (Unix/macOS)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Run tests

```powershell
# From repo-up/backend/ (venv active)
python test_scorer.py
python test_ast.py
python validate.py
```

### Usage
1. Open `http://localhost:5173`
2. Upload a `.zip` of any Python, JS/TS, Java, or C++ project
3. Watch the dependency graph stream in live
4. Review the dashboard: score, ISO metrics, findings
5. Click any finding with a file path to open the code viewer at the relevant line

### Dataset Generation Pipeline (Phase 10)
Repo-Up includes an offline pipeline for generating high-quality vulnerability and repair datasets. This bypasses the UI and creates a reproducible, mathematically validated structured output (JSONL, CSV).
To use the dataset pipeline:
```powershell
# From repo-up/backend/ (venv active)
# Run the synthetic dataset generation
python evaluation/generate_datasets.py

# Run the evaluation benchmark
python run_cross_language_benchmark.py
```
This generates `manifest.json`, `eval_report.json`, and `benchmark_report.md` in the `backend/evaluation/` directory.

---

## Architecture

```
Frontend (React/Vite)
   │   POST /analyze  (multipart/form-data)
   │◄──SSE stream (file / edge / done / error events)
   │
FastAPI backend
   ├── upload_service.py   — extract ZIP, validate limits
   ├── graph_service.py    — Tree-sitter AST → NetworkX DiGraph (streaming)
   ├── rules/structural.py — 5 structural checks
   ├── rules/security.py   — regex secret detection
   ├── rules/ast_security.py — AST: eval/exec, missing try-catch
   ├── repair/             — Auto-fix engine (LLM suggestions, patch diffs)
   ├── verification/       — Sandbox environments (sandbox.py, runner.py)
   ├── metrics/class_metrics.py — DIT, WMC proxy, LCOM proxy
   ├── metrics/graph_metrics.py — COF, afferent, CBO, Tarjan SCC
   └── scorer.py           — ISO 25010 weighted score
```
