from typing import List, Optional
from app.models.user import UserRole

# Define role hierarchy and permissions
ROLE_HIERARCHY = {
    UserRole.ADMIN: 6,
    UserRole.MANAGER: 5,
    UserRole.STAFF: 4,
    UserRole.SUB_DISTRIBUTOR: 3,
    UserRole.CLUSTER: 2,
    UserRole.OPERATOR: 1
}

# Default permission definitions
PERMISSIONS = {
    # User management
    "users:read": [UserRole.ADMIN, UserRole.MANAGER],
    "users:create": [UserRole.ADMIN],
    "users:update": [UserRole.ADMIN, UserRole.MANAGER],
    "users:delete": [UserRole.ADMIN],
    "users:set_permissions": [UserRole.ADMIN],
    
    # Device management
    "devices:read": [UserRole.ADMIN, UserRole.MANAGER, UserRole.STAFF, UserRole.SUB_DISTRIBUTOR, UserRole.CLUSTER, UserRole.OPERATOR],
    "devices:create": [UserRole.ADMIN, UserRole.MANAGER],
    "devices:update": [UserRole.ADMIN, UserRole.MANAGER],
    "devices:delete": [UserRole.ADMIN],
    
    # Distribution management
    "distributions:read": [UserRole.ADMIN, UserRole.MANAGER, UserRole.STAFF, UserRole.SUB_DISTRIBUTOR, UserRole.CLUSTER, UserRole.OPERATOR],
    "distributions:create": [UserRole.ADMIN, UserRole.MANAGER],
    "distributions:update": [UserRole.ADMIN, UserRole.MANAGER],
    "distributions:delete": [UserRole.ADMIN, UserRole.MANAGER],
    "distributions:approve": [UserRole.ADMIN, UserRole.MANAGER],
    
    # Sub-distribution management
    "sub_distributors:read": [UserRole.ADMIN, UserRole.MANAGER, UserRole.STAFF],
    "sub_distributors:create": [UserRole.ADMIN, UserRole.MANAGER],
    "sub_distributors:update": [UserRole.ADMIN, UserRole.MANAGER],
    "sub_distributors:delete": [UserRole.ADMIN],
    
    # Cluster management
    "clusters:read": [UserRole.ADMIN, UserRole.MANAGER, UserRole.STAFF, UserRole.SUB_DISTRIBUTOR],
    "clusters:create": [UserRole.ADMIN, UserRole.MANAGER, UserRole.SUB_DISTRIBUTOR],
    "clusters:update": [UserRole.ADMIN, UserRole.MANAGER, UserRole.SUB_DISTRIBUTOR],
    "clusters:delete": [UserRole.ADMIN],
    
    # Operator management
    "operators:read": [UserRole.ADMIN, UserRole.MANAGER, UserRole.STAFF, UserRole.SUB_DISTRIBUTOR, UserRole.CLUSTER],
    "operators:create": [UserRole.ADMIN, UserRole.MANAGER, UserRole.CLUSTER],
    "operators:update": [UserRole.ADMIN, UserRole.MANAGER, UserRole.CLUSTER],
    "operators:delete": [UserRole.ADMIN],
    
    # Defect management
    "defects:read": [UserRole.ADMIN, UserRole.MANAGER, UserRole.STAFF, UserRole.SUB_DISTRIBUTOR, UserRole.CLUSTER, UserRole.OPERATOR],
    "defects:create": [UserRole.ADMIN, UserRole.MANAGER, UserRole.STAFF, UserRole.SUB_DISTRIBUTOR, UserRole.CLUSTER, UserRole.OPERATOR],
    "defects:update": [UserRole.ADMIN, UserRole.MANAGER],
    "defects:delete": [UserRole.ADMIN],
    "defects:resolve": [UserRole.ADMIN, UserRole.MANAGER],
    
    # Return management
    "returns:read": [UserRole.ADMIN, UserRole.MANAGER, UserRole.STAFF, UserRole.SUB_DISTRIBUTOR, UserRole.CLUSTER, UserRole.OPERATOR],
    "returns:create": [UserRole.ADMIN, UserRole.MANAGER, UserRole.STAFF, UserRole.SUB_DISTRIBUTOR, UserRole.CLUSTER, UserRole.OPERATOR],
    "returns:update": [UserRole.ADMIN, UserRole.MANAGER],
    "returns:delete": [UserRole.ADMIN, UserRole.MANAGER],
    "returns:approve": [UserRole.ADMIN, UserRole.MANAGER],
    
    # Approval management
    "approvals:read": [UserRole.ADMIN, UserRole.MANAGER],
    "approvals:approve": [UserRole.ADMIN, UserRole.MANAGER],
    "approvals:reject": [UserRole.ADMIN, UserRole.MANAGER],
    
    # Reports
    "reports:read": [UserRole.ADMIN, UserRole.MANAGER],
    "reports:export": [UserRole.ADMIN, UserRole.MANAGER],
    
    # Dashboard
    "dashboard:read": [UserRole.ADMIN, UserRole.MANAGER, UserRole.STAFF, UserRole.SUB_DISTRIBUTOR, UserRole.CLUSTER, UserRole.OPERATOR],
    
    # Notifications
    "notifications:read": [UserRole.ADMIN, UserRole.MANAGER, UserRole.STAFF, UserRole.SUB_DISTRIBUTOR, UserRole.CLUSTER, UserRole.OPERATOR],
}


def check_permission(user_role: str, permission: str, user_permissions: dict = None) -> bool:
    """Check if a user role has a specific permission.
    If user has custom permissions set by admin, those override defaults."""
    # Admin always has all permissions
    if user_role == "admin":
        return True
    
    # Check custom user-level permissions if set
    if user_permissions and permission in user_permissions:
        return user_permissions[permission]
    
    # Fall back to role-based defaults
    try:
        role = UserRole(user_role)
        allowed_roles = PERMISSIONS.get(permission, [])
        return role in allowed_roles
    except ValueError:
        return False


def get_user_permissions(user_role: str) -> List[str]:
    """Get all permissions for a user role"""
    permissions = []
    try:
        role = UserRole(user_role)
        for perm, roles in PERMISSIONS.items():
            if role in roles:
                permissions.append(perm)
    except ValueError:
        pass
    return permissions


def is_higher_role(role1: str, role2: str) -> bool:
    """Check if role1 is higher than role2 in hierarchy"""
    try:
        r1 = UserRole(role1)
        r2 = UserRole(role2)
        return ROLE_HIERARCHY.get(r1, 0) > ROLE_HIERARCHY.get(r2, 0)
    except ValueError:
        return False


def can_manage_user(manager_role: str, target_role: str) -> bool:
    """Check if a manager can manage a target user based on role hierarchy"""
    return is_higher_role(manager_role, target_role)


def get_viewable_roles(user_role: str) -> List[UserRole]:
    """Get roles that a user can view based on their role"""
    try:
        role = UserRole(user_role)
        user_level = ROLE_HIERARCHY.get(role, 0)
        return [r for r, level in ROLE_HIERARCHY.items() if level <= user_level]
    except ValueError:
        return []
