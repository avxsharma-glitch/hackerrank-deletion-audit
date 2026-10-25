# Ghost Data Still Exists - Deletion Audit Solution

## Overview

This is an autonomous deletion-audit solution for the HackerRank Orchestrate challenge. The system investigates deletion requests to determine whether user data has been truly deleted across all systems, or if "ghost data" still exists.

## Architecture

The solution follows a modular, pipeline-based architecture:

### Core Modules (`code/core/`)

1. **intent_classifier.py** - Classifies user intent from request text
   - Detects deletion vs. non-deletion requests (access, export, marketing opt-out, etc.)
   - Supports multi-language keywords (English, Spanish, French)
   - Returns NOT_APPLICABLE for non-deletion intents

2. **identity_resolver.py** - Resolves canonical user identity
   - Looks up current user identities from `user_identities.csv`
   - Aggregates historical variants from `user_audit_log.csv`
   - Handles multi-hop identity evolution (email changes, phone updates)
   - Returns all identifiers (emails, phones, hashes) for comprehensive audit

3. **evidence_scanner.py** - Scans evidence files for PII
   - Parses SQL snapshots, JSON, logs, text files
   - Supports PDF parsing (pypdf/pdfplumber) with fallback
   - Supports image OCR (pytesseract) with fallback
   - Searches for user identifiers line-by-line

4. **dataflow_auditor.py** - Reconstructs timeline and identifies risks
   - Filters system activities by audit timestamp
   - Identifies active data flows (SYNC, INDEX, EXPORT)
   - Identifies restore risks (BACKUP, RESTORE, ARCHIVE)
   - Checks deletion success/failure from activity logs

5. **policy_engine.py** - Applies deletion rules
   - Loads rules from `deletion_rules.csv`
   - Determines required treatment (DELETE, REDACT, ANONYMIZE, RETAIN)
   - Evaluates rule conditions (legal holds, retention periods, attribution)
   - Checks tombstone compliance (user_id retained, direct identifiers removed)

### Synthesis Modules (`code/synthesis/`)

6. **step_builder.py** - Builds ordered audit steps
   - Adds findings, remediation, and verification steps
   - Follows strict phase ordering (FINDING -> REMEDIATION -> VERIFICATION)
   - Maps findings to appropriate remediation actions
   - Generates verification steps for target state

7. **orderer.py** - Orders steps deterministically
   - Orders by phase, then operation, then system_id, then resource_id
   - Ensures consistent output across runs
   - Adds step_no to each step

### Evaluation Module (`code/evaluation/`)

8. **evaluate.py** - Evaluates results against ground truth
   - Validates output format (518 cases, sorted by case_id)
   - Checks JSON validity
   - Generates evaluation report with metrics
   - Documents synthetic edge test cases and improvements

## Usage

### Installation

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On Unix:
source venv/bin/activate

