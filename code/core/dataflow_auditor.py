"""
Dataflow Auditor Module
Reconstructs timeline and identifies active data flows and restore risks.
"""

import pandas as pd
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime
from collections import defaultdict


class DataflowAuditor:
    """Audits system activity for data flows and risks."""
    
    def __init__(self, system_activity_path: str):
        """
        Initialize the dataflow auditor.
        
        Args:
            system_activity_path: Path to system_activity.csv
        """
        self.activity_df = pd.read_csv(system_activity_path)
        self.activity_df['event_time'] = pd.to_datetime(self.activity_df['event_time'])
    
    def get_activities_before(self, audit_at: str, user_id: Optional[str] = None) -> pd.DataFrame:
        """
        Get all activities that occurred before audit_at.
        
        Args:
            audit_at: The audit timestamp
            user_id: Optional user_id to filter by
            
        Returns:
            DataFrame of relevant activities
        """
        audit_dt = pd.to_datetime(audit_at)
        
        # Filter by time
        filtered = self.activity_df[self.activity_df['event_time'] <= audit_dt].copy()
        
        # Filter by user if provided (would need to match on resource_id or details)
        # For now, return all activities before the audit time
        
        return filtered
    
    def find_user_activities(self, activities: pd.DataFrame, resource_ids: Set[str]) -> pd.DataFrame:
        """
        Filter activities to those related to specific resources.
        
        Args:
            activities: DataFrame of activities
            resource_ids: Set of resource IDs to filter by
            
        Returns:
            Filtered DataFrame
        """
        if not resource_ids:
            return pd.DataFrame()
        
        filtered = activities[activities['resource_id'].isin(resource_ids)]
        return filtered
    
    def identify_active_data_flows(self, activities: pd.DataFrame, audit_at: str) -> List[Dict]:
        """
        Identify active data flows that could recreate user data.
        
        Args:
            activities: DataFrame of activities
            audit_at: The audit timestamp
            
        Returns:
            List of active data flow findings
        """
        active_flows = []
        
        # Look for SYNC_RECORD, INDEX_RECORD, EXPORT activities
        sync_events = activities[
            activities['event_type'].isin(['SYNC_RECORD', 'INDEX_RECORD', 'EXPORT_RECORD'])
        ]
        
        for _, row in sync_events.iterrows():
            # Check if the flow is still active (no DISABLE or DELETE after it)
            resource_id = row['resource_id']
            event_time = row['event_time']
            
            # Look for disabling events after this sync
            later_activities = activities[
                (activities['event_time'] > event_time) &
                (activities['event_time'] <= pd.to_datetime(audit_at)) &
                (activities['resource_id'] == resource_id)
            ]
            
            disabling_events = later_activities[
                later_activities['event_type'].isin(['DISABLE_FLOW', 'DELETE_FLOW', 'STOP_SYNC'])
            ]
            
            if disabling_events.empty:
                # Flow is still active
                active_flows.append({
                    'activity_id': row['activity_id'],
                    'system_id': row['source_system'],
                    'resource_id': resource_id,
                    'event_type': row['event_type'],
                    'event_time': event_time,
                    'target_system': row['target_system']
                })
        
        return active_flows
    
    def identify_restore_risks(self, activities: pd.DataFrame, audit_at: str) -> List[Dict]:
        """
        Identify backup/restore risks that could bring deleted data back.
        
        Args:
            activities: DataFrame of activities
            audit_at: The audit timestamp
            
        Returns:
            List of restore risk findings
        """
        restore_risks = []
        
        # Look for BACKUP, RESTORE, ARCHIVE activities
        backup_events = activities[
            activities['event_type'].isin(['BACKUP', 'RESTORE', 'ARCHIVE', 'CREATE_BACKUP'])
        ]
        
        for _, row in backup_events.iterrows():
            resource_id = row['resource_id']
            event_time = row['event_time']
            
            # Check if restore has been blocked
            later_activities = activities[
                (activities['event_time'] > event_time) &
                (activities['event_time'] <= pd.to_datetime(audit_at)) &
                (activities['resource_id'] == resource_id)
            ]
            
            block_events = later_activities[
                later_activities['event_type'].isin(['BLOCK_RESTORE', 'DELETE_BACKUP'])
            ]
            
            if block_events.empty:
                # Restore risk exists
                restore_risks.append({
                    'activity_id': row['activity_id'],
                    'system_id': row['source_system'],
                    'resource_id': resource_id,
                    'event_type': row['event_type'],
                    'event_time': event_time
                })
        
        return restore_risks
    
    def get_deletion_activities(self, activities: pd.DataFrame, resource_ids: Set[str]) -> List[Dict]:
        """
        Get deletion activities for specific resources.
        
        Args:
            activities: DataFrame of activities
            resource_ids: Set of resource IDs
            
        Returns:
            List of deletion activities
        """
        deletions = activities[
            activities['event_type'].isin(['DELETE_RECORD', 'DELETE_ACCOUNT', 'PURGE']) &
            activities['resource_id'].isin(resource_ids)
        ]
        
        return deletions.to_dict('records')
    
    def check_deletion_success(self, activities: pd.DataFrame, resource_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a deletion was successful.
        
        Args:
            activities: DataFrame of activities
            resource_id: Resource ID to check
            
        Returns:
            Tuple of (is_deleted, evidence_activity_id)
        """
        resource_activities = activities[activities['resource_id'] == resource_id]
        
        # Look for successful deletion
        successful_deletions = resource_activities[
            (resource_activities['event_type'].isin(['DELETE_RECORD', 'DELETE_ACCOUNT'])) &
            (resource_activities['reported_result'] == 'SUCCESS')
        ]
        
        if not successful_deletions.empty:
            # Check if it was recreated later
            latest_deletion = successful_deletions.iloc[-1]
            deletion_time = latest_deletion['event_time']
            
            later_activities = resource_activities[resource_activities['event_time'] > deletion_time]
            
            recreation_events = later_activities[
                later_activities['event_type'].isin(['CREATE_RECORD', 'SYNC_RECORD', 'RESTORE'])
            ]
            
            if recreation_events.empty:
                return True, latest_deletion['activity_id']
        
        return False, None
