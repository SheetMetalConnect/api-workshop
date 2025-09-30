"""
Comprehensive Authentication and Authorization for MES API.

This module provides:
- JWT token validation
- Role-based access control (RBAC)
- Resource-level permissions
- Manufacturing domain-specific security
- API key authentication for machine-to-machine
"""

import os
import jwt
import logging
from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from passlib.context import CryptContext
from pydantic import BaseModel
import redis
from enum import Enum

logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
API_KEY_HEADER_NAME = "X-API-Key"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
security = HTTPBearer()
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)

# Redis for token blacklisting (optional)
try:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True
    )
except Exception:
    redis_client = None
    logger.warning("Redis not available - token blacklisting disabled")


class UserRole(str, Enum):
    """Manufacturing-specific user roles."""
    OPERATOR = "operator"           # Can view and update operations they're assigned to
    SUPERVISOR = "supervisor"       # Can manage operations in their area
    MANAGER = "manager"            # Can manage multiple areas and create operations
    ADMIN = "admin"                # Full system access
    READONLY = "readonly"          # Read-only access to reports and data
    MACHINE = "machine"            # Machine-to-machine access for automation


class Permission(str, Enum):
    """Fine-grained permissions for resources."""
    # Operation permissions
    OPERATION_READ = "operation:read"
    OPERATION_CREATE = "operation:create"
    OPERATION_UPDATE = "operation:update"
    OPERATION_DELETE = "operation:delete"
    OPERATION_TRANSITION = "operation:transition"

    # Batch permissions
    OPERATION_BATCH_UPDATE = "operation:batch_update"

    # Administrative permissions
    USER_MANAGE = "user:manage"
    SYSTEM_CONFIG = "system:config"

    # Reporting permissions
    REPORTS_VIEW = "reports:view"
    ANALYTICS_VIEW = "analytics:view"


class User(BaseModel):
    """User model for authentication."""
    user_id: str
    username: str
    email: Optional[str] = None
    role: UserRole
    workplace_access: List[str] = []  # Workplaces this user can access
    permissions: List[Permission] = []
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None


class TokenData(BaseModel):
    """JWT token payload structure."""
    user_id: str
    username: str
    role: UserRole
    workplace_access: List[str]
    permissions: List[str]
    exp: datetime
    iat: datetime


# Role-based permission mapping
ROLE_PERMISSIONS = {
    UserRole.OPERATOR: [
        Permission.OPERATION_READ,
        Permission.OPERATION_UPDATE,
        Permission.OPERATION_TRANSITION,
    ],
    UserRole.SUPERVISOR: [
        Permission.OPERATION_READ,
        Permission.OPERATION_CREATE,
        Permission.OPERATION_UPDATE,
        Permission.OPERATION_DELETE,
        Permission.OPERATION_TRANSITION,
        Permission.OPERATION_BATCH_UPDATE,
        Permission.REPORTS_VIEW,
    ],
    UserRole.MANAGER: [
        Permission.OPERATION_READ,
        Permission.OPERATION_CREATE,
        Permission.OPERATION_UPDATE,
        Permission.OPERATION_DELETE,
        Permission.OPERATION_TRANSITION,
        Permission.OPERATION_BATCH_UPDATE,
        Permission.REPORTS_VIEW,
        Permission.ANALYTICS_VIEW,
    ],
    UserRole.ADMIN: [permission for permission in Permission],  # All permissions
    UserRole.READONLY: [
        Permission.OPERATION_READ,
        Permission.REPORTS_VIEW,
        Permission.ANALYTICS_VIEW,
    ],
    UserRole.MACHINE: [
        Permission.OPERATION_READ,
        Permission.OPERATION_UPDATE,
        Permission.OPERATION_TRANSITION,
    ],
}


class SecurityManager:
    """Central security management class."""

    def __init__(self):
        self.public_endpoints = {
            "/docs", "/redoc", "/openapi.json", "/health", "/"
        }

    def create_access_token(self, user: User) -> str:
        """Create JWT access token for user."""
        now = datetime.utcnow()
        exp = now + timedelta(hours=JWT_EXPIRATION_HOURS)

        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role.value,
            "workplace_access": user.workplace_access,
            "permissions": [p.value for p in user.permissions],
            "exp": exp.timestamp(),
            "iat": now.timestamp(),
        }

        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        logger.info(f"Access token created for user {user.username}")
        return token

    def verify_token(self, token: str) -> TokenData:
        """Verify and decode JWT token."""
        try:
            # Check if token is blacklisted
            if redis_client and redis_client.get(f"blacklist:{token}"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )

            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

            # Validate expiration
            exp_timestamp = payload.get("exp")
            if not exp_timestamp or datetime.utcnow().timestamp() > exp_timestamp:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )

            return TokenData(
                user_id=payload["user_id"],
                username=payload["username"],
                role=UserRole(payload["role"]),
                workplace_access=payload.get("workplace_access", []),
                permissions=payload.get("permissions", []),
                exp=datetime.fromtimestamp(exp_timestamp),
                iat=datetime.fromtimestamp(payload.get("iat", exp_timestamp))
            )

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

    def blacklist_token(self, token: str):
        """Add token to blacklist (for logout)."""
        if redis_client:
            # Set expiration based on token's remaining lifetime
            try:
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                exp_timestamp = payload.get("exp", 0)
                remaining_seconds = max(0, int(exp_timestamp - datetime.utcnow().timestamp()))

                redis_client.setex(f"blacklist:{token}", remaining_seconds, "revoked")
                logger.info("Token blacklisted successfully")
            except Exception as e:
                logger.error(f"Failed to blacklist token: {str(e)}")

    def get_user_permissions(self, role: UserRole) -> List[Permission]:
        """Get permissions for a user role."""
        return ROLE_PERMISSIONS.get(role, [])

    def has_permission(self, user_permissions: List[str], required_permission: Permission) -> bool:
        """Check if user has required permission."""
        return required_permission.value in user_permissions

    def can_access_workplace(self, user_workplace_access: List[str], workplace: str) -> bool:
        """Check if user can access a specific workplace."""
        # Empty list means access to all workplaces (for admins)
        if not user_workplace_access:
            return True
        return workplace in user_workplace_access


