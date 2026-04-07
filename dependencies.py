"""
FastAPI dependencies for authentication and authorization
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from auth import decode_token, verify_token_type
from database import database
from models import UserRole
import uuid

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Extract and validate current user from JWT token
    Returns user dict with id, email, role, etc.
    """
    token = credentials.credentials
    payload = decode_token(token)
    verify_token_type(payload, "access")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Fetch user from database
    query = """
        SELECT id, email, full_name, role, created_at, last_login, is_active
        FROM users
        WHERE id = :user_id
    """
    user = await database.fetch_one(query=query, values={"user_id": user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return dict(user)


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Ensure user is active"""
    if not current_user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def require_role(*allowed_roles):
    """
    Dependency factory for role-based access control
    Usage: 
        - Depends(require_role(UserRole.TEACHER, UserRole.ADMIN))
        - Depends(require_role("teacher", "admin"))
    """
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role")
        
        # Convert allowed_roles to a list of string values
        # Handle both UserRole enums and plain strings
        allowed_role_values = []
        for role in allowed_roles:
            if isinstance(role, UserRole):
                allowed_role_values.append(role.value)
            elif isinstance(role, str):
                allowed_role_values.append(role)
            elif isinstance(role, list):
                # Handle case where a list is passed as a single argument
                for r in role:
                    if isinstance(r, UserRole):
                        allowed_role_values.append(r.value)
                    else:
                        allowed_role_values.append(r)
        
        if user_role not in allowed_role_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_role_values}"
            )
        
        return current_user
    
    return role_checker


async def get_current_student(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Ensure current user is a student"""
    if current_user.get("role") != UserRole.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required"
        )
    return current_user


async def get_current_teacher(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Ensure current user is a teacher"""
    if current_user.get("role") != UserRole.TEACHER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required"
        )
    return current_user


async def get_current_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Ensure current user is an admin"""
    if current_user.get("role") != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
