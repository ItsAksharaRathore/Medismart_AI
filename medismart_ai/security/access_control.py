"""
Role-based access control module for managing user permissions.
"""
from typing import Dict, List, Set, Any, Optional
import logging

logger = logging.getLogger(__name__)

class Role:
    """Represents a user role with specific permissions."""
    
    def __init__(self, name: str, permissions: List[str]):
        """
        Initialize a role.
        
        Args:
            name: The name of the role
            permissions: List of permission identifiers
        """
        self.name = name
        self.permissions = set(permissions)
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if the role has a specific permission.
        
        Args:
            permission: The permission to check
            
        Returns:
            True if the role has the permission, False otherwise
        """
        return permission in self.permissions
    
    def add_permission(self, permission: str):
        """
        Add a permission to the role.
        
        Args:
            permission: The permission to add
        """
        self.permissions.add(permission)
    
    def remove_permission(self, permission: str):
        """
        Remove a permission from the role.
        
        Args:
            permission: The permission to remove
        """
        if permission in self.permissions:
            self.permissions.remove(permission)


class AccessControl:
    """
    Manages role-based access control for the healthcare application.
    """
    
    # Default roles and their permissions
    DEFAULT_ROLES = {
        "admin": [
            "user:create", "user:read", "user:update", "user:delete",
            "patient:create", "patient:read", "patient:update", "patient:delete",
            "record:create", "record:read", "record:update", "record:delete",
            "system:configure"
        ],
        "doctor": [
            "patient:read", "patient:update",
            "record:create", "record:read", "record:update"
        ],
        "nurse": [
            "patient:read",
            "record:read", "record:update"
        ],
        "patient": [
            "patient:read_own",
            "record:read_own"
        ],
        "receptionist": [
            "patient:create", "patient:read", "patient:update",
            "appointment:create", "appointment:read", "appointment:update", "appointment:delete"
        ]
    }
    
    def __init__(self):
        """Initialize the access control system with default roles."""
        self.roles: Dict[str, Role] = {}
        self.user_roles: Dict[str, Set[str]] = {}
        
        # Initialize default roles
        for role_name, permissions in self.DEFAULT_ROLES.items():
            self.roles[role_name] = Role(role_name, permissions)
    
    def assign_role(self, user_id: str, role_name: str):
        """
        Assign a role to a user.
        
        Args:
            user_id: The user ID
            role_name: The role to assign
            
        Raises:
            ValueError: If the role doesn't exist
        """
        if role_name not in self.roles:
            raise ValueError(f"Role '{role_name}' does not exist")
        
        if user_id not in self.user_roles:
            self.user_roles[user_id] = set()
        
        self.user_roles[user_id].add(role_name)
        logger.info(f"Assigned role '{role_name}' to user '{user_id}'")
    
    def revoke_role(self, user_id: str, role_name: str):
        """
        Revoke a role from a user.
        
        Args:
            user_id: The user ID
            role_name: The role to revoke
        """
        if user_id in self.user_roles and role_name in self.user_roles[user_id]:
            self.user_roles[user_id].remove(role_name)
            logger.info(f"Revoked role '{role_name}' from user '{user_id}'")
    
    def create_role(self, role_name: str, permissions: List[str]):
        """
        Create a new role.
        
        Args:
            role_name: The name of the new role
            permissions: List of permissions for the role
            
        Raises:
            ValueError: If the role already exists
        """
        if role_name in self.roles:
            raise ValueError(f"Role '{role_name}' already exists")
        
        self.roles[role_name] = Role(role_name, permissions)
        logger.info(f"Created new role '{role_name}' with permissions: {permissions}")
    
    def has_permission(self, user_id: str, permission: str) -> bool:
        """
        Check if a user has a specific permission.
        
        Args:
            user_id: The user ID
            permission: The permission to check
            
        Returns:
            True if the user has the permission, False otherwise
        """
        if user_id not in self.user_roles:
            return False
        
        for role_name in self.user_roles[user_id]:
            if self.roles[role_name].has_permission(permission):
                return True
        
        return False
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """
        Get all permissions for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            Set of all permissions the user has
        """
        if user_id not in self.user_roles:
            return set()
        
        permissions = set()
        for role_name in self.user_roles[user_id]:
            permissions.update(self.roles[role_name].permissions)
        
        return permissions