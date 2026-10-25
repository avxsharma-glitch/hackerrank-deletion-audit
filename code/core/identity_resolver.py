"""
Identity Resolver Module
Resolves canonical user identity including historical variants.
"""

import pandas as pd
from typing import Dict, List, Set, Optional
from collections import defaultdict


class IdentityResolver:
    """Resolves user identities including historical changes."""
    
    def __init__(self, user_identities_path: str, user_audit_log_path: str):
        """
        Initialize the identity resolver.
        
        Args:
            user_identities_path: Path to user_identities.csv
            user_audit_log_path: Path to user_audit_log.csv
        """
        self.user_identities_df = pd.read_csv(user_identities_path)
        self.user_audit_log_df = pd.read_csv(user_audit_log_path)
        
        # Build identity mappings
        self.email_to_user_id = self._build_email_mapping()
        self.user_id_to_identities = self._build_identity_mapping()
    
    def _build_email_mapping(self) -> Dict[str, str]:
        """Build email to user_id mapping from current identities."""
        mapping = {}
        for _, row in self.user_identities_df.iterrows():
            email = row['email'].lower().strip()
            mapping[email] = row['user_id']
        return mapping
    
    def _build_identity_mapping(self) -> Dict[str, Dict]:
        """
        Build comprehensive identity mapping including historical changes.
        
        Returns:
            Dict mapping user_id to identity information including historical variants
        """
        mapping = defaultdict(lambda: {
            'user_id': None,
            'current_name': None,
            'current_email': None,
            'current_phone': None,
            'current_email_hash': None,
            'historical_emails': set(),
            'historical_phones': set(),
            'historical_names': set(),
            'all_identifiers': set(),
        })
        
        # Add current identities
        for _, row in self.user_identities_df.iterrows():
            user_id = row['user_id']
            mapping[user_id]['user_id'] = user_id
            mapping[user_id]['current_name'] = row['name']
            mapping[user_id]['current_email'] = row['email'].lower()
            mapping[user_id]['current_phone'] = row['phone']
            mapping[user_id]['current_email_hash'] = row['email_hash']
            
            # Add to all identifiers
            mapping[user_id]['historical_emails'].add(row['email'].lower())
            mapping[user_id]['historical_phones'].add(row['phone'])
            mapping[user_id]['historical_names'].add(row['name'])
            mapping[user_id]['all_identifiers'].add(row['email'].lower())
            mapping[user_id]['all_identifiers'].add(row['phone'])
            mapping[user_id]['all_identifiers'].add(row['email_hash'])
        
        # Add historical changes from audit log
        for _, row in self.user_audit_log_df.iterrows():
            user_id = row['user_id']
            field_name = row['field_name']
            old_value = row['old_value']
            new_value = row['new_value']
            
            if field_name == 'email':
                mapping[user_id]['historical_emails'].add(old_value.lower())
                mapping[user_id]['historical_emails'].add(new_value.lower())
                mapping[user_id]['all_identifiers'].add(old_value.lower())
                mapping[user_id]['all_identifiers'].add(new_value.lower())
            elif field_name == 'phone':
                mapping[user_id]['historical_phones'].add(old_value)
                mapping[user_id]['historical_phones'].add(new_value)
                mapping[user_id]['all_identifiers'].add(old_value)
                mapping[user_id]['all_identifiers'].add(new_value)
            elif field_name == 'name':
                mapping[user_id]['historical_names'].add(old_value)
                mapping[user_id]['historical_names'].add(new_value)
        
        return dict(mapping)
    
    def resolve_user(self, email: str) -> Optional[Dict]:
        """
        Resolve a user by email, including historical variants.
        
        Args:
            email: The email address to resolve
            
        Returns:
            Dict containing all identity information, or None if not found
        """
        email_normalized = email.lower().strip()
        
        # Direct lookup
        if email_normalized in self.email_to_user_id:
            user_id = self.email_to_user_id[email_normalized]
            return self._get_identity_dict(user_id)
        
        # Check historical emails
        for user_id, identity in self.user_id_to_identities.items():
            if email_normalized in identity['historical_emails']:
                return self._get_identity_dict(user_id)
        
        return None
    
    def _get_identity_dict(self, user_id: str) -> Dict:
        """Get identity dict for a user_id, converting sets to lists."""
        identity = self.user_id_to_identities[user_id].copy()
        identity['historical_emails'] = list(identity['historical_emails'])
        identity['historical_phones'] = list(identity['historical_phones'])
        identity['historical_names'] = list(identity['historical_names'])
        identity['all_identifiers'] = list(identity['all_identifiers'])
        return identity
    
    def get_all_identifiers(self, email: str) -> Set[str]:
        """
        Get all identifiers (emails, phones, hashes) for a user.
        
        Args:
            email: The email address to look up
            
        Returns:
            Set of all identifier strings
        """
        identity = self.resolve_user(email)
        if identity:
            return set(identity['all_identifiers'])
        return set()
