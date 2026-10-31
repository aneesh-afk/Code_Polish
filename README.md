# Repo-Up
## Intelligent Multi-Language Code Quality Analysis, Automated Program Repair, and Empirical Repair Evaluation Framework

**Project:** Repo-Up  
**Domain:** Software Engineering, Static Analysis, Automated Program Repair, Software Quality Assessment  
**Architecture:** Full-stack web application with an independent research and evaluation pipeline  
**Backend:** Python, FastAPI, Tree-sitter, NetworkX  
**Frontend:** React, TypeScript, Vite, Tailwind CSS  
**Research Standards:** ISO/IEC 25010, CK-style software metrics, empirical software engineering  
**Project Status:** Core implementation developed; repair evaluation, benchmark expansion, and experimental validation ongoing.

---

# 1. Project Overview

Repo-Up is a web-based, multi-language software quality analysis and automated repair platform designed to evaluate, understand, and improve the structural quality, maintainability, security, and reliability of software repositories.

The platform allows developers and researchers to upload an entire codebase as a ZIP archive and automatically generates a comprehensive software quality assessment.

Unlike conventional static analysis tools that primarily identify coding violations, Repo-Up combines multiple dimensions of software analysis into one integrated environment:

1. Structural software quality analysis.
2. Source-code parsing and dependency relationship extraction.
3. CK-style object-oriented software metrics.
4. Security vulnerability and insecure coding pattern detection.
5. ISO/IEC 25010-aligned software quality scoring.
6. Automated repair candidate generation.
7. Isolated sandbox-based patch verification.
8. Comparative evaluation of multiple automated repair approaches.
9. Reproducible vulnerability and repair dataset generation.
10. Cross-language benchmarking and empirical research.

The central objective of Repo-Up is not simply to identify problems in a repository, but to investigate whether detected problems can be repaired safely, whether the resulting modifications preserve program correctness, and whether those repairs produce measurable improvements in software quality.

The project therefore combines two complementary systems:

- **Repo-Up Application:** The developer-facing platform for repository ingestion, analysis, visualization, repair, and verification.
- **Repo-Up Research Framework:** The experimental environment for dataset construction, repair-method comparison, benchmark execution, and quantitative evaluation.

The overall workflow is:

**Upload → Extract → Parse → Analyze → Measure → Detect → Score → Generate Repairs → Verify → Evaluate → Report**

---

# 2. Problem Statement

Software repositories frequently accumulate structural and security-related problems as development progresses.

Examples include:

- Excessive coupling between source files.
- Poor modularization.
- Missing project documentation.
- Inadequate testing infrastructure.
- Deep inheritance hierarchies.
- High method complexity and poor class cohesion.
- Circular dependencies.
- Hardcoded credentials and secrets.
- Unsafe function execution.
- Insecure deserialization.
- Weak cryptographic algorithms.
- Missing exception handling.
- Inadequate dependency management.

Existing code analysis tools can identify many of these problems. However, identifying a problem and successfully correcting it are two different challenges.

A static analyzer may report a vulnerability without providing a safe repair. An AI-based code generation system may suggest a correction that introduces syntax errors, changes program behavior, breaks dependencies, or causes existing tests to fail.

Furthermore, a repair that appears correct at the source-code level does not necessarily improve the overall quality of a software repository.

Repo-Up addresses these challenges through an integrated analysis-and-repair architecture.

The research investigates the following central question:

**Can multiple automated program repair approaches be systematically evaluated using a common multi-language analysis framework and an isolated verification pipeline, while measuring both repair correctness and improvements in software quality?**

---

# 3. Research Objectives

The major objectives are:

### Objective 1: Multi-language repository analysis

Develop an automated system capable of processing complete software repositories written in multiple programming languages using syntax-aware parsing.

### Objective 2: Software quality measurement

Extract structural and object-oriented metrics and map them to selected ISO/IEC 25010 quality characteristics.

### Objective 3: Vulnerability detection

Identify structural weaknesses, insecure coding patterns, and potentially dangerous source-code constructs.

### Objective 4: Automated program repair

Generate candidate modifications for detected findings using multiple repair strategies.

### Objective 5: Repair verification

Determine whether generated patches are syntactically valid, avoid static-analysis and security regressions, and pass available unit tests.

### Objective 6: Comparative repair evaluation

Evaluate four planned repair approaches under a common experimental protocol, using the same datasets, findings, and verification criteria.

### Objective 7: Reproducible benchmark construction

Develop a repeatable dataset-generation and benchmarking pipeline that can process repositories incrementally without retaining unnecessary downloaded source archives.

### Objective 8: Quality improvement assessment

Measure whether successful repairs improve the software quality assessment and whether the improvements are achieved without introducing regressions.

---

# 4. Overall System Architecture

Repo-Up consists of two major environments.

## 4.1 Application architecture

The application handles interactive repository analysis and repair.

```text
                    USER
                     |
                     v
             REPO-UP FRONTEND
              React + Vite
                     |
                     v
               FASTAPI BACKEND
                     |
          +----------+----------+
          |                     |
          v                     v
    INGESTION ENGINE       SESSION MANAGER
          |
          v
    REPOSITORY EXTRACTION
          |
          v
     TREE-SITTER PARSING
          |
          +-----------------------+
          |                       |
          v                       v
    DEPENDENCY GRAPH         SOURCE ANALYSIS
          |                       |
          v                       v
    NETWORKX GRAPH         STATIC ANALYSIS
          |                       |
          +-----------+-----------+
                      |
                      v
               METRICS ENGINE
                      |
                      v
              QUALITY SCORER
                      |
                      v
              FINDINGS ENGINE
                      |
                      v
              REPAIR ENGINE
                      |
                      v
              SANDBOX ENGINE
                      |
          +-----------+-----------+
          |                       |
          v                       v
     PATCH VERIFIED          PATCH REJECTED
          |
          v
     SCORE RECOMPUTATION
          |
          v
       FINAL REPORT
```

