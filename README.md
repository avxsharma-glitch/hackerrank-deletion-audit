# Ghost Data Still Exists

### HackerRank Orchestrate · October 2026

**An evidence-driven approach to auditing personal-data deletion across distributed systems.**

A system saying *“Deletion Complete”* does not guarantee that the data is actually gone. Records may survive in database replicas, application logs, exports, support attachments, search indexes, archives, or backups. Worse, synchronization and restoration processes can bring deleted data back.

This project tackles that problem by analyzing deletion requests and supporting evidence to determine whether deletion is applicable, whether it can be verified, and what actions are needed to resolve any remaining gaps.

---

## Problem Statement

The challenge is to build an agent that audits personal-data deletion requests using the supplied dataset and evidence files.

For every request, the solution must:

- Determine whether a deletion was actually requested and is applicable.
- Resolve the relevant user identity, including historical identity changes.
- Assess the resource state at the specified `audit_at` timestamp.
- Identify remaining data and potential data recreation risks.
- Apply the supplied deletion rules to relevant data categories.
- Generate ordered findings, remediation actions, and verification steps.
- Produce one valid prediction row per request in `output.csv`.

The central challenge is distinguishing a **reported successful operation** from a deletion that is actually supported by evidence.

## Solution Approach

My approach is to treat deletion auditing as an evidence and state-reconstruction problem rather than trusting workflow status labels.

### 1. Request Applicability

I first determine whether a request represents an applicable deletion under the challenge contract. Requests that do not qualify are assigned `NOT_APPLICABLE`, with an empty steps array.

### 2. Identity Resolution

Current identity records and historical audit logs provide the context needed to associate requests with the correct user identifiers. This is important when identifiers have changed over time.

### 3. Evidence Analysis

The solution uses the supplied activity records, deletion rules, evidence manifest, and supporting evidence files to investigate the relevant resources. Evidence may include database snapshots, SQL exports, logs, JSON files, documents, and images.

### 4. Resource-State Assessment

The audit must evaluate the available evidence in relation to `audit_at`. A workflow status or operation result is treated as a claim, not automatic proof that the data was deleted.

### 5. Policy Evaluation

Relevant resources are checked against the deletion requirements for their data categories. Remaining copies, inconsistent replicas, unresolved retention requirements, and insufficient verification can prevent a deletion from being considered complete.

### 6. Remediation and Verification

When a deletion remains incomplete, the output describes the required remediation and subsequent verification steps in the order specified by the challenge.

### 7. Structured Output

Finally, the solution generates `output.csv` and validates its structure, row coverage, status values, JSON arrays, evidence references, step numbering, and ordering.

---

## Deletion Statuses

| Status           | Interpretation                                                                                                                        |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `COMPLETE`       | Available evidence establishes that the applicable deletion requirements are satisfied and required verification checks pass.         |
| `INCOMPLETE`     | Deletion is applicable, but remaining data, unresolved requirements, recreation risks, or insufficient evidence prevent confirmation. |
| `NOT_APPLICABLE` | The request does not qualify for an applicable deletion under the challenge rules. `steps_json` must be `[]`.                         |

**Important:** A workflow reporting `Complete` is not enough to establish `COMPLETE`. The decision must be supported by the available evidence and evaluated against the relevant audit time.

## Dataset

The challenge provides the following files:

| File                           | Purpose                                                     |
| ------------------------------ | ----------------------------------------------------------- |
| `deletion_requests.csv`        | The 518 requests requiring predictions                      |
| `sample_deletion_requests.csv` | Sample requests for development and testing                 |
| `sample_output.csv`            | Reference answers and expected output structure             |
| `user_identities.csv`          | Current user identity records                               |
| `user_audit_log.csv`           | Historical identity changes                                 |
| `system_activity.csv`          | System operations and data-process activity                 |
| `deletion_rules.csv`           | Required treatment for data categories                      |
| `evidence_files.csv`           | Manifest of available evidence files                        |
| `evidence/`                    | Supporting logs, documents, images, JSON, and SQL snapshots |
| `output.csv`                   | Blank reference template                                    |

The solution must answer every request in `deletion_requests.csv`. The other files provide evidence and context for making those decisions.

## Output Format

The final output is written to `output.csv` in the repository root.

Required header:

```csv
case_id,deletion_status,steps_json
```

### Output requirements

- Exactly 518 data rows, plus the header.
- One prediction per request.
- Rows sorted by `case_id`.
- Only the permitted deletion status values.
- A valid JSON array in every `steps_json` field.
- Consecutive step numbers starting at `1`.
- Findings before remediation, and remediation before verification.
- Required operation ordering, followed by sorting on `system_id` and `resource_id` within each phase.
- Valid evidence identifiers for evidence-backed findings.
- An empty `evidence_id` (`""`) for proposed remediation and future verification steps.
- An empty array (`[]`) for every `NOT_APPLICABLE` request.

