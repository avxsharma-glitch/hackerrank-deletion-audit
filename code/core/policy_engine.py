"""
Policy Engine Module
Reconciles deletion rules against records and determines required actions.
"""

import pandas as pd
from typing import Dict, List, Optional, Set
from enum import Enum


class RequiredAction(Enum):
    """Required deletion actions."""
    DELETE = "DELETE"
    REDACT = "REDACT"
    ANONYMIZE = "ANONYMIZE"
    RETAIN = "RETAIN"


class PolicyEngine:
    """Applies deletion rules to determine required treatments."""
    
    def __init__(self, deletion_rules_path: str):
        """
        Initialize the policy engine.
        
        Args:
            deletion_rules_path: Path to deletion_rules.csv
        """
        self.rules_df = pd.read_csv(deletion_rules_path)
        self.rules_map = self._build_rules_map()
    
    def _build_rules_map(self) -> Dict[str, Dict]:
        """Build a map of data_category to rule details."""
        rules_map = {}
        for _, row in self.rules_df.iterrows():
            rules_map[row['data_category']] = {
                'rule_id': row['rule_id'],
                'condition': row['condition'],
                'required_action': RequiredAction(row['required_action'])
            }
        return rules_map
    
    def get_required_action(self, data_category: str, context: Dict) -> RequiredAction:
        """
        Get the required action for a data category based on context.
        
        Args:
            data_category: The category of data
            context: Dict with contextual information (e.g., has_legal_hold, is_tax_record)
            
        Returns:
            RequiredAction enum value
        """
        if data_category not in self.rules_map:
            # Default to DELETE for unknown categories
            return RequiredAction.DELETE
        
        rule = self.rules_map[data_category]
        
        # Check conditions
        condition = rule['condition']
        
        if condition == "Always":
            return rule['required_action']
        
        elif "legal hold" in condition.lower():
            if context.get('has_legal_hold', False):
                return RequiredAction.RETAIN
            return RequiredAction.DELETE
        
        elif "retention period" in condition.lower():
            if context.get('within_retention_period', False):
                return RequiredAction.RETAIN
            return RequiredAction.DELETE
        
        elif "attributable to a user" in condition.lower():
            if context.get('is_attributable', True):
                return rule['required_action']
            return RequiredAction.RETAIN
        
        elif "conversation contains" in condition.lower():
            if context.get('has_context', False):
                return rule['required_action']
            return RequiredAction.DELETE
        
        elif "attachment belongs only" in condition.lower():
            if context.get('belongs_only_to_subject', True):
                return RequiredAction.DELETE
            return RequiredAction.REDACT
        
        elif "restore access can be blocked" in condition.lower():
            if context.get('can_block_restore', True):
                return RequiredAction.RETAIN
            return RequiredAction.DELETE
        
        elif "account is deleted" in condition.lower():
            if context.get('account_deleted', False):
                return rule['required_action']
            return RequiredAction.DELETE
        
        # Default to DELETE if condition not understood
        return RequiredAction.DELETE
    
    def determine_treatment(self, record: Dict, identifiers: Set[str]) -> Dict:
        """
        Determine the required treatment for a record.
        
        Args:
            record: Dict with record information (system_id, resource_id, data_category, content)
            identifiers: Set of user identifiers to check for
            
        Returns:
            Dict with treatment decision and details
        """
        data_category = record.get('data_category', 'UNKNOWN')
        content = record.get('content', '')
        
        # Build context
        context = {
            'has_legal_hold': record.get('has_legal_hold', False),
            'within_retention_period': record.get('within_retention_period', False),
            'is_attributable': self._is_attributable(content, identifiers),
            'has_context': record.get('has_conversation_context', False),
            'belongs_only_to_subject': record.get('belongs_only_to_subject', True),
            'can_block_restore': record.get('can_block_restore', True),
            'account_deleted': record.get('account_deleted', False),
        }
        
        required_action = self.get_required_action(data_category, context)
        
        return {
            'data_category': data_category,
            'required_action': required_action.value,
            'context': context,
            'reason': self._get_reason(data_category, required_action, context)
        }
    
    def _is_attributable(self, content: str, identifiers: Set[str]) -> bool:
        """
        Check if content is attributable to the user based on identifiers.
        
        Args:
            content: The record content
            identifiers: Set of user identifiers
            
        Returns:
            True if attributable, False otherwise
        """
        content_lower = content.lower()
        for identifier in identifiers:
            if identifier.lower() in content_lower:
                return True
        return False
    
    def _get_reason(self, data_category: str, action: RequiredAction, context: Dict) -> str:
        """Generate a reason for the treatment decision."""
        if action == RequiredAction.RETAIN:
            return f"Record retained per policy rule for {data_category}"
        elif action == RequiredAction.DELETE:
            return f"Record must be deleted per policy rule for {data_category}"
        elif action == RequiredAction.REDACT:
            return f"Record must be redacted per policy rule for {data_category}"
        elif action == RequiredAction.ANONYMIZE:
            return f"Record must be anonymized per policy rule for {data_category}"
        return "Unknown treatment"
    
    def check_tombstone_compliance(self, record: Dict, identifiers: Set[str]) -> Dict:
        """
        Check if an account tombstone is compliant (only user_id retained, no direct identifiers).
        
        Args:
            record: Dict with tombstone record info
            identifiers: Set of user identifiers
            
        Returns:
            Dict with compliance status and any exposed identifiers
        """
        content = record.get('content', '')
        exposed_identifiers = []
        
        for identifier in identifiers:
            if identifier.lower() in content.lower():
                # Check if it's just the user_id reference (allowed)
                if identifier.startswith('user_') and identifier in content:
                    continue  # user_id reference is allowed
                exposed_identifiers.append(identifier)
        
        return {
            'is_compliant': len(exposed_identifiers) == 0,
            'exposed_identifiers': exposed_identifiers
        }