## 4.2 Research architecture

The research environment operates independently of the normal application workflow.

```text
              RESEARCH FRAMEWORK
                      |
                      v
             DATASET ACQUISITION
                      |
                      v
          REPOSITORY DOWNLOAD / EXTRACTION
                      |
                      v
             VULNERABILITY ANALYSIS
                      |
                      v
             DATASET CONSTRUCTION
                      |
                      v
              REPAIR EXPERIMENTS
                      |
           +----------+----------+
           |          |          |
           v          v          v
        METHOD 1   METHOD 2   METHOD 3
           |          |          |
           +----------+----------+
                      |
                      v
                  METHOD 4
                      |
                      v
             PATCH VERIFICATION
                      |
                      v
             METRIC COLLECTION
                      |
                      v
          CROSS-METHOD COMPARISON
                      |
                      v
             STATISTICAL REPORTS
```

The four repair approaches are intended to operate under a shared evaluation protocol. Their precise algorithm names, model configurations, and implementation status must be confirmed against the final research code before being published as completed methods.

---

# 5. Repository Ingestion and Processing

## 5.1 ZIP-based repository ingestion

Repo-Up accepts complete software repositories in ZIP format.

Current ingestion limits:

| Parameter | Limit |
|---|---:|
| Maximum compressed archive | 50 MB |
| Maximum extracted content | 300 MB |
| Session lifetime | 2 hours |
| Extraction mode | Session-scoped temporary directory |

The ingestion engine performs:

- File type validation.
- Archive integrity validation.
- ZIP-slip path traversal protection.
- Symbolic-link rejection.
- File-count and extracted-size restrictions.
- Session-specific directory creation.
- Temporary repository cleanup.

These protections prevent malicious archives from writing files outside their intended extraction directory or exhausting available storage.

## 5.2 Supported programming languages

The existing parser supports:

| Language | Extensions |
|---|---|
| Python | `.py` |
| JavaScript | `.js`, `.jsx` |
| TypeScript | `.ts`, `.tsx` |
| Java | `.java` |
| C++ | `.cpp`, `.cc`, `.cxx`, `.hpp`, `.h` |

Tree-sitter provides syntax-aware parsing, allowing the system to examine source-code structures without relying entirely on regular expressions.

C-language `.c` support is a planned extension rather than an assumed existing capability.

## 5.3 File and directory analysis

The extracted repository is examined to identify:

- Source files.
- Directory hierarchy.
- Project configuration files.
- Dependency manifests.
- Test directories.
- Documentation files.
- Environment configuration templates.
- Potentially sensitive files.

The resulting repository tree is presented through the frontend.

---

# 6. Dependency Graph Analysis

Repo-Up constructs a directed file-level dependency graph.

Each source file is represented as a graph node.

An import or dependency relationship between two files is represented as a directed edge.

The graph is generated using:

- Tree-sitter-based import extraction.
- File-level import resolution.
- NetworkX directed graph structures.
- Graph traversal and connectivity analysis.

### Graph representation

```text
src/main.py
     |
     +------> src/auth.py
     |
     +------> src/database.py
                     |
                     +------> src/config.py
```

### Graph capabilities

- File-level dependency visualization.
- Import relationship identification.
- In-degree and out-degree measurement.
- Coupling analysis.
- Circular dependency detection.
- Strongly connected component analysis.
- Identification of highly connected files.

Tarjan's strongly connected components algorithm is used to identify circular dependency structures.

The frontend uses D3 force-directed graph visualization to provide an interactive representation of the repository.

Users can:

- Explore dependency relationships.
- Focus on individual nodes.
- Inspect connected files.
- Examine source code.
- Understand how a finding relates to the repository structure.

Dependency graph information is also used by the metrics and structural analysis engines.

---

# 7. Structural and Security Analysis

Repo-Up combines structural rule-based checks, syntax-aware security analysis, and pattern-based secret detection.

## 7.1 Structural analysis

| Rule | Severity |
|---|---|
| Missing README | High |
| Missing `src/` directory | Medium |
| Missing `tests/` directory | High |
| Missing dependency manifest | High |
| Missing `.env.example` | Medium |
| Committed `.env` file | High |
| Circular dependencies | High |
| High file-level coupling | Medium |

The dependency manifest check considers language-specific files such as `requirements.txt` and `package.json`.

These rules are intended to identify repository organization and maintainability weaknesses.

## 7.2 Security analysis

The security engine examines source files for potentially dangerous constructs and insecure practices.

| Detection | Analysis approach | Severity |
|---|---|---|
| AWS access key patterns | Pattern matching | High |
| Generic API keys and tokens | Regex detection | High |
| Hardcoded secrets | Pattern matching | High |
| `eval()` usage | AST-based analysis | High |
| `exec()` usage | AST-based analysis | High |
| Dangerous `system()` usage | Source/AST analysis | High |
| Missing exception handling around selected I/O/network imports | Rule-based analysis | Medium |

Security findings are reported with their associated source locations wherever available.

**Research limitation:** Pattern matching and AST-based rules identify suspicious constructs, not necessarily exploitable vulnerabilities. Findings therefore require contextual validation. For example, the presence of `eval()` does not independently establish exploitability.

---

# 8. Software Quality Metrics

Repo-Up implements a collection of CK-style and dependency-graph-based metric proxies.

