"""
Step Orderer Module
Orders steps according to the strict phase and operation ordering rules.
"""

from typing import List, Dict


class StepOrderer:
    """Orders steps according to the specification."""
    
    # Phase order
    PHASE_ORDER = {
        'FINDING': 1,
        'REMEDIATION': 2,
        'VERIFICATION': 3
    }
    
    # Operation order within each phase (from problem statement)
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
    
    @classmethod
    def order_steps(cls, steps: List[Dict]) -> List[Dict]:
        """
        Order steps according to the specification.
        
        Ordering rules:
        1. By phase: FINDING -> REMEDIATION -> VERIFICATION
        2. Within phase: by operation order from problem statement
        3. Then by system_id ascending
        4. Then by resource_id ascending
        
        Args:
            steps: List of step dicts
            
        Returns:
            Ordered list of steps with step_no added
        """
        # Sort steps
        sorted_steps = sorted(
            steps,
            key=lambda s: (
                cls.PHASE_ORDER.get(s['phase'], 999),
                cls.OPERATION_ORDER.get(s['operation'], 999),
                s['system_id'],
                s['resource_id']
            )
        )
        
        # Add step_no
        for i, step in enumerate(sorted_steps, 1):
            step['step_no'] = i
        
        return sorted_steps