# Global security manager instance
security_manager = SecurityManager()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """Dependency to get current authenticated user from JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required"
        )

    return security_manager.verify_token(credentials.credentials)


async def get_api_key_user(
    api_key: Optional[str] = Depends(api_key_header)
) -> Optional[TokenData]:
    """Dependency for API key authentication (machine-to-machine)."""
    if not api_key:
        return None

    # In a real implementation, validate API key against database
    # For demo purposes, we'll accept a hardcoded key
    valid_api_keys = {
        os.getenv("MACHINE_API_KEY", "demo-machine-key"): {
            "user_id": "machine-001",
            "username": "machine_user",
            "role": UserRole.MACHINE,
            "workplace_access": [],
            "permissions": ROLE_PERMISSIONS[UserRole.MACHINE]
        }
    }

    user_data = valid_api_keys.get(api_key)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return TokenData(
        user_id=user_data["user_id"],
        username=user_data["username"],
        role=user_data["role"],
        workplace_access=user_data["workplace_access"],
        permissions=[p.value for p in user_data["permissions"]],
        exp=datetime.utcnow() + timedelta(hours=24),  # API keys don't expire quickly
        iat=datetime.utcnow()
    )


async def get_current_user_flexible(
    jwt_user: Optional[TokenData] = Depends(get_current_user),
    api_key_user: Optional[TokenData] = Depends(get_api_key_user)
) -> TokenData:
    """Flexible authentication supporting both JWT and API key."""
    if jwt_user:
        return jwt_user
    elif api_key_user:
        return api_key_user
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (JWT token or API key)"
        )


class RequirePermissions:
    """Dependency class for permission-based access control."""

    def __init__(self, required_permissions: List[Permission]):
        self.required_permissions = required_permissions

    def __call__(self, current_user: TokenData = Depends(get_current_user_flexible)) -> TokenData:
        """Check if user has all required permissions."""
        user_permissions = current_user.permissions

        for required_perm in self.required_permissions:
            if not security_manager.has_permission(user_permissions, required_perm):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {required_perm.value}"
                )

        return current_user


class RequireWorkplaceAccess:
    """Dependency class for workplace-based access control."""

    def __init__(self, workplace_param: str = "workplace_name"):
        self.workplace_param = workplace_param

    def __call__(
        self,
        request: Request,
        current_user: TokenData = Depends(get_current_user_flexible)
    ) -> TokenData:
        """Check if user can access the requested workplace."""
        # Extract workplace from request (path params, query params, or body)
        workplace = None

        # Try path parameters first
        if hasattr(request, 'path_params') and self.workplace_param in request.path_params:
            workplace = request.path_params[self.workplace_param]

        # Try query parameters
        if not workplace and hasattr(request, 'query_params'):
            workplace = request.query_params.get(self.workplace_param)

        if workplace and not security_manager.can_access_workplace(
            current_user.workplace_access, workplace
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to workplace: {workplace}"
            )

        return current_user


# Convenience dependencies for common permission combinations
RequireOperationRead = RequirePermissions([Permission.OPERATION_READ])
RequireOperationWrite = RequirePermissions([Permission.OPERATION_CREATE, Permission.OPERATION_UPDATE])
RequireOperationManage = RequirePermissions([Permission.OPERATION_CREATE, Permission.OPERATION_UPDATE, Permission.OPERATION_DELETE])
RequireBatchOperations = RequirePermissions([Permission.OPERATION_BATCH_UPDATE])
RequireAdminAccess = RequirePermissions([Permission.SYSTEM_CONFIG])


def create_demo_token(role: UserRole = UserRole.SUPERVISOR, workplaces: List[str] = None) -> str:
    """Create a demo token for testing purposes."""
    if workplaces is None:
        workplaces = ["LASER_001", "ASSEMBLY_001"]

    demo_user = User(
        user_id=f"demo-{role.value}",
        username=f"demo_{role.value}",
        email=f"demo_{role.value}@company.com",
        role=role,
        workplace_access=workplaces,
        permissions=security_manager.get_user_permissions(role),
        created_at=datetime.utcnow()
    )

    return security_manager.create_access_token(demo_user)


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)