These metrics are used to characterize structural complexity, coupling, inheritance, and cohesion.

| Metric | Measurement |
|---|---|
| COF | File-level graph coupling factor |
| Afferent Coupling | Average incoming dependencies per file |
| WMC proxy | Average public method count per class |
| Public Fields | Average public field count per class |
| DIT | Average depth of inheritance tree |
| LCOM proxy | Average methods-minus-one per class |

## 8.1 Coupling Factor (COF)

The current implementation calculates:

\[
COF = \frac{E}{N(N-1)}
\]

Where:

- \(E\) = number of directed dependency edges.
- \(N\) = number of source-file nodes.

The result represents normalized file-level coupling.

For a graph with fewer than two nodes, the metric requires a defined zero-denominator handling policy.

## 8.2 Afferent Coupling

Afferent coupling measures the average number of incoming dependencies.

\[
Ca_{avg} = \frac{\sum_{i=1}^{N} indegree(i)}{N}
\]

Higher values can indicate that more files depend on a particular set of modules, potentially increasing the impact of modifications.

## 8.3 Weighted Methods per Class proxy

The current metric approximates WMC using public method counts.

\[
WMC_{proxy} =
\frac{\sum_{i=1}^{C} PublicMethods_i}{C}
\]

Where \(C\) represents the number of analyzed classes.

## 8.4 Depth of Inheritance Tree

DIT estimates inheritance depth for supported class structures.

A deeper inheritance hierarchy can increase the effort required to understand and modify a class.

## 8.5 Lack of Cohesion proxy

The implemented approximation is:

\[
LCOM_{proxy} =
\frac{\sum_{i=1}^{C}\max(0,Methods_i-1)}{C}
\]

This is a simplified proxy, not the original CK LCOM formulation.

## 8.6 Threshold references

The current metric thresholds are documented as drawing from:

Ferreira et al. (2012), *Journal of Systems and Software*, 85(2), 244–257.

Threshold applicability and cross-language validity remain important research considerations.

**Important methodological distinction:** These measurements should be described as CK-style proxies rather than claiming that every original CK metric is implemented exactly. File-level graph coupling and class-level object-oriented metrics are also different measurement levels.

---

# 9. ISO/IEC 25010-Aligned Quality Scoring

Repo-Up converts the extracted metrics and analysis results into a normalized software quality score.

The current weighted scoring formula is:

\[
S_{final} =
0.50S_{metrics}
+0.30S_{structural}
+0.20S_{security}
\]

Where:

- \(S_{metrics}\) = normalized metrics score.
- \(S_{structural}\) = structural quality score.
- \(S_{security}\) = security score.

Each component is normalized to a 0–100 scale.

The resulting score provides a consolidated view of repository quality.

## 9.1 Quality characteristics

The scoring framework maps the measurements to selected ISO/IEC 25010-aligned characteristics:

| Quality characteristic | Interpretation |
|---|---|
| Modularity | Degree to which the software is organized into distinct components |
| Analysability | Ease of understanding and examining the software |
| Modifiability | Ease of changing software without introducing unintended effects |
| Testability | Ease of establishing test criteria and performing verification |

The score is a project-specific quality assessment model inspired by ISO/IEC 25010.

It should not be interpreted as an official ISO certification or a complete implementation of the entire ISO quality model.

## 9.2 Score breakdown

The dashboard presents:

- Overall quality score.
- Structural quality score.
- Security score.
- Metrics score.
- Category-level breakdown.
- Individual metric ratings.

The scoring system is also used to examine whether verified repairs result in measurable quality improvements.

---

# 10. Automated Program Repair Engine

One of the central components of Repo-Up is its automated repair engine.

Traditional static analysis identifies problematic code, but Repo-Up additionally attempts to generate candidate modifications.

The repair engine is divided into multiple levels of repair assistance.

## 10.1 Tier 1: Deterministic automatic repair

This tier handles findings for which a predefined, predictable transformation can be generated.

Currently supported examples include:

- Replacing unsafe YAML loading with `yaml.safe_load`.
- Replacing weak cryptographic hash algorithms with stronger alternatives through supported transformations.

The objective is to avoid unnecessary AI generation when a deterministic modification is sufficient.

## 10.2 Tier 2 and Tier 3: Suggested repairs and explanations

For more complex findings, Repo-Up provides repair suggestions and actionable explanations.

Examples include:

- Unsafe deserialization.
- Dangerous execution constructs.
- Missing exception handling.
- Unsafe assertions.

These cases may require contextual understanding and cannot always be corrected using simple string replacement.

The system can use LLM-generated suggestions for supported findings.

These suggestions are candidate patches, not automatically trusted modifications.

## 10.3 Patch representation

Candidate repairs contain information such as:

- Affected file.
- Original code.
- Proposed replacement.
- Unified diff.
- Explanation.
- Verification state.

The frontend displays the proposed changes using before-and-after comparisons and unified diffs.

## 10.4 Patch validation

Before accepting a generated patch, Repo-Up applies a strict validation procedure.

1. Path escape protection.
2. Line-boundary validation.
3. Exact old-text matching.
4. Non-empty resulting content validation.
5. Tree-sitter parseability validation.

This prevents malformed patches and unintended modifications from being accepted by the repair engine.

---

# 11. Research Extension: Comparative Evaluation of Four Repair Methods

A major research extension of Repo-Up is the comparative evaluation of four automated program repair approaches.

The goal is to move beyond demonstrating that a repair can be generated and instead determine which repair approach performs most reliably under identical experimental conditions.

## 11.1 Research motivation

Different repair approaches may produce different results even when given the same vulnerability or source-code finding.