# Install dependencies
pip install -r code/requirements.txt
```

### Running the Solution

```bash
# From the project root directory
python code/main.py
```

This will:
1. Load all dataset files from `dataset/`
2. Process all 518 deletion requests
3. Generate `output.csv` in the project root

### Running Evaluation

```bash
python code/evaluation/evaluate.py
```

This will:
1. Validate the output format
2. Generate `evaluation/evaluation_report.md`

## Output Format

The solution generates `output.csv` with the following schema:

```csv
case_id,deletion_status,steps_json
case_100,COMPLETE,"[{\"step_no\":1,\"phase\":\"VERIFICATION\",\"system_id\":\"account_service\",\"resource_id\":\"account_001\",\"operation\":\"VERIFY_RECORD_ABSENT\",\"state\":\"ABSENT\",\"evidence_id\":\"evidence_01\"}]"
```

- **case_id**: Unique case identifier
- **deletion_status**: COMPLETE | INCOMPLETE | NOT_APPLICABLE
- **steps_json**: JSON array of ordered steps

### Step Schema

Each step in `steps_json` contains:

```json
{
  "step_no": 1,
  "phase": "FINDING",
  "system_id": "account_service",
  "resource_id": "account_001",
  "operation": "REPORT_REMAINING_RECORD",
  "state": "PRESENT",
  "evidence_id": "evidence_01"
}
```

### Allowed Operations

**Finding Phase:**
- `REPORT_REMAINING_RECORD` - Record that should be deleted still exists
- `REPORT_EXPOSED_PII` - Record contains identifiers that should be redacted
- `REPORT_ACTIVE_DATA_FLOW` - Active process can recreate data
- `REPORT_RESTORE_RISK` - Backup can restore deleted data

**Remediation Phase:**
- `DISABLE_DATA_FLOW` - Stop the data flow
- `BLOCK_RESTORE` - Prevent backup restore
- `DELETE_RECORD` - Remove the entire record
- `REDACT_RECORD` - Remove identifying fields
- `ANONYMIZE_RECORD` - Unlink record from user

**Verification Phase:**
- `VERIFY_RECORD_ABSENT` - Confirm record no longer exists
- `VERIFY_RECORD_PRESENT` - Confirm retained record exists
- `VERIFY_RECORD_REDACTED` - Confirm fields removed
- `VERIFY_RECORD_ANONYMIZED` - Confirm unlinked
- `VERIFY_DATA_FLOW_DISABLED` - Confirm flow inactive
- `VERIFY_RESTORE_BLOCKED` - Confirm restore blocked

## Key Design Decisions

### Deterministic Processing
The solution uses rule-based processing instead of LLM inference to ensure:
- Consistent results across runs
- Fast execution (~30 seconds for 518 cases)
- No external API dependencies
- Minimal operational costs

### Timeline-Aware Evidence
Only evidence captured at or before `audit_at` is considered. This ensures the audit reflects the true state at the time of the audit, not post-audit cleanup.

### Identity Resolution with History
The identity resolver aggregates all historical variants (emails, phones, names) from the audit log to ensure comprehensive coverage of user data across systems.

### Strict Step Ordering
Steps are ordered deterministically by:
1. Phase (FINDING -> REMEDIATION -> VERIFICATION)
2. Operation (per problem statement table)
3. System ID (ascending)
4. Resource ID (ascending)

This ensures consistent output and proper grader compatibility.

## Limitations and Future Improvements

1. **Resource Mapping**: System activity to user resource mapping is heuristic-based. Could be improved with explicit user_id tracking in activity details.

2. **Policy Conditions**: Some rule conditions require external context (legal holds, retention periods). Could be improved with metadata files for these states.

3. **Evidence OCR**: OCR for images is optional and may miss some PII. Could be improved with alternative OCR engines or manual annotation.

4. **Multi-hop Identity**: Current implementation handles single-hop identity changes. Could be extended for complex multi-hop scenarios.

## Dependencies

- pandas >= 2.0.0
- scikit-learn >= 1.3.0

Optional (for enhanced evidence scanning):
- pypdf or pdfplumber (PDF parsing)
- pytesseract (image OCR)
- PIL (image processing)

## File Structure

```
hackerrank-orchestrate-october26/
├── code/
│   ├── __init__.py
│   ├── main.py                 # Orchestration script
│   ├── requirements.txt        # Python dependencies
│   ├── README.md              # This file
│   ├── core/
│   │   ├── __init__.py
│   │   ├── intent_classifier.py
│   │   ├── identity_resolver.py
│   │   ├── evidence_scanner.py
│   │   ├── dataflow_auditor.py
│   │   └── policy_engine.py
│   ├── synthesis/
│   │   ├── __init__.py
│   │   ├── step_builder.py
│   │   └── orderer.py
│   └── evaluation/
│       ├── __init__.py
│       └── evaluate.py
├── dataset/
│   ├── deletion_requests.csv
│   ├── sample_deletion_requests.csv
│   ├── sample_output.csv
│   ├── user_identities.csv
│   ├── user_audit_log.csv
│   ├── system_activity.csv
│   ├── deletion_rules.csv
│   ├── evidence_files.csv
│   └── evidence/
├── evaluation/
│   ├── evaluation_report.md
│   └── usage_report.md
└── output.csv
```

## License

This solution was developed for the HackerRank Orchestrate challenge.
