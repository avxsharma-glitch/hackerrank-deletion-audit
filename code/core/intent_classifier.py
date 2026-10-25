"""
Intent Classifier Module
Determines if a deletion request is actually requesting deletion or another action.
"""

import re
from typing import Tuple


class IntentClassifier:
    """Classifies user intent from request text."""
    
    # Keywords/phrases that indicate NON-deletion requests
    NON_DELETION_KEYWORDS = [
        # Access requests
        'access', 'retrieve', 'view', 'see my', 'show me', 'get my',
        'download my data', 'export my', 'copy my',
        
        # Marketing opt-out
        'unsubscribe', 'opt out', 'marketing', 'newsletter', 'promotional',
        'stop emails', 'no more emails',
        
        # Rectification/correction
        'correct', 'update', 'change', 'modify', 'fix', 'edit',
        'wrong information', 'incorrect', 'mistake',
        
        # Portability
        'transfer', 'move my data', 'portability',
        
        # Restriction
        'restrict', 'limit', 'stop processing',
        
        # Objection (other than deletion)
        'object to', 'complain', 'dispute',
    ]
    
    # Keywords/phrases that indicate deletion requests (in multiple languages)
    DELETION_KEYWORDS = [
        # English
        'delete', 'deletion', 'remove', 'erase', 'close account',
        'permanently delete', 'delete my account', 'close my account',
        'erase my account', 'remove my account',
        'account deletion', 'account closure',
        
        # Spanish
        'eliminar', 'borrar', 'suprimir', 'cierre', 'eliminar mi cuenta',
        'borrar mi cuenta', 'supresión',
        
        # French
        'supprimer', 'effacer', 'fermer', 'supprimer mon compte',
        'effacer mon compte', 'suppression définitive',
    ]
    
    @classmethod
    def classify(cls, request_text: str) -> Tuple[bool, str]:
        """
        Classify the intent of a deletion request.
        
        Args:
            request_text: The user's request text
            
        Returns:
            Tuple of (is_deletion_intent, reason)
            - is_deletion_intent: True if requesting deletion, False otherwise
            - reason: Explanation of classification
        """
        if not request_text:
            return False, "Empty request text"
        
        text_lower = request_text.lower()
        
        # Check for non-deletion keywords first (these take precedence)
        for keyword in cls.NON_DELETION_KEYWORDS:
            if keyword in text_lower:
                # Check if it's actually a deletion request with secondary mentions
                # e.g., "delete my account and stop marketing emails"
                if any(kw in text_lower for kw in cls.DELETION_KEYWORDS[:5]):  # Check primary deletion keywords
                    return True, "Primary deletion intent detected despite secondary keywords"
                return False, f"Non-deletion intent detected: '{keyword}'"
        
        # Check for deletion keywords
        for keyword in cls.DELETION_KEYWORDS:
            if keyword in text_lower:
                return True, f"Deletion intent detected: '{keyword}'"
        
        # If no clear keywords found, check for general account closure language
        if 'account' in text_lower and ('close' in text_lower or 'remove' in text_lower):
            return True, "Account closure intent detected"
        
        # Default: assume NOT_APPLICABLE if intent is unclear
        return False, "No clear deletion intent detected"