A method may generate syntactically correct code but fail unit tests.

Another method may pass tests but introduce security regressions.

A third may generate a semantically appropriate patch but require substantially more processing time.

Therefore, repair quality cannot be evaluated using a single metric.

The research framework is designed to compare four repair methods using common inputs, shared validation criteria, and standardized result records.

## 11.2 Four-method experimental design

The experiment uses four independently evaluated repair methods.

| Method | Experimental role | Evaluation |
|---|---|---|
| Repair Method 1 | First candidate repair approach | Generation and verification |
| Repair Method 2 | Second candidate repair approach | Generation and verification |
| Repair Method 3 | Third candidate repair approach | Generation and verification |
| Repair Method 4 | Fourth candidate repair approach | Generation and verification |

The exact method identities and configurations should be taken from the finalized research implementation, rather than inferred from the existing Tier 1/Tier 2/Tier 3 repair engine.

The four research methods are not automatically equivalent to the three repair assistance tiers in the existing application.

## 11.3 Standardized experiment

Each method receives the same eligible repair task.

The experimental workflow is:

```text
                REPAIR TASK
                     |
                     v
             ORIGINAL SOURCE CODE
                     |
                     v
             VULNERABILITY CONTEXT
                     |
          +----------+----------+
          |          |          |
          v          v          v
       METHOD 1   METHOD 2   METHOD 3
          |          |          |
          +----------+----------+
                     |
                     v
                  METHOD 4
                     |
                     v
              CANDIDATE PATCHES
                     |
                     v
             STANDARD VERIFICATION
                     |
                     v
              METRIC COLLECTION
                     |
                     v
             COMPARATIVE RESULTS
```

Each method must be evaluated independently against the same original source state.

A patch produced by one method must not become the starting source for another method.

This prevents order-dependent improvements from contaminating the comparison.

## 11.4 Experimental control

The following variables should be kept consistent:

- Original source-code version.
- Vulnerability or finding.
- Repair task description.
- Available repository context.
- Test environment.
- Static-analysis rules.
- Security checks.
- Patch acceptance criteria.
- Evaluation metrics.

Model versions, prompts, temperature, token limits, retry policies, and execution environments must be recorded wherever applicable.

This ensures that observed differences are attributable to the repair approaches as far as the experimental design allows.

## 11.5 Evaluation metrics

The research framework should collect the following:

| Metric | Purpose |
|---|---|
| Patch generation success | Whether a method generates a candidate |
| Syntax validity | Whether the resulting source parses |
| Static-analysis pass rate | Whether the patch avoids selected static-analysis regressions |
| Security regression rate | Whether the patch introduces new security findings |
| Unit test pass rate | Whether available tests pass |
| Verified repair rate | Percentage of tasks satisfying all required verification gates |
| Repair latency | Time taken to generate and verify a repair |
| Patch size | Number of changed lines |
| Quality score delta | Change in the repository quality assessment |
| Failure category | Reason a repair was rejected |

A central measure is:

\[
VerifiedRepairRate =
\frac{VerifiedRepairs}{EligibleRepairAttempts}
\times 100
\]

Quality improvement is calculated as:

\[
\Delta S = S_{after}-S_{before}
\]

A positive value indicates an improvement under the Repo-Up scoring model.

Importantly, a successful patch must not be classified as a verified repair merely because it parses successfully.

The full verification policy determines acceptance.

---

# 12. Sandbox-Based Patch Verification

The sandbox verification engine is responsible for determining whether a candidate repair can safely be applied.

This is a critical part of Repo-Up because generated code should not be trusted solely on the basis of its appearance.

## 12.1 Isolated execution

For each repair attempt, the system creates an ephemeral sandbox environment.

The original repository is preserved separately.

The candidate patch is applied to the sandbox copy, preventing experimental changes from corrupting the original extracted source.

## 12.2 Verification stages

The current sandbox verification pipeline contains four major validation stages.

**Stage 1: Syntax and AST validation**

- Apply the candidate patch.
- Parse the modified source.
- Reject syntax-invalid changes.

**Stage 2: Static-analysis regression checks**

- Re-run relevant analysis rules.
- Check whether the modification introduces new structural or code-quality problems.
- Record any regression.

**Stage 3: Security regression checks**

- Re-run applicable security checks.
- Examine whether the patch introduces new insecure patterns.
- Reject patches that violate the configured security acceptance criteria.

**Stage 4: Unit testing**

- Execute available tests in the verification environment.
- Record success, failure, or unavailable test status.
- Prevent unverified test results from being represented as successful.

## 12.3 Rollback mechanism

If any required validation stage fails:

- The candidate modification is rejected.
- The sandbox state is rolled back.
- The original source remains unchanged.
- The failure reason is recorded.

A patch is accepted only when it satisfies the configured validation policy.

## 12.4 Verification events

The sandbox engine streams progress events to the frontend.

Examples include:

```text
fix_started
parse_started
parse_completed
static_analysis_started
security_check_started
test_started
test_completed
fix_passed
fix_failed
```

The frontend displays these events as a live verification queue.

Users can observe the progress of individual repair attempts rather than waiting for a single final response.

## 12.5 Research significance

The sandbox is important for the comparative repair experiments because it establishes a common acceptance criterion for all four repair methods.

It also enables the collection of reproducible experimental outcomes.

**Security boundary:** The sandbox must be treated as an isolation layer, not an automatic guarantee of security. Running untrusted repository code requires OS/container-level isolation, restricted privileges, resource limits, network controls, and process cleanup.

---

# 13. Optimistic Scoring and Quality Improvement

