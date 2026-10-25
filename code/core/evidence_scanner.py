"""
Evidence Scanner Module
Parses and scans evidence files for PII and data records.
"""

import os
import json
import sqlite3
import pandas as pd
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path


class EvidenceScanner:
    """Scans evidence files for PII and records."""
    
    def __init__(self, evidence_files_path: str, evidence_dir: str):
        """
        Initialize the evidence scanner.
        
        Args:
            evidence_files_path: Path to evidence_files.csv manifest
            evidence_dir: Base directory for evidence files
        """
        self.evidence_files_df = pd.read_csv(evidence_files_path)
        self.evidence_dir = Path(evidence_dir)
        self.file_cache = {}
    
    def get_file_at_time(self, file_id: str, audit_at: str) -> Optional[Dict]:
        """
        Get evidence file if it was captured before or at audit_at.
        
        Args:
            file_id: The evidence file ID
            audit_at: The audit timestamp
            
        Returns:
            Dict with file info if valid for audit time, None otherwise
        """
        file_info = self.evidence_files_df[self.evidence_files_df['file_id'] == file_id]
        if file_info.empty:
            return None
        
        file_info = file_info.iloc[0].to_dict()
        captured_at = file_info['captured_at']
        
        # Only use evidence captured at or before audit_at
        if captured_at > audit_at:
            return None
        
        return file_info
    
    def scan_file(self, file_id: str, identifiers: Set[str]) -> List[Dict]:
        """
        Scan an evidence file for PII matches.
        
        Args:
            file_id: The evidence file ID
            identifiers: Set of identifiers to search for
            
        Returns:
            List of findings with location and matched identifier
        """
        file_info = self.evidence_files_df[self.evidence_files_df['file_id'] == file_id]
        if file_info.empty:
            return []
        
        file_info = file_info.iloc[0].to_dict()
        file_path = self.evidence_dir / file_info['file_path']
        
        if not file_path.exists():
            return []
        
        findings = []
        file_ext = file_path.suffix.lower()
        
        try:
            if file_ext == '.sql':
                findings.extend(self._scan_sql(file_path, identifiers, file_id))
            elif file_ext == '.json':
                findings.extend(self._scan_json(file_path, identifiers, file_id))
            elif file_ext in ['.log', '.txt']:
                findings.extend(self._scan_text(file_path, identifiers, file_id))
            elif file_ext == '.pdf':
                findings.extend(self._scan_pdf(file_path, identifiers, file_id))
            elif file_ext in ['.png', '.jpg', '.jpeg']:
                findings.extend(self._scan_image(file_path, identifiers, file_id))
        except Exception as e:
            # Log error but continue
            pass
        
        return findings
    
    def _scan_sql(self, file_path: Path, identifiers: Set[str], file_id: str) -> List[Dict]:
        """Scan SQL file for identifiers."""
        findings = []
        
        try:
            # Read SQL content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Search for identifiers in SQL content
            for identifier in identifiers:
                if identifier.lower() in content.lower():
                    findings.append({
                        'file_id': file_id,
                        'type': 'SQL',
                        'identifier': identifier,
                        'location': 'SQL content'
                    })
        except Exception:
            pass
        
        return findings
    
    def _scan_json(self, file_path: Path, identifiers: Set[str], file_id: str) -> List[Dict]:
        """Scan JSON file for identifiers."""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
            
            # Convert to string and search
            content = json.dumps(data).lower()
            
            for identifier in identifiers:
                if identifier.lower() in content:
                    findings.append({
                        'file_id': file_id,
                        'type': 'JSON',
                        'identifier': identifier,
                        'location': 'JSON content'
                    })
        except Exception:
            pass
        
        return findings
    
    def _scan_text(self, file_path: Path, identifiers: Set[str], file_id: str) -> List[Dict]:
        """Scan text/log file for identifiers."""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line_lower = line.lower()
                for identifier in identifiers:
                    if identifier.lower() in line_lower:
                        findings.append({
                            'file_id': file_id,
                            'type': 'TEXT',
                            'identifier': identifier,
                            'location': f'Line {line_num}'
                        })
        except Exception:
            pass
        
        return findings
    
    def _scan_pdf(self, file_path: Path, identifiers: Set[str], file_id: str) -> List[Dict]:
        """Scan PDF file for identifiers."""
        findings = []
        
        try:
            # Try pypdf first
            try:
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                
                for identifier in identifiers:
                    if identifier.lower() in text.lower():
                        findings.append({
                            'file_id': file_id,
                            'type': 'PDF',
                            'identifier': identifier,
                            'location': 'PDF content'
                        })
            except ImportError:
                # Try pdfplumber
                try:
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        text = ""
                        for page in pdf.pages:
                            text += page.extract_text()
                    
                    for identifier in identifiers:
                        if identifier.lower() in text.lower():
                            findings.append({
                                'file_id': file_id,
                                'type': 'PDF',
                                'identifier': identifier,
                                'location': 'PDF content'
                            })
                except ImportError:
                    pass
        except Exception:
            pass
        
        return findings
    
    def _scan_image(self, file_path: Path, identifiers: Set[str], file_id: str) -> List[Dict]:
        """Scan image file for identifiers using OCR."""
        findings = []
        
        try:
            # Try pytesseract OCR
            try:
                from PIL import Image
                import pytesseract
                
                img = Image.open(file_path)
                text = pytesseract.image_to_string(img)
                
                for identifier in identifiers:
                    if identifier.lower() in text.lower():
                        findings.append({
                            'file_id': file_id,
                            'type': 'IMAGE',
                            'identifier': identifier,
                            'location': 'OCR extracted text'
                        })
            except ImportError:
                pass
        except Exception:
            pass
        
        return findings
