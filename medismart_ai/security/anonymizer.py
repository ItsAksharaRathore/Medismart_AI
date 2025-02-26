"""
Data anonymization module for removing or obfuscating personally identifiable information.
"""
import re
import hashlib
import uuid
from typing import Dict, Any, Union, List, Callable, Pattern

class DataAnonymizer:
    """
    Service for anonymizing sensitive healthcare data to protect patient privacy
    while maintaining data utility for analysis.
    """
    
    # Regular expressions for identifying common PII
    PII_PATTERNS = {
        'ssn': re.compile(r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'phone': re.compile(r'\b(\+\d{1,2}\s?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
        'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
        'ip_address': re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
        'date_of_birth': re.compile(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b')
    }
    
    def __init__(self, salt: str = None):
        """
        Initialize the anonymizer with an optional salt for hashing.
        
        Args:
            salt: A string to use as salt for hashing functions
        """
        self.salt = salt or str(uuid.uuid4())
        self.anonymization_map = {}
        
        # Define default anonymization strategies
        self.strategies = {
            'hash': self._hash_value,
            'mask': self._mask_value,
            'redact': self._redact_value,
            'generalize': self._generalize_value,
            'pseudonymize': self._pseudonymize_value
        }
    
    def _hash_value(self, value: str) -> str:
        """Hash a value using SHA-256."""
        return hashlib.sha256(f"{value}{self.salt}".encode()).hexdigest()
    
    def _mask_value(self, value: str) -> str:
        """Mask a value, preserving some characters."""
        if not value or len(value) < 4:
            return "****"
        return value[0] + "*" * (len(value) - 2) + value[-1]
    
    def _redact_value(self, value: str) -> str:
        """Completely redact a value."""
        return "[REDACTED]"
    
    def _generalize_value(self, value: str) -> str:
        """
        Generalize a value (simplified implementation).
        In practice, this would use more sophisticated generalization
        based on the type of data.
        """
        # This is a simplified implementation
        if isinstance(value, str) and value.isdigit():
            # For numeric strings, round to nearest 10
            return str(round(int(value), -1))
        elif len(value) > 5:
            # For longer strings, keep only first character
            return value[0] + "..."
        return "[GENERALIZED]"
    
    def _pseudonymize_value(self, value: str) -> str:
        """Replace value with a pseudonym that maps to the original value."""
        if value not in self.anonymization_map:
            self.anonymization_map[value] = f"ID_{len(self.anonymization_map) + 1}"
        return self.anonymization_map[value]
    
    def anonymize_field(self, field_name: str, value: Any, strategy: str = 'hash') -> Any:
        """
        Anonymize a single field using the specified strategy.
        
        Args:
            field_name: Name of the field
            value: Value to anonymize
            strategy: Anonymization strategy to use
            
        Returns:
            Anonymized value
        """
        if strategy not in self.strategies:
            raise ValueError(f"Unknown anonymization strategy: {strategy}")
        
        if value is None or value == "":
            return value
        
        if isinstance(value, (int, float)):
            value = str(value)
        
        return self.strategies[strategy](value)
    
    def anonymize_data(self, data: Dict[str, Any], field_strategies: Dict[str, str]) -> Dict[str, Any]:
        """
        Anonymize data using specified strategies for different fields.
        
        Args:
            data: Data dictionary to anonymize
            field_strategies: Mapping of field names to anonymization strategies
            
        Returns:
            Anonymized data dictionary
        """
        result = {}
        
        for field, value in data.items():
            if field in field_strategies:
                result[field] = self.anonymize_field(field, value, field_strategies[field])
            else:
                result[field] = value
                
        return result
    
    def detect_and_anonymize_pii(self, text: str) -> str:
        """
        Scan text for PII patterns and anonymize detected patterns.
        
        Args:
            text: Text to scan for PII
            
        Returns:
            Text with PII anonymized
        """
        if not isinstance(text, str):
            return text
            
        for pii_type, pattern in self.PII_PATTERNS.items():
            text = pattern.sub(
                lambda match: self._mask_value(match.group(0)), 
                text
            )
            
        return text
    
    def get_deid_config(self) -> Dict[str, Any]:
        """
        Get the current de-identification configuration.
        
        Returns:
            Dictionary with anonymization configuration
        """
        return {
            "salt": self.salt,
            "strategies": list(self.strategies.keys()),
            "pii_patterns": {k: v.pattern for k, v in self.PII_PATTERNS.items()},
            "pseudonym_count": len(self.anonymization_map)
        }