Repo-Up includes a dynamic scoring mechanism that updates the dashboard as verified repairs pass.

When a repair is successfully verified:

1. The repair result is received.
2. The accepted modification is reflected in the analysis state.
3. Relevant metrics and findings are recalculated.
4. The quality score is updated.
5. The dashboard displays the resulting score change.

This gives developers immediate feedback about the potential quality improvement resulting from repair.

The displayed score must remain tied to verified changes. A proposed but rejected patch must not be treated as a successful improvement.

For research reporting, the final score should be computed from a reproducible, fully analyzed repository snapshot rather than relying exclusively on intermediate UI updates.

---

# 14. Research Dataset Generation Pipeline

Repo-Up includes a separate dataset-generation pipeline intended to support repeatable vulnerability and automated repair experiments.

The dataset pipeline operates independently of the interactive web interface.

Its purpose is to construct structured datasets suitable for automated evaluation.

## 14.1 Dataset generation

The existing pipeline is initiated using:

```bash
python evaluation/generate_datasets.py
```

The intended outputs include:

- `manifest.json`
- `eval_report.json`
- Structured JSONL data.
- CSV datasets.

The generated records can capture repository metadata, findings, repair context, and evaluation information according to the implemented dataset schema.

## 14.2 Iterative repository acquisition

A key research workflow is the iterative download, process, and delete approach.

Instead of downloading and retaining every repository simultaneously, the acquisition pipeline processes repositories incrementally.

The intended workflow is:

```text
          REPOSITORY LIST
                 |
                 v
          SELECT NEXT REPO
                 |
                 v
          DOWNLOAD REPOSITORY
                 |
                 v
          EXTRACT / PREPARE
                 |
                 v
          RUN ANALYSIS
                 |
                 v
          GENERATE FINDINGS
                 |
                 v
          RUN REPAIR EXPERIMENTS
                 |
                 v
          VERIFY CANDIDATES
                 |
                 v
          SAVE STRUCTURED RESULTS
                 |
                 v
          VALIDATE SAVED RESULTS
                 |
                 v
          DELETE TEMPORARY COPY
                 |
                 v
          SELECT NEXT REPO
                 |
                 +-------> REPEAT
```

### Why iterative processing?

Downloading many repositories simultaneously can create unnecessary storage consumption and make experiments difficult to manage.

Incremental processing provides several advantages:

- Lower peak disk usage.
- Reduced temporary storage accumulation.
- Easier recovery after failures.
- Clear repository-level experiment boundaries.
- Better resource management.
- Easier reproducibility.
- Reduced risk of accidentally mixing source versions.

### Important deletion policy

The original source repository must not be deleted before the required experiment outputs have been successfully saved and validated.

The intended order is:

1. Download one repository.
2. Record its identity and version.
3. Process and analyze it.
4. Generate repair candidates.
5. Execute the required verification.
6. Save the structured outputs.
7. Validate the output records and manifest.
8. Delete only the temporary downloaded/extracted working copy.
9. Continue with the next repository.

The generated dataset, manifest, logs, and evaluation reports must be retained independently.

This makes the pipeline suitable for processing larger repository collections without requiring all downloaded source code to remain on disk.

## 14.3 Reproducibility metadata

Where supported, each repository should be associated with:

- Repository identifier.
- Source URL.
- Commit hash or immutable revision.
- Programming language.
- Acquisition timestamp.
- Dataset record identifier.
- Analysis configuration.
- Repair method identifier.
- Verification outcome.
- Failure reason.

This information helps researchers reproduce results and trace each evaluation record to its original source state.

---

# 15. Cross-Language Benchmarking

The project includes a benchmark execution script:

```bash
python run_cross_language_benchmark.py
```

The purpose is to assess the behavior of Repo-Up across supported programming languages.

The benchmark examines whether the same analysis and repair evaluation framework can operate consistently across different language ecosystems.

## 15.1 Benchmark dimensions

- Repository ingestion success.
- Parsing success.
- Dependency extraction.
- Structural finding detection.
- Security finding detection.
- Metric extraction.
- Repair candidate generation.
- Patch verification.
- Quality score calculation.

## 15.2 Cross-language research questions

The benchmark is intended to investigate:

1. Whether Tree-sitter parsing works consistently across the supported languages.
2. Whether file-level dependency extraction is comparable across language ecosystems.
3. Whether metric proxies behave consistently across different language paradigms.
4. Whether security rules produce different false-positive patterns across languages.
5. Whether repair approaches demonstrate different success rates across languages.
6. Whether the quality scoring model requires language-specific calibration.

The results should not assume that equivalent numerical values necessarily have identical meanings across languages.

Cross-language validity and threshold calibration are explicit research concerns.

---

# 16. Research Organization and Parallel Development

Repo-Up is being developed through separate workstreams so that application development, repair-method research, and benchmark construction can progress independently.

The research work is organized around three broad responsibilities.

## Workstream 1: Core application and analysis

Responsibilities:

- Repository ingestion.
- Multi-language parsing.
- Dependency graph generation.
- Structural analysis.
- Security detection.
- Metric extraction.
- ISO-aligned scoring.
- Frontend and API integration.

## Workstream 2: Repair methods

Responsibilities:

- Implementation of the four planned repair approaches.
- Common repair-task input format.
- Patch generation.
- Method-specific configuration.
- Repair output normalization.
- Error and failure handling.
- Comparison-ready experiment records.

## Workstream 3: Dataset and evaluation

Responsibilities:

- Repository acquisition.
- Iterative download and cleanup.
- Vulnerability dataset construction.
- Benchmark execution.
- Sandbox verification.
- Cross-language evaluation.
- Comparative metrics and reports.