The exact step schema must follow `problem_statement.md` and `sample_output.csv`.

## Project Structure

```text
hackerrank-deletion-audit/
├── AGENTS.md
├── README.md
├── log.txt
├── output.csv
├── code/
│   ├── main.py
│   └── evaluation/
│       ├── evaluation_report.md
│       └── usage_report.md
└── dataset/
    ├── deletion_requests.csv
    ├── sample_deletion_requests.csv
    ├── sample_output.csv
    ├── user_identities.csv
    ├── user_audit_log.csv
    ├── system_activity.csv
    ├── deletion_rules.csv
    ├── evidence_files.csv
    └── evidence/
```

*Note: The dataset is supplied separately and must not be included in `code.zip`.*

## Getting Started

### Prerequisites

- Python 3
- The challenge repository and its supplied dataset
- Any additional dependencies required by the implementation

### Run the solution

Run the following command from the repository root:

```bash
python3 code/main.py
```

On Windows:

```powershell
python code/main.py
```

After execution, check that `output.csv` exists in the repository root and contains the expected predictions.

If additional packages are required, install them using the dependency instructions provided by the implementation.

## Evaluation Strategy

The solution should be evaluated at multiple levels rather than relying on status accuracy alone.

| Evaluation area           | What to check                                                     |
| ------------------------- | ----------------------------------------------------------------- |
| Case accuracy             | Whether each deletion status matches the expected result          |
| Row accuracy              | Whether all 518 requests are covered exactly once                 |
| Field accuracy            | Whether required output fields contain valid values               |
| Sequence accuracy         | Whether steps follow the required numbering and phase order       |
| Identity resolution       | Whether historical identifiers are handled correctly              |
| Evidence accuracy         | Whether findings reference valid and relevant evidence            |
| Residual-data detection   | Whether remaining data and inconsistent replicas are identified   |
| Recreation-risk detection | Whether relevant synchronization and restore risks are identified |

### Evaluation reports

The submission includes two required reports:

**`code/evaluation/evaluation_report.md`**

Documents the evaluation methodology, measured case/row/field/sequence accuracy, at least three additional test cases, failures discovered, and improvements made.

**`code/evaluation/usage_report.md`**

Documents the final full-dataset run, model providers and names where applicable, model-call counts, input/output tokens, total and average tokens per request, and estimated costs. If the implementation uses no language model, the report explicitly states that no model calls or model-token costs were incurred.

All reported metrics and usage figures must come from actual execution and evaluation results.

## Submission Packaging

The HackerRank submission requires three main artifacts:

| Artifact          | Contents                                                                                     |
| ----------------- | -------------------------------------------------------------------------------------------- |
| `code.zip`        | Runnable source code, README, prompts/configuration where applicable, and evaluation reports |
| `output.csv`      | Predictions for all 518 deletion requests                                                    |
| `chat_transcript` | The `log.txt` generated by the coding agent                                                  |

### Create `code.zip`

From the repository root on Linux or macOS:

```bash
zip -r code.zip README.md code \
  -x "*/__pycache__/*" \
     "*/.venv/*" \
     "*/venv/*" \
     "*/node_modules/*" \
     "*/.git/*" \
     "*/.DS_Store" \
     "*.zip" "*.tar" "*.gz" "*.tgz" "*.7z" "*.rar"
```

On Windows PowerShell:

```powershell
Compress-Archive -Path README.md, code -DestinationPath code.zip -Force
```

Do not include the dataset, virtual environments, build caches, credentials, or nested archives. Upload `log.txt` separately as the `chat_transcript` submission.

## Final Validation Checklist

Before submitting, verify that:

- [x] `python3 code/main.py` runs from the repository root.
- [x] `output.csv` has the exact required header.
- [x] All 518 requests have exactly one output row.
- [x] Rows are sorted by `case_id`.
- [x] Every `steps_json` value parses as a JSON array.
- [x] Step numbering and ordering follow the challenge contract.
- [x] Evidence references are valid and support the associated findings.
- [x] Both evaluation reports are present and contain actual results.
- [x] `code.zip` contains the runnable code and required documentation.
- [x] `log.txt` follows the required transcript format and is submitted separately.
- [x] No API keys, credentials, or sensitive configuration values are included.

## Conclusion

This project focuses on a critical gap in data deletion workflows: the difference between a deletion being reported as complete and the available evidence actually establishing that it is complete.

By combining identity history, system activity, deletion policies, and supporting evidence, the solution aims to make deletion assessments more traceable and actionable, while identifying unresolved data and recreation risks that require further investigation.

---

**Challenge:** HackerRank Orchestrate — October 2026
**Repository:** `hackerrank-deletion-audit`
**Entry point:** `code/main.py`
**Prediction file:** `output.csv`
