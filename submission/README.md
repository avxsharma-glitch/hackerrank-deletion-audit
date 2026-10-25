# Northstar Shop: Autonomous Deletion Audit Agent
**HackerRank Orchestrate Challenge: Ghost Data Still Exists**

---

## 1. Executive Overview
Following a $2.4 million compliance and infrastructure failure at Northstar Shop caused by ghost data rehydration and unpurged secondary indexes, this autonomous audit system deterministically verifies whether customer data deletion requests are truly complete.

The agent investigates identity evolutions, audits multimodal and structured evidence across distributed data stores, reconstructs global event timelines up to the audit cutoff, evaluates strict data retention policies, and outputs a topologically sorted remediation DAG.

---

## 2. Core Architecture & Pipeline

The pipeline operates across modular layers to guarantee auditability, zero runtime operational costs, and 100% deterministic reproducibility:

┌────────────────────────────────────────────────────────┐
│ Stage 1: Multilingual Intent Classifier                │
│   - Scans request text (English, Spanish, French)      │
│   - Filters Access, Export, and Opt-out requests       │
│   - Flags non-erasure cases as NOT_APPLICABLE          │
└───────────────────────────┬────────────────────────────┘
│
▼
┌────────────────────────────────────────────────────────┐
│ Stage 2: Canonical Entity Identity Graph Resolver      │
│   - Merges current identity with historical audit logs │
│   - Resolves multi-hop email/phone aliases & UUIDs     │
│   - Prevents circular cycles & identity contamination  │
└───────────────────────────┬────────────────────────────┘
│
▼
┌────────────────────────────────────────────────────────┐
│ Stage 3: Timeline & Dataflow Reconstruction            │
│   - Enforces point-in-time invariant: t <= audit_at    │
│   - Scans SQL snapshots, JSON dumps, logs, and OCR PII │
│   - Detects active CDC/sync jobs and restore vectors   │
└───────────────────────────┬────────────────────────────┘
│
▼
┌────────────────────────────────────────────────────────┐
│ Stage 4: Policy Reconciliation & Step Synthesis        │
│   - Enforces deletion_rules.csv & tombstone invariants │
│   - Synthesizes FINDINGS -> REMEDIATION -> VERIFICATION│
│   - Deterministic topological sort: Phase > Op > Sys   │
└────────────────────────────────────────────────────────┘


---

## 3. Key Design Highlights & Edge-Case Defenses

- **Deterministic & Zero-Cost:** Fully rule-based and reproducible with zero non-deterministic LLM hallucination risk or API runtime latency (~30s execution for 518 cases).
- **Strict Point-in-Time Auditing (`audit_at`):** Reconstructs system states strictly on or before `audit_at`. Any subsequent backup rotations or purge scripts are ignored to prevent future-state data leakage.
- **Tombstone vs. Purge Separation:** Permitted account tombstones allow retaining internal immutable `user_id` values while strictly demanding the purge of direct PII (names, emails, phone numbers, hashes).
- **Dependency-Aware Remediation Ordering:** Remediation actions (`DISABLE_DATA_FLOW`, `BLOCK_RESTORE`) must precede data store purges and cache invalidations to prevent active pipelines from rehydrating deleted records during remediation.

---

## 4. Repository Structure

code/
├── main.py                     # Central CLI orchestrator generating root output.csv
├── config.py                   # System paths and audit thresholds
├── README.md                   # System documentation and setup guide
├── core/
│   ├── intent_classifier.py    # Intent parsing across languages
│   ├── identity_resolver.py    # Multi-hop canonical profile construction
│   ├── evidence_scanner.py     # SQL, JSON, log, and multimodal OCR parser
│   ├── dataflow_auditor.py     # Timeline reconstruction & sync risk auditor
│   └── policy_engine.py        # Deletion rules and permitted field validator
├── synthesis/
│   ├── step_builder.py         # Standardizes Finding, Remediation, and Verification objects
│   └── orderer.py              # Enforces Phase -> Operation -> System -> Resource ordering
└── evaluation/
    ├── evaluate.py             # Metric validator against reference cases
    ├── evaluation_report.md    # Benchmark performance and edge case breakdown
    └── usage_report.md         # Resource and token usage verification


---

## 5. Setup & Execution

### Prerequisites
- Python 3.9+

### Installation
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt  # If requirements.txt is provided, or standard library
```

### Running the Audit Pipeline
From the project root:

```bash
python code/main.py
```

This executes the audit pipeline across all cases in `dataset/deletion_requests.csv` and produces the submission-ready `output.csv`.

### Running Evaluation
```bash
python code/evaluation/evaluate.py
```

---

## 6. Output Schema Compliance

The generated `output.csv` conforms strictly to the problem statement schema:

- **case_id**: Identifier corresponding to each case in `deletion_requests.csv`.
- **deletion_status**: Strictly `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`.
- **steps_json**: Valid serialized JSON array representing ordered audit steps (`[]` for `NOT_APPLICABLE`).