## Integration and coordination

The integration process ensures that all workstreams use the same:

- Frozen source snapshots.
- Finding schema.
- Repair task representation.
- Patch format.
- Verification criteria.
- Dataset identifiers.
- Experimental configuration.

Separate development folders and tools, including the RuntimeGate Kit research workspace discussed during development, should be treated as research infrastructure unless their code has actually been integrated into the main Repo-Up application.

A separate research harness does not automatically mean that its functionality is available through the main web application.

---

# 17. Frontend Architecture

The Repo-Up frontend is developed using:

- React 19.
- TypeScript.
- Vite.
- Tailwind CSS.
- Framer Motion.
- Lucide React.
- Monaco Editor.
- D3 force-directed graph visualization.

## 17.1 Dashboard

The dashboard provides an overview of repository quality.

It displays:

- Overall quality score.
- Structural score.
- Security score.
- Metrics score.
- Total files and folders.
- Programming language.
- Framework identification.
- Finding counts and severities.

## 17.2 Findings explorer

Findings can be filtered by:

- Structural.
- Metrics.
- Security.

Each finding includes relevant descriptive information and source location where available.

## 17.3 Code viewer

Monaco Editor provides an interactive source-code viewing experience.

When a user selects a finding:

- The corresponding file is opened.
- The relevant line is located.
- Issue markers highlight the problematic code.
- The user can inspect the source context.

## 17.4 Dependency explorer

The dependency explorer allows users to:

- Visualize the source-file graph.
- Select individual nodes.
- Examine dependencies.
- Focus on connected modules.
- Navigate to source code.

## 17.5 Repair interface

The repair interface presents:

- Repair explanations.
- Candidate unified diffs.
- Before-and-after source comparisons.
- Patch validation information.
- Verification status.

## 17.6 Sandbox verification dashboard

The sandbox interface provides live progress information.

It visualizes:

- Repair execution.
- Patch application.
- Parsing.
- Static-analysis checks.
- Security checks.
- Unit test results.
- Accepted and rejected repairs.

The dashboard also updates the quality score when verified modifications are reflected in the analysis.

## 17.7 Reporting

The application supports JSON report export.

The report is intended to provide a structured representation of repository findings, metrics, quality scores, and dependency information.

---

# 18. Backend API

The backend uses FastAPI.

All API errors follow the common response structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable explanation"
  }
}
```

## 18.1 Repository analysis

**POST `/analyze`**

Accepts a ZIP repository using multipart/form-data.

The analysis process streams file and dependency information using Server-Sent Events.

Example:

```text
data: {"type":"file","path":"src/foo.py"}

data: {
  "type":"edge",
  "source":"src/foo.py",
  "target":"src/bar.py"
}

data: {
  "type":"done",
  "result": { ... }
}
```

The final event contains the analysis result.

## 18.2 Repair request

**POST `/repair`**

Example input:

```json
{
  "session_id": "uuid",
  "finding": {
    "category": "Security",
    "title": "Unsafe YAML deserialization",
    "file": "src/config.py",
    "line": 15
  }
}
```

Returns candidate repair information when a supported repair is available.

Possible output information includes:

- Unified diff.
- Proposed modification.
- Explanation.
- Verification-related status.

## 18.3 Sandbox execution

**POST `/sandbox/run`**

Example input:

```json
{
  "session_id": "uuid",
  "findings": [
    {
      "category": "Security",
      "title": "Unsafe YAML deserialization",
      "file": "src/config.py",
      "line": 15
    }
  ]
}
```

The endpoint streams execution events using SSE.

Possible event types include:

```text
fix_started
parse_started
test_completed
fix_passed
fix_failed
```

## 18.4 Error codes

| Error code | Meaning |
|---|---|
| `INVALID_FILE_TYPE` | Unsupported upload format |
| `INVALID_ARCHIVE` | Invalid or corrupted archive |
| `ARCHIVE_TOO_LARGE` | Archive exceeds permitted limits |
| `SESSION_NOT_FOUND` | Analysis session does not exist |
| `FILE_NOT_FOUND` | Requested source file does not exist |
| `INVALID_PATH` | Invalid or unsafe file path |
| `ANALYSIS_FAILED` | Repository analysis failed |

---

# 19. Analysis Result Structure

A representative analysis response has the following structure:

```json
{
  "language": "Python",
  "framework": "FastAPI",
  "files": 42,
  "folders": 8,
  "score": 71,
  "issues": [
    {
      "category": "Security",
      "title": "Unsafe function usage",
      "description": "Potentially unsafe execution pattern",
      "severity": "High",
      "file": "src/example.py",
      "line": 25
    }
  ],
  "tree": [
    "src/",
    "  foo.py"
  ],
  "rubric": {
    "final_score": 71.0,
    "structural_score": 85,
    "security_score": 80,
    "metrics_score": 60.0,
    "category_breakdown": {
      "modularity": 80,
      "analysability": 75,
      "modifiability": 70,
      "testability": 65
    },
    "metric_ratings": {
      "cof": 70,
      "afferent_couplings": 65,
      "public_fields": 80,
      "public_methods": 75,
      "dit": 85,
      "lcom": 60
    }
  },
  "graph": {
    "nodes": [
      {
        "id": "src/foo.py",
        "label": "foo.py"
      }
    ],
    "edges": [
      {
        "source": "src/foo.py",
        "target": "src/bar.py"
      }
    ]
  },
  "session_id": "uuid"
}
```

This is an illustrative response structure. The exact result fields and value types should be aligned with the current backend implementation.

---

# 20. Technology Stack

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | React 19 | User interface |
| Language | TypeScript | Frontend type safety |
| Build tool | Vite | Development and bundling |
| Styling | Tailwind CSS | UI styling |
| Animation | Framer Motion | UI transitions |
| Icons | Lucide React | Interface icons |
| Code editor | Monaco Editor | Source-code inspection |
| Graph visualization | D3 | Dependency visualization |
| Backend | Python | Analysis and orchestration |
| API | FastAPI | HTTP and streaming endpoints |
| Parsing | Tree-sitter | Syntax-aware parsing |
| Graph analysis | NetworkX | Dependency graph algorithms |
| Graph algorithms | Tarjan SCC | Circular dependency detection |
| Data exchange | JSON / JSONL / CSV | Analysis and research datasets |
| Communication | SSE | Live progress updates |
| Testing | Python testing utilities | Validation and regression testing |
| Repair verification | Isolated sandbox | Patch verification |

---

# 21. Project Directory Structure

The following represents the logical organization of the application and research components. Exact filenames should be reconciled with the actual repository.

```text
repo-up/
│
├── backend/
│   │
│   ├── main.py
│   ├── requirements.txt
│   ├── upload_service.py
│   ├── graph_service.py
│   ├── scorer.py
│   │
│   ├── rules/
│   │   ├── structural.py
│   │   ├── security.py
│   │   └── ast_security.py
│   │
│   ├── metrics/
│   │   ├── class_metrics.py
│   │   └── graph_metrics.py
│   │
│   ├── repair/
│   │   ├── repair_engine.py
│   │   ├── patch_generator.py
│   │   └── validation.py
│   │
│   ├── verification/
│   │   ├── sandbox.py
│   │   └── runner.py
│   │
│   ├── evaluation/
│   │   ├── generate_datasets.py
│   │   ├── manifest.json
│   │   ├── eval_report.json
│   │   └── benchmark_report.md
│   │
│   ├── run_cross_language_benchmark.py
│   ├── test_scorer.py
│   ├── test_ast.py
│   └── validate.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── types/
│   │
│   └── ...
│
├── research/
│   ├── datasets/
│   ├── experiments/
│   ├── results/
│   └── documentation/
│
└── README.md
```

The `research/` directory represents the proposed logical organization of the broader research work. Its existence and contents must not be assumed until confirmed in the repository.

---

# 22. Installation and Execution

## 22.1 Prerequisites

- Node.js 18 or later.
- npm.
- Python 3.10 or later.
- Git (recommended).

## 22.2 Frontend installation

From the project root:

```powershell
npm install
npm run dev
```

The frontend runs at:

```text
http://localhost:5173
```

## 22.3 Backend installation — Windows

```powershell
cd backend

python -m venv venv

.\venv\Scripts\Activate.ps1

pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

## 22.4 Backend installation — Linux/macOS

```bash
cd backend

python -m venv venv

source venv/bin/activate

pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

## 22.5 Run tests

From the backend directory:

```bash
python test_scorer.py

python test_ast.py

python validate.py
```

## 22.6 Run dataset generation

```bash
python evaluation/generate_datasets.py
```

## 22.7 Run cross-language benchmarking

```bash
python run_cross_language_benchmark.py
```

---

# 23. How to Use Repo-Up

1. Start the backend and frontend.
2. Open `http://localhost:5173`.
3. Upload a supported software repository as a ZIP archive.
4. Wait for the repository extraction and parsing process.
5. Observe the dependency graph being generated through live streaming.
6. Review the structural, metrics, and security findings.
7. Examine the overall ISO/IEC 25010-aligned quality score.
8. Select a finding to inspect its source code.
9. Request a suggested repair where supported.
10. Examine the proposed unified diff.
11. Submit supported repair candidates for sandbox verification.
12. Observe the verification progress.
13. Review accepted and rejected repairs.
14. Examine the updated quality assessment.
15. Export the analysis report.

---

# 24. Research Evaluation Methodology

The research component uses a controlled experimental methodology.

## 24.1 Experimental unit

The experimental unit is a repair task associated with a specific source-code finding in a fixed repository revision.

## 24.2 Baseline measurement

Before applying repairs, the system records:

- Original source code.
- Original analysis findings.
- Baseline metrics.
- Baseline quality score.
- Available unit test results.
- Repository metadata.

## 24.3 Repair execution

Each of the four repair methods receives the same eligible task.

The output is captured independently.

## 24.4 Verification

Each candidate is passed through the same verification pipeline.

Results are categorized as:

- Generation failure.
- Patch application failure.
- Syntax failure.
- Static-analysis regression.
- Security regression.
- Test failure.
- Verification success.
- Verification unavailable.

An unavailable test environment must not be counted as a successful test.

## 24.5 Comparative evaluation

The four methods are compared using:

- Verified repair rate.
- Syntax validity.
- Unit test pass rate.
- Security regression rate.
- Static-analysis regression rate.
- Average repair latency.
- Patch size.
- Quality score improvement.

The evaluation should also report denominators, excluded tasks, and missing results to avoid misleading percentages.

## 24.6 Statistical analysis

Depending on the final dataset size and experimental design, suitable statistical analyses may include:

- Descriptive statistics.
- Confidence intervals.
- Paired comparisons for repair methods evaluated on the same tasks.
- Non-parametric comparisons where metric distributions require them.
- Per-language and per-vulnerability-category breakdowns.

The statistical procedure must be selected based on the actual experimental data, not chosen after observing which method appears best.

---

# 25. Current Limitations

Repo-Up is a research-oriented platform, and several limitations remain.

## 25.1 Analysis limitations

