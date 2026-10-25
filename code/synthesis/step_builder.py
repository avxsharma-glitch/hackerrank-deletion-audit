"""
Step Builder Module
Builds ordered steps for findings, remediation, and verification.
"""

from typing import Dict, List, Optional
from enum import Enum


class Phase(Enum):
    """Step phases."""
    FINDING = "FINDING"
    REMEDIATION = "REMEDIATION"
    VERIFICATION = "VERIFICATION"


class StepBuilder:
    """Builds ordered steps for deletion audit results."""
    
    # Operation ordering within each phase (from problem statement)
    OPERATION_ORDER = {
        # Finding operations
        'REPORT_REMAINING_RECORD': 1,
        'REPORT_EXPOSED_PII': 2,
        'REPORT_ACTIVE_DATA_FLOW': 3,
        'REPORT_RESTORE_RISK': 4,
        
        # Remediation operations
        'DISABLE_DATA_FLOW': 1,
        'BLOCK_RESTORE': 2,
        'DELETE_RECORD': 3,
        'REDACT_RECORD': 4,
        'ANONYMIZE_RECORD': 5,
        
        # Verification operations
        'VERIFY_RECORD_ABSENT': 1,
        'VERIFY_RECORD_PRESENT': 2,
        'VERIFY_RECORD_REDACTED': 3,
        'VERIFY_RECORD_ANONYMIZED': 4,
        'VERIFY_DATA_FLOW_DISABLED': 5,
        'VERIFY_RESTORE_BLOCKED': 6,
    }
    
    def __init__(self):
        """Initialize the step builder."""
        self.steps = []
    
    def add_finding(self, operation: str, system_id: str, resource_id: str, 
                    state: str, evidence_id: str) -> None:
        """
        Add a finding step.
        
        Args:
            operation: The operation type
            system_id: The system ID
            resource_id: The resource ID
            state: The state (PRESENT, ACTIVE, etc.)
            evidence_id: The evidence ID (or empty string for proposed steps)
        """
        self.steps.append({
            'phase': Phase.FINDING.value,
            'operation': operation,
            'system_id': system_id,
            'resource_id': resource_id,
            'state': state,
            'evidence_id': evidence_id
        })
    
    def add_remediation(self, operation: str, system_id: str, resource_id: str,
                        state: str) -> None:
        """
        Add a remediation step.
        
        Args:
            operation: The operation type
            system_id: The system ID
            resource_id: The resource ID
            state: The target state (ABSENT, REDACTED, etc.)
        """
        self.steps.append({
            'phase': Phase.REMEDIATION.value,
            'operation': operation,
            'system_id': system_id,
            'resource_id': resource_id,
            'state': state,
            'evidence_id': ""  # Remediation steps have empty evidence_id
        })
    
    def add_verification(self, operation: str, system_id: str, resource_id: str,
                         state: str, evidence_id: str = "") -> None:
        """
        Add a verification step.
        
        Args:
            operation: The operation type
            system_id: The system ID
            resource_id: The resource ID
            state: The expected state
            evidence_id: The evidence ID (or empty for proposed verification)
        """
        self.steps.append({
            'phase': Phase.VERIFICATION.value,
            'operation': operation,
            'system_id': system_id,
            'resource_id': resource_id,
            'state': state,
            'evidence_id': evidence_id
        })
    
    def build_complete_steps(self, verification_steps: List[Dict]) -> List[Dict]:
        """
        Build steps for a COMPLETE case (verification only).
        
        Args:
            verification_steps: List of verification step dicts
            
        Returns:
            Ordered list of steps with step_no
        """
        self.steps = []
        
        for step in verification_steps:
            self.add_verification(
                operation=step['operation'],
                system_id=step['system_id'],
                resource_id=step['resource_id'],
                state=step['state'],
                evidence_id=step.get('evidence_id', '')
            )
        
        return self._order_and_number()
    
    def build_incomplete_steps(self, findings: List[Dict], remediations: List[Dict],
                               verifications: List[Dict]) -> List[Dict]:
        """
        Build steps for an INCOMPLETE case (findings -> remediation -> verification).
        
        Args:
            findings: List of finding step dicts
            remediations: List of remediation step dicts
            verifications: List of verification step dicts
            
        Returns:
            Ordered list of steps with step_no
        """
        self.steps = []
        
        # Add findings
        for finding in findings:
            self.add_finding(
                operation=finding['operation'],
                system_id=finding['system_id'],
                resource_id=finding['resource_id'],
                state=finding['state'],
                evidence_id=finding.get('evidence_id', '')
            )
        
        # Add remediations
        for remediation in remediations:
            self.add_remediation(
                operation=remediation['operation'],
                system_id=remediation['system_id'],
                resource_id=remediation['resource_id'],
                state=remediation['state']
            )
        
        # Add verifications
        for verification in verifications:
            self.add_verification(
                operation=verification['operation'],
                system_id=verification['system_id'],
                resource_id=verification['resource_id'],
                state=verification['state'],
                evidence_id=verification.get('evidence_id', '')
            )
        
        return self._order_and_number()
    
    def _order_and_number(self) -> List[Dict]:
        """
        Order steps by phase, then operation order, then system_id, then resource_id.
        Add step_no to each step.
        
        Returns:
            Ordered list of steps
        """
        # Define phase order
        phase_order = {
            Phase.FINDING.value: 1,
            Phase.REMEDIATION.value: 2,
            Phase.VERIFICATION.value: 3
        }
        
        # Sort steps
        sorted_steps = sorted(
            self.steps,
            key=lambda s: (
                phase_order[s['phase']],
                self.OPERATION_ORDER.get(s['operation'], 999),
                s['system_id'],
                s['resource_id']
            )
        )
        
        # Add step_no
        for i, step in enumerate(sorted_steps, 1):
            step['step_no'] = i
        
        return sorted_steps
    
    def clear(self) -> None:
        """Clear all steps."""
        self.steps = []
