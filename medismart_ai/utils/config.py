"""
Configuration manager for handling application settings.
"""
import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, Union, List

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Configuration manager that handles loading, validating, and providing access
    to application configuration.
    """
    
    DEFAULT_CONFIG = {
        "app": {
            "name": "Healthcare App",
            "environment": "development",
            "debug": True,
            "host": "0.0.0.0",
            "port": 5000
        },
        "database": {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "name": "healthcare_db",
            "user": "postgres",
            "password": "",
            "pool_size": 5,
            "max_overflow": 10
        },
        "security": {
            "secret_key": "",
            "token_expiration": 3600,
            "password_min_length": 8,
            "enable_2fa": False,
            "cors_origins": ["http://localhost:3000"]
        },
        "storage": {
            "type": "local",
            "path": "data",
            "max_file_size_mb": 10
        },
        "logging": {
            "level": "info",
            "log_to_file": True,
            "log_to_console": True,
            "json_format": False
        }
    }
    
    def __init__(self, config_path: str = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self.DEFAULT_CONFIG.copy()
        self.config_path = config_path
        
        # Load configuration from file if provided
        if config_path:
            self.load_config(config_path)
        
        # Override with environment variables
        self._override_from_env()
    
    def load_config(self, config_path: str):
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config file format is invalid
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            # Determine file format from extension
            _, ext = os.path.splitext(config_path)
            
            with open(config_path, 'r') as f:
                if ext.lower() == '.json':
                    file_config = json.load(f)
                elif ext.lower() in ['.yaml', '.yml']:
                    file_config = yaml.safe_load(f)
                else:
                    raise ValueError(f"Unsupported configuration file format: {ext}")
            
            # Deep merge loaded config with default config
            self._deep_merge(self.config, file_config)
            
            logger.info(f"Configuration loaded from {config_path}")
        
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            raise
    
    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]):
        """
        Deep merge two dictionaries, modifying the target.
        
        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    def _override_from_env(self):
        """Override configuration with environment variables."""
        prefix = "APP_"
        
        for env_name, env_value in os.environ.items():
            if env_name.startswith(prefix):
                # Convert APP_DATABASE_HOST to ["database", "host"]
                path = env_name[len(prefix):].lower().split("_")
                
                # Navigate to the correct config section
                config_section = self.config
                for part in path[:-1]:
                    if part not in config_section:
                        config_section[part] = {}
                    config_section = config_section[part]
                
                # Set the value, converting to appropriate type
                key = path[-1]
                current_value = config_section.get(key)
                
                if isinstance(current_value, bool):
                    config_section[key] = env_value.lower() in ["true", "1", "yes"]
                elif isinstance(current_value, int):
                    config_section[key] = int(env_value)
                elif isinstance(current_value, float):
                    config_section[key] = float(env_value)
                elif isinstance(current_value, list):
                    config_section[key] = env_value.split(",")
                else:
                    config_section[key] = env_value
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            path: Configuration path (e.g., "database.host")
            default: Default value if path not found
            
        Returns:
            Configuration value or default
        """
        parts = path.split(".")
        value = self.config
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        
        return value
    
    def set(self, path: str, value: Any):
        """
        Set a configuration value using dot notation.
        
        Args:
            path: Configuration path (e.g., "database.host")
            value: Value to set
        """
        parts = path.split(".")
        config_section = self.config
        
        for part in parts[:-1]:
            if part not in config_section:
                config_section[part] = {}
            config_section = config_section[part]
        
        config_section[parts[-1]] = value
    
    def save(self, config_path: str = None):
        """
        Save the current configuration to a file.
        
        Args:
            config_path: Path to save the configuration
            
        Raises:
            ValueError: If file extension is not supported
        """
        save_path = config_path or self.config_path
        if not save_path:
            raise ValueError("No configuration path specified for saving")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Determine file format from extension
        _, ext = os.path.splitext(save_path)
        
        try:
            with open(save_path, 'w') as f:
                if ext.lower() == '.json':
                    json.dump(self.config, f, indent=2)
                elif ext.lower() in ['.yaml', '.yml']:
                    yaml.dump(self.config, f, default_flow_style=False)
                else:
                    raise ValueError(f"Unsupported configuration file format: {ext}")
            
            logger.info(f"Configuration saved to {save_path}")
        
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            raise
    
    def validate(self, schema: Dict[str, Any] = None) -> List[str]:
        """
        Validate the configuration against a schema.
        
        Args:
            schema: Validation schema (if None, no validation is performed)
            
        Returns:
            List of validation errors (empty if valid)
        """
        if not schema:
            return []
        
        # Simple validation implementation
        errors = []
        
        def validate_section(config_section, schema_section, path=""):
            for key, schema_value in schema_section.items():
                current_path = f"{path}.{key}" if path else key
                
                # Check if required key exists
                if isinstance(schema_value, dict) and schema_value.get("required", False):
                    if key not in config_section:
                        errors.append(f"Missing required config: {current_path}")
                        continue
                
                # If key exists, validate type and value
                if key in config_section:
                    value = config_section[key]
                    
                    # Validate type
                    if isinstance(schema_value, dict) and "type" in schema_value:
                        expected_type = schema_value["type"]
                        if expected_type == "string" and not isinstance(value, str):
                            errors.append(f"Config {current_path} should be a string")
                        elif expected_type == "number" and not isinstance(value, (int, float)):
                            errors.append(f"Config {current_path} should be a number")
                        elif expected_type == "boolean" and not isinstance(value, bool):
                            errors.append(f"Config {current_path} should be a boolean")
                        elif expected_type == "array" and not isinstance(value, list):
                            errors.append(f"Config {current_path} should be an array")
                        elif expected_type == "object" and not isinstance(value, dict):
                            errors.append(f"Config {current_path} should be an object")
                    
                    # Validate nested objects
                    if isinstance(schema_value, dict) and "properties" in schema_value:
                        if isinstance(value, dict):
                            validate_section(value, schema_value["properties"], current_path)
        
        validate_section(self.config, schema)
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get the entire configuration as a dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self.config.copy()
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get a configuration section.
        
        Args:
            section: Section name
            
        Returns:
            Section configuration or empty dict if not found
        """
        return self.get(section, {})