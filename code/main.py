"""
Main Orchestration Script
Coordinates all modules to perform deletion audit and generate output.csv
"""

import sys
import os
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Set

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.intent_classifier import IntentClassifier
from core.identity_resolver import IdentityResolver
from core.evidence_scanner import EvidenceScanner
from core.dataflow_auditor import DataflowAuditor
from core.policy_engine import PolicyEngine
from synthesis.step_builder import StepBuilder
from synthesis.orderer import StepOrderer


class DeletionAuditor:
    """Main deletion audit orchestrator."""
    
    def __init__(self, dataset_dir: str):
        """
        Initialize the deletion auditor.
        
        Args:
            dataset_dir: Path to the dataset directory
        """
        self.dataset_dir = Path(dataset_dir)
        
        # Initialize modules
        self.intent_classifier = IntentClassifier()
        self.identity_resolver = IdentityResolver(
            self.dataset_dir / 'user_identities.csv',
            self.dataset_dir / 'user_audit_log.csv'
        )
        self.evidence_scanner = EvidenceScanner(
            self.dataset_dir / 'evidence_files.csv',
            self.dataset_dir / 'evidence'
        )
        self.dataflow_auditor = DataflowAuditor(
            self.dataset_dir / 'system_activity.csv'
        )
        self.policy_engine = PolicyEngine(
            self.dataset_dir / 'deletion_rules.csv'
        )
        self.step_builder = StepBuilder()
        
        # Load deletion requests
        self.requests_df = pd.read_csv(self.dataset_dir / 'deletion_requests.csv')
        
        # Load evidence files manifest
        self.evidence_files_df = pd.read_csv(self.dataset_dir / 'evidence_files.csv')
    
    def audit_case(self, case: Dict) -> Dict:
        """
        Audit a single deletion request case.
        
        Args:
            case: Dict with case information
            
        Returns:
            Dict with case_id, deletion_status, and steps_json
        """
        case_id = case['case_id']
        email = case['email']
        request_text = case['request_text']
        audit_at = case['audit_at']
        
        # Step 1: Intent Classification
        is_deletion_intent, reason = self.intent_classifier.classify(request_text)
        
        if not is_deletion_intent:
            return {
                'case_id': case_id,
                'deletion_status': 'NOT_APPLICABLE',
                'steps_json': '[]'
            }
        
        # Step 2: Identity Resolution
        identity = self.identity_resolver.resolve_user(email)
        
        if not identity:
            # User not found - treat as complete (no data to delete)
            return {
                'case_id': case_id,
                'deletion_status': 'COMPLETE',
                'steps_json': json.dumps([])
            }
        
        identifiers = set(identity['all_identifiers'])
        user_id = identity['user_id']
        
        # Step 3: Get activities before audit_at
        activities = self.dataflow_auditor.get_activities_before(audit_at)
        
        # Step 4: Scan evidence for PII
        evidence_findings = self._scan_evidence(identifiers, audit_at)
        
        # Step 5: Identify issues
        findings = self._identify_findings(activities, evidence_findings, identifiers, user_id, audit_at)
        
        # Step 6: Determine status and build steps
        if not findings:
            # No issues found - COMPLETE
            steps = self._build_verification_steps(identifiers, user_id, audit_at, activities)
            return {
                'case_id': case_id,
                'deletion_status': 'COMPLETE',
                'steps_json': json.dumps(steps)
            }
        else:
            # Issues found - INCOMPLETE
            remediations = self._build_remediations(findings)
            verifications = self._build_verification_steps(identifiers, user_id, audit_at, activities)
            
            steps = self.step_builder.build_incomplete_steps(findings, remediations, verifications)
            return {
                'case_id': case_id,
                'deletion_status': 'INCOMPLETE',
                'steps_json': json.dumps(steps)
            }
    
    def _scan_evidence(self, identifiers: Set[str], audit_at: str) -> List[Dict]:
        """Scan evidence files for PII."""
        findings = []
        
        for _, file_info in self.evidence_files_df.iterrows():
            file_id = file_info['file_id']
            captured_at = file_info['captured_at']
            
            # Only scan evidence captured at or before audit_at
            if captured_at > audit_at:
                continue
            
            file_findings = self.evidence_scanner.scan_file(file_id, identifiers)
            findings.extend(file_findings)
        
        return findings
    
    def _identify_findings(self, activities: pd.DataFrame, evidence_findings: List[Dict],
                          identifiers: Set[str], user_id: str, audit_at: str) -> List[Dict]:
        """Identify findings from activities and evidence."""
        findings = []
        
        # Check for active data flows
        active_flows = self.dataflow_auditor.identify_active_data_flows(activities, audit_at)
        for flow in active_flows:
            findings.append({
                'phase': 'FINDING',
                'operation': 'REPORT_ACTIVE_DATA_FLOW',
                'system_id': flow['system_id'],
                'resource_id': flow['resource_id'],
                'state': 'ACTIVE',
                'evidence_id': flow['activity_id']
            })
        
        # Check for restore risks
        restore_risks = self.dataflow_auditor.identify_restore_risks(activities, audit_at)
        for risk in restore_risks:
            findings.append({
                'phase': 'FINDING',
                'operation': 'REPORT_RESTORE_RISK',
                'system_id': risk['system_id'],
                'resource_id': risk['resource_id'],
                'state': 'ACTIVE',
                'evidence_id': risk['activity_id']
            })
        
        # Check evidence for exposed PII
        for finding in evidence_findings:
            # Map file_id to evidence_id
            findings.append({
                'phase': 'FINDING',
                'operation': 'REPORT_EXPOSED_PII',
                'system_id': self._infer_system_from_file(finding['file_id']),
                'resource_id': finding['file_id'],
                'state': 'PRESENT',
                'evidence_id': finding['file_id']
            })
        
        # Check for remaining records in system activities
        # Look for user-related resources that weren't deleted
        user_resources = self._find_user_resources(activities, user_id)
        for resource in user_resources:
            is_deleted, _ = self.dataflow_auditor.check_deletion_success(activities, resource['resource_id'])
            if not is_deleted:
                findings.append({
                    'phase': 'FINDING',
                    'operation': 'REPORT_REMAINING_RECORD',
                    'system_id': resource['system_id'],
                    'resource_id': resource['resource_id'],
                    'state': 'PRESENT',
                    'evidence_id': resource.get('activity_id', '')
                })
        
        return findings
    
    def _infer_system_from_file(self, file_id: str) -> str:
        """Infer system_id from file_id based on evidence files."""
        file_info = self.evidence_files_df[self.evidence_files_df['file_id'] == file_id]
        if not file_info.empty:
            origin = file_info.iloc[0]['origin']
            # Map origin to system_id
            if 'account' in origin.lower():
                return 'account_service'
            elif 'search' in origin.lower():
                return 'search_service'
            elif 'support' in origin.lower():
                return 'support_platform'
            elif 'analytics' in origin.lower():
                return 'analytics_platform'
            elif 'integration' in origin.lower():
                return 'integration_service'
            elif 'backup' in origin.lower():
                return 'backup_service'
            elif 'security' in origin.lower():
                return 'security_service'
        return 'unknown_system'
    
    def _find_user_resources(self, activities: pd.DataFrame, user_id: str) -> List[Dict]:
        """Find resources related to a user from system activities."""
        resources = []
        
        # Look for activities involving this user's resources
        # This is a simplified approach - in reality, we'd need to match on user_id in details
        user_activities = activities[
            activities['details'].str.contains(user_id, na=False) |
            activities['resource_id'].str.contains(f"account_{user_id.replace('user_', '')}", na=False)
        ]
        
        for _, activity in user_activities.iterrows():
            resources.append({
                'system_id': activity['source_system'],
                'resource_id': activity['resource_id'],
                'activity_id': activity['activity_id']
            })
        
        return resources
    
    def _build_remediations(self, findings: List[Dict]) -> List[Dict]:
        """Build remediation steps from findings."""
        remediations = []
        
        for finding in findings:
            operation = finding['operation']
            system_id = finding['system_id']
            resource_id = finding['resource_id']
            
            # Map finding operation to remediation operation
            if operation == 'REPORT_ACTIVE_DATA_FLOW':
                remediation_op = 'DISABLE_DATA_FLOW'
                target_state = 'DISABLED'
            elif operation == 'REPORT_RESTORE_RISK':
                remediation_op = 'BLOCK_RESTORE'
                target_state = 'BLOCKED'
            elif operation == 'REPORT_REMAINING_RECORD':
                remediation_op = 'DELETE_RECORD'
                target_state = 'ABSENT'
            elif operation == 'REPORT_EXPOSED_PII':
                remediation_op = 'REDACT_RECORD'
                target_state = 'REDACTED'
            else:
                continue
            
            remediations.append({
                'phase': 'REMEDIATION',
                'operation': remediation_op,
                'system_id': system_id,
                'resource_id': resource_id,
                'state': target_state
            })
        
        return remediations
    
    def _build_verification_steps(self, identifiers: Set[str], user_id: str,
                                  audit_at: str, activities: pd.DataFrame) -> List[Dict]:
        """Build verification steps."""
        verifications = []
        
        # Verify account is deleted
        account_resource_id = f"account_{user_id.replace('user_', '')}"
        is_deleted, evidence_id = self.dataflow_auditor.check_deletion_success(activities, account_resource_id)
        
        if is_deleted:
            verifications.append({
                'phase': 'VERIFICATION',
                'operation': 'VERIFY_RECORD_ABSENT',
                'system_id': 'account_service',
                'resource_id': account_resource_id,
                'state': 'ABSENT',
                'evidence_id': evidence_id or ''
            })
        
        # Verify security audit record is retained (per policy)
        verifications.append({
            'phase': 'VERIFICATION',
            'operation': 'VERIFY_RECORD_PRESENT',
            'system_id': 'security_service',
            'resource_id': f"audit_record_{user_id.replace('user_', '')}",
            'state': 'PRESENT',
            'evidence_id': ''
        })
        
        return verifications
    
    def audit_all_cases(self) -> pd.DataFrame:
        """
        Audit all deletion request cases.
        
        Returns:
            DataFrame with results for all cases
        """
        results = []
        
        for _, case in self.requests_df.iterrows():
            result = self.audit_case(case.to_dict())
            results.append(result)
        
        results_df = pd.DataFrame(results)
        
        # Sort by case_id
        results_df = results_df.sort_values('case_id')
        
        return results_df


def main():
    """Main entry point."""
    # Get paths
    script_dir = Path(__file__).parent
    dataset_dir = script_dir.parent / 'dataset'
    output_path = script_dir.parent / 'output.csv'
    
    # Initialize auditor
    auditor = DeletionAuditor(dataset_dir)
    
    # Audit all cases
    print("Auditing deletion requests...")
    results_df = auditor.audit_all_cases()
    
    # Save results
    results_df.to_csv(output_path, index=False)
    
    print(f"Results saved to {output_path}")
    print(f"Total cases processed: {len(results_df)}")
    print(f"Status distribution:")
    print(results_df['deletion_status'].value_counts())


if __name__ == '__main__':
    main()
