"""
Authentication and Authorization module for MES API.
"""

from .security import (
    SecurityManager,
    User,
    UserRole,
    Permission,
    TokenData,
    get_current_user,
    get_current_user_flexible,
    RequirePermissions,
    RequireWorkplaceAccess,
    RequireOperationRead,
    RequireOperationWrite,
    RequireOperationManage,
    RequireBatchOperations,
    RequireAdminAccess,
    create_demo_token,
    hash_password,
    verify_password,
    security_manager
)

__all__ = [
    "SecurityManager",
    "User",
    "UserRole",
    "Permission",
    "TokenData",
    "get_current_user",
    "get_current_user_flexible",
    "RequirePermissions",
    "RequireWorkplaceAccess",
    "RequireOperationRead",
    "RequireOperationWrite",
    "RequireOperationManage",
    "RequireBatchOperations",
    "RequireAdminAccess",
    "create_demo_token",
    "hash_password",
    "verify_password",
    "security_manager"
]