- Language-specific parsing differences.
- Incomplete dependency resolution in complex repositories.
- Potential false positives from pattern-based security checks.
- Simplified CK-style metric proxies.
- Language-dependent interpretation of object-oriented metrics.
- Limited coverage of advanced interprocedural analysis.

## 25.2 Repair limitations

- Not every finding has a supported repair.
- LLM-generated patches may be incorrect.
- Some changes require broader project context.
- Tests may be missing or incomplete.
- A passing test suite cannot establish complete behavioral correctness.
- Sandbox isolation requires additional security hardening for untrusted code.

## 25.3 Research limitations

- Dataset representativeness must be established.
- Cross-language metric thresholds require validation.
- Repair-method comparisons require controlled configurations.
- Repository versions must be fixed for reproducibility.
- Benchmark results may depend on model versions and execution environments.
- Synthetic datasets must be distinguished from real-world vulnerability datasets.

---

# 26. Not Yet Implemented or Requiring Further Validation

The following features are not to be treated as completed merely because they are included in the overall project vision.

| Feature | Status |
|---|---|
| ZIP-based ingestion | Implemented |
| Python parsing | Implemented |
| JavaScript/TypeScript parsing | Implemented |
| Java parsing | Implemented |
| C++ parsing | Implemented |
| Dependency graph | Implemented |
| Structural analysis | Implemented |
| Security rule analysis | Implemented |
| CK-style metric proxies | Implemented |
| ISO-aligned scoring | Implemented |
| Tier 1 deterministic repairs | Implemented |
| LLM-assisted repair suggestions | Implemented for supported cases |
| Sandbox verification pipeline | Implemented |
| Live verification dashboard | Implemented |
| JSON report export | Implemented |
| Dataset generation pipeline | Implemented |
| Cross-language benchmark script | Implemented |
| Four-method comparative repair evaluation | Research extension; completion requires experiment and code verification |
| Full empirical benchmark results | Pending validation |
| Statistical significance analysis | Pending experimental data |
| GitHub URL ingestion | Planned |
| Paste-code input | Planned |
| Clone/duplication detection | Planned |
| Halstead metrics | Planned |
| Maintainability Index | Planned |
| `.c` language support | Planned |
| Threshold cross-validation against non-Java corpora | Ongoing research |
| PostgreSQL session metadata storage | Planned |
| User accounts and analysis history | Planned |

---

# 27. Future Enhancements

The long-term development of Repo-Up includes the following directions.

### Repository ingestion

- GitHub repository URL ingestion.
- Additional archive formats.
- More programming languages.
- Incremental repository analysis.

### Software quality analysis

- Halstead complexity metrics.
- Maintainability Index.
- More advanced class and method-level metrics.
- Improved cross-language metric calibration.
- Advanced dependency and architectural analysis.

### Security analysis

- Expanded vulnerability rule coverage.
- Data-flow analysis.
- Taint analysis.
- Context-sensitive security checks.
- Dependency vulnerability analysis.

### Automated repair

- Expanded repair coverage.
- More sophisticated contextual patch generation.
- Improved patch ranking.
- Multi-file repair support.
- Better behavioral regression detection.

### Research and benchmarking

- Larger real-world repository datasets.
- More vulnerability categories.
- Expanded cross-language evaluation.
- Repeated experiments across model versions.
- Repair-method ablation studies.
- Statistical comparison of repair methods.
- Reproducible benchmark releases.

### Platform development

- PostgreSQL-based session metadata.
- User accounts.
- Historical analysis.
- Repository comparison.
- Continuous integration integration.
- Exportable research reports.

---

# 28. Expected Research Contributions

Repo-Up aims to contribute to software engineering research in several ways.

**Contribution 1: Integrated quality analysis**

A unified framework combining dependency graphs, structural checks, security findings, and object-oriented metric proxies.

**Contribution 2: Quality-aware automated repair**

An approach that evaluates candidate repairs not only by whether a patch can be generated, but also by whether the patch passes verification and changes the repository's quality assessment.

**Contribution 3: Comparative repair evaluation**

A common experimental environment for evaluating four repair approaches under standardized inputs and verification conditions.

**Contribution 4: Isolated patch verification**

A staged verification architecture that checks syntax, static-analysis regressions, security regressions, and available unit tests before accepting a repair.

**Contribution 5: Reproducible research pipeline**

An incremental dataset acquisition and processing pipeline that supports structured result generation while removing temporary downloaded repository copies after successful processing.

**Contribution 6: Cross-language evaluation**

An experimental framework for examining the reliability and applicability of software quality analysis and repair techniques across multiple programming languages.

These are intended contributions. Their novelty and effectiveness must be established through literature comparison and experimental results rather than assumed from implementation alone.

---

# 29. Conclusion

Repo-Up is designed to bridge the gap between software quality assessment and automated program repair.

It begins with complete repository ingestion and syntax-aware analysis, extracts dependency relationships, calculates software quality metrics, identifies structural and security weaknesses, and generates an ISO/IEC 25010-aligned assessment.

Beyond analysis, the system attempts to repair supported findings using deterministic and AI-assisted techniques.

The sandbox verification engine then evaluates candidate modifications through syntax validation, static-analysis regression checks, security regression checks, and unit testing.

The research extension expands this workflow into a controlled comparison of four automated repair methods. Through incremental dataset acquisition, reproducible repository snapshots, standardized verification, and cross-language benchmarking, Repo-Up aims to determine not only whether automated repairs can be generated, but whether they are reliable, safe, and beneficial to software quality.

**The central vision of Repo-Up is to transform repository analysis from a problem-detection process into a measurable, verification-driven software quality improvement process.**
