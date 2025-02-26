"""
Input validation utilities for ensuring data correctness and security.
"""
import re
import json
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime

class ValidationError(Exception):
    """Exception raised for validation errors."""
    
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class Validator:
    """
    Handles validation of input data against defined schemas.
    """
    
    # Common validation patterns
    PATTERNS = {
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'phone': re.compile(r'^\+?[0-9]{10,15}$'),
        'zipcode': re.compile(r'^\d{5}(-\d{4})?$'),
        'date': re.compile(r'^\d{4}-\d{2}-\d{2}$'),
        'time': re.compile(r'^\d{2}:\d{2}(:\d{2})?$'),
        'url': re.compile(r'^https?://[^\s/$.?#].[^\s]*$'),
        'alpha': re.compile(r'^[a-zA-Z]+$'),
        'alphanumeric': re.compile(r'^[a-zA-Z0-9]+$'),
        'numeric': re.compile(r'^[0-9]+$'),
        'ssn': re.compile(r'^\d{3}-\d{2}-\d{4}$'),
    }
    
    def __init__(self):
        """Initialize the validator."""
        pass
    
    def validate(self, data: Dict[str, Any], schema: Dict[str, Any]) -> List[ValidationError]:
        """
        Validate data against a schema.
        
        Args:
            data: Data to validate
            schema: Validation schema
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for field, rules in schema.items():
            value = data.get(field)
            
            # Check required fields
            if rules.get('required', False) and (value is None or value == ''):
                errors.append(ValidationError(field, "This field is required"))
                continue
            
            # Skip validation if value is None and field is not required
            if value is None:
                continue
            
            # Validate field type
            if 'type' in rules:
                type_error = self._validate_type(field, value, rules['type'])
                if type_error:
                    errors.append(type_error)
                    continue
            
            # Validate string rules
            if rules.get('type') == 'string' and isinstance(value, str):
                errors.extend(self._validate_string(field, value, rules))
            
            # Validate numeric rules
            elif rules.get('type') in ['integer', 'number'] and isinstance(value, (int, float)):
                errors.extend(self._validate_numeric(field, value, rules))
            
            # Validate array rules
            elif rules.get('type') == 'array' and isinstance(value, list):
                errors.extend(self._validate_array(field, value, rules))
            
            # Validate object rules
            elif rules.get('type') == 'object' and isinstance(value, dict):
                errors.extend(self._validate_object(field, value, rules))
            
            # Validate enum
            if 'enum' in rules:
                if value not in rules['enum']:
                    errors.append(ValidationError(
                        field, f"Value must be one of: {', '.join(str(v) for v in rules['enum'])}"
                    ))
            
            # Custom validation
            if 'custom' in rules and callable(rules['custom']):
                try:
                    result = rules['custom'](value)
                    if result is not True:
                        errors.append(ValidationError(field, result or "Failed custom validation"))
                except Exception as e:
                    errors.append(ValidationError(field, str(e)))
        
        return errors
    
    def _validate_type(self, field: str, value: Any, expected_type: str) -> Optional[ValidationError]:
        """Validate value type."""
        if expected_type == 'string' and not isinstance(value, str):
            return ValidationError(field, "Must be a string")
        elif expected_type == 'integer' and not isinstance(value, int):
            return ValidationError(field, "Must be an integer")
        elif expected_type == 'number' and not isinstance(value, (int, float)):
            return ValidationError(field, "Must be a number")
        elif expected_type == 'boolean' and not isinstance(value, bool):
            return ValidationError(field, "Must be a boolean")
        elif expected_type == 'array' and not isinstance(value, list):
            return ValidationError(field, "Must be an array")
        elif expected_type == 'object' and not isinstance(value, dict):
            return ValidationError(field, "Must be an object")
        elif expected_type == 'date' and not self._is_valid_date(value):
            return ValidationError(field, "Must be a valid date (YYYY-MM-DD)")
        return None
    
    def _is_valid_date(self, value: Any) -> bool:
        """Check if value is a valid date."""
        if isinstance(value, datetime):
            return True
        
        if isinstance(value, str):
            try:
                datetime.strptime(value, '%Y-%m-%d')
                return True
            except ValueError:
                pass
        
        return False
    
    def _validate_string(self, field: str, value: str, rules: Dict[str, Any]) -> List[ValidationError]:
        """Validate string rules."""
        errors = []
        
        if 'minLength' in rules and len(value) < rules['minLength']:
            errors.append(ValidationError(
                field, f"Must be at least {rules['minLength']} characters"
            ))
        
        if 'maxLength' in rules and len(value) > rules['maxLength']:
            errors.append(ValidationError(
                field, f"Must be at most {rules['maxLength']} characters"
            ))
        
        if 'pattern' in rules:
            pattern = rules['pattern']
            if isinstance(pattern, str) and pattern in self.PATTERNS:
                if not self.PATTERNS[pattern].match(value):
                    errors.append(ValidationError(
                        field, f"Must be a valid {pattern}"
                    ))
            elif hasattr(pattern, 'match') and not pattern.match(value):
                errors.append(ValidationError(
                    field, "Does not match the required pattern"
                ))
        
        return errors
    
    def _validate_numeric(self, field: str, value: Union[int, float], rules: Dict[str, Any]) -> List[ValidationError]:
        """Validate numeric rules."""
        errors = []
        
        if 'minimum' in rules and value < rules['minimum']:
            errors.append(ValidationError(
                field, f"Must be at least {rules['minimum']}"
            ))
        
        if 'maximum' in rules and value > rules['maximum']:
            errors.append(ValidationError(
                field, f"Must be at most {rules['maximum']}"
            ))
        
        return errors
    
    def _validate_array(self, field: str, value: List[Any], rules: Dict[str, Any]) -> List[ValidationError]:
        """Validate array rules."""
        errors = []
        
        if 'minItems' in rules and len(value) < rules['minItems']:
            errors.append(ValidationError(
                field, f"Must contain at least {rules['minItems']} items"
            ))
        
        if 'maxItems' in rules and len(value) > rules['maxItems']:
            errors.append(ValidationError(
                field, f"Must contain at most {rules['maxItems']} items"
            ))
        
        if 'items' in rules and isinstance(rules['items'], dict):
            item_schema = rules['items']
            for i, item in enumerate(value):
                if 'type' in item_schema:
                    item_field = f"{field}[{i}]"
                    type_error = self._validate_type(item_field, item, item_schema['type'])
                    if type_error:
                        errors.append(type_error)
        
        return errors
    
    def _validate_object(self, field: str, value: Dict[str, Any], rules: Dict[str, Any]) -> List[ValidationError]:
        """Validate object rules."""
        errors = []
        
        if 'properties' in rules:
            nested_errors = self.validate(value, rules['properties'])
            for error in nested_errors:
                errors.append(ValidationError(
                    f"{field}.{error.field}", error.message
                ))
        
        return errors
    
    @classmethod
    def is_valid_email(cls, email: str) -> bool:
        """Check if a string is a valid email address."""
        return bool(cls.PATTERNS['email'].match(email))
    
    @classmethod
    def is_valid_phone(cls, phone: str) -> bool:
        """Check if a string is a valid phone number."""
        return bool(cls.PATTERNS['phone'].match(phone))
    
    @classmethod
    def sanitize_string(cls, value: str) -> str:
        """Sanitize a string by removing potentially harmful characters."""
        if not isinstance(value, str):
            return str(value)
        
        # Remove HTML tags
        value = re.sub(r'<[^>]*>', '', value)
        
        # Remove control characters
        value = re.sub(r'[\x00-\x1F\x7F]', '', value)
        
        return value
    
    @classmethod
    def sanitize_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize all string values in a data dictionary."""
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = cls.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.sanitize_data(item) if isinstance(item, dict)
                    else cls.sanitize_string(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized