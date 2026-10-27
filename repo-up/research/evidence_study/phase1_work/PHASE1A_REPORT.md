# Phase 1A: Benchmark Metadata Audit Report

**Date:** 2026-10-27  
**Protocol Version:** `0.1.0 (frozen)`  
**Study Title:** *When Does Repair Evidence Pay Off? An Oracle-Guided Study of Evidence Selection for Python Vulnerability Repair*

---

## 1. Provenance and Scope

- **Benchmark Repository:** `https://github.com/bytedance/PatchEval`
- **Benchmark Commit Hash:** `b43285cdde80cc04608d5f1178a330b740c91c2d`
- **Metadata Path:** `%USERPROFILE%\research\PatchEval\patcheval\datasets\patcheval_verified.json`
- **Audit Objective:** Inspect official benchmark metadata and produce a reproducible Python candidate inventory under low-storage constraints.

---

## 2. Hard Storage and Protocol Guardrails

- **Docker operations:** 0 Docker pulls, 0 image builds, 0 container executions.
- **Source repositories:** No benchmark repository source trees or git clones downloaded into workspace.
- **Model / LLM access:** 0 model weights downloaded, 0 Kaggle calls, 0 LLM queries.
- **Data leakage prevention:** Reference patch snippets (`patch`) and ground-truth fix functions (`fix_func`) are strictly excluded from all candidate records.
- **Repo-Up project code:** 0 lines of Repo-Up application code modified.
- **Phase 0 artifacts:** All Phase 0 protocol, configuration, schema, checklist, and test files remain untouched and verified.

---

## 3. Metadata Structure and Field Inventory

The benchmark metadata file `patcheval_verified.json` contains a root JSON array with **230** total records. Every record contains exactly 9 standard keys:

| Field Name | Type | Description |
|---|---|---|
| `cve_id` | string | Standard CVE identifier (e.g. `CVE-2020-26215`) |
| `cve_description` | string | Description of vulnerability and vulnerability context |
| `cwe_info` | object | Dictionary mapping CWE identifier (e.g. `CWE-601`) to name and description |
| `repo` | string | Upstream repository URL (e.g. `https://github.com/jupyter/notebook`) |
| `patch_url` | array of strings | Upstream commit URLs for the official fix |
| `programming_language` | string | Primary implementation language (`Go`, `JavaScript`, or `Python`) |
| `vul_func` | array of objects | Metadata for vulnerable functions (id, commit, file_path, lines, snippet, vul_localization) |
| `fix_func` | array of objects | Ground-truth reference fix metadata (excluded from candidates) |
| `image_url` | string | Official GHCR Docker image identifier (e.g. `ghcr.io/patcheval-cve/patcheval-cve:...`) |

---

## 4. Metadata Inventory & Findings

- **Total records:** 230
- **Language distribution:**
  - `Go`: 83 (36.09%)
  - `JavaScript`: 77 (33.48%)
  - `Python`: 70 (30.43%)
- **Python candidate count:** **70**
- **Distinct Python repositories:** 48
- **Duplicate CVE IDs:** 0 (all 230 CVEs are unique)
- **Missing or malformed metadata fields in Python records:** 0
  - All 70 Python candidates have non-empty `cve_description`.
  - All 70 Python candidates have non-empty, structured `cwe_info`.
  - All 70 Python candidates specify an upstream `repo` URL.
  - All 70 Python candidates specify at least 1 vulnerable function in `vul_func`.
  - All 70 Python candidates reference valid Docker image tags matching `name:tag`.

---

## 5. Artifacts Generated

All Phase 1A outputs are confined to `research/evidence_study/phase1_work/`:
- `inventory_metadata.py`: Deterministic inventory and metadata audit tool (12.2 KB).
- `metadata_inventory.json`: Machine-readable summary of counts, languages, and commit info (435 bytes).
- `python_candidates.csv`: Deterministic CSV inventory of the 70 Python candidate tasks (10.9 KB).
- `metadata_issues.jsonl`: Detailed log of metadata anomalies (0 bytes; 0 issues detected).
- `test_inventory.py`: Automated test suite covering edge cases, missing fields, duplicates, and leak prevention (5.9 KB).

**Total disk impact:** ~30 KB across all generated files.

---

## 6. Stop/Go and Limitations

- **Phase 1A Verdict:** **PASS** (The metadata inventory is valid, reproducible, and compliant with protocol constraints).
- **Eligibility Caution:** This pass confirms *metadata presence only*. As defined by the Phase 0 protocol, benchmark-task eligibility (`eligible=true`) is **not** established until Phase 1B/Phase 2 verify clean reproducible vulnerable reset, official security validator execution, and passing reference validation in isolated environments.
