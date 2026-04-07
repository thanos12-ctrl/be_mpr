"""
Authentication Router
Handles user registration, login, token refresh, and user info
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict
from datetime import datetime
import uuid

from database import database
from auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token, verify_token_type
from dependencies import get_current_user
import models as m


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=m.TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: m.UserCreate):
    """Register a new user (student by default)"""
    
    # Check if email already exists
    query = "SELECT id FROM users WHERE email = :email"
    existing = await database.fetch_one(query=query, values={"email": user_data.email})
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    print(user_data)
    hashed_pwd = hash_password(user_data.password)
    
    # Insert user
    user_id = uuid.uuid4()
    insert_query = """
        INSERT INTO users (id, email, password_hash, full_name, role, created_at, is_active)
        VALUES (:id, :email, :password_hash, :full_name, :role, :created_at, :is_active)
        RETURNING id, email, full_name, role, created_at, last_login, is_active
    """
    
    user = await database.fetch_one(
        query=insert_query,
        values={
            "id": str(user_id),
            "email": user_data.email,
            "password_hash": hashed_pwd,
            "full_name": user_data.full_name,
            "role": user_data.role.value,
            "created_at": datetime.utcnow(),
            "is_active": True
        }
    )
    
    # Create tokens
    access_token = create_access_token({"sub": str(user["id"]), "role": user["role"]})
    refresh_token = create_refresh_token({"sub": str(user["id"])})
    
    return m.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=m.UserResponse(**dict(user))
    )


@router.post("/login", response_model=m.TokenResponse)
async def login(credentials: m.UserLogin):
    """Login and receive JWT tokens"""
    
    # Fetch user
    query = """
        SELECT id, email, password_hash, full_name, role, created_at, last_login, is_active
        FROM users
        WHERE email = :email
    """
    user = await database.fetch_one(query=query, values={"email": credentials.email})
    
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Update last login
    await database.execute(
        query="UPDATE users SET last_login = :now WHERE id = :user_id",
        values={"now": datetime.utcnow(), "user_id": user["id"]}
    )
    
    # Create tokens
    access_token = create_access_token({"sub": str(user["id"]), "role": user["role"]})
    refresh_token = create_refresh_token({"sub": str(user["id"])})
    
    return m.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=m.UserResponse(**{k: v for k, v in dict(user).items() if k != "password_hash"})
    )


@router.post("/refresh", response_model=Dict[str, str])
async def refresh_token_endpoint(token_data: m.TokenRefresh):
    """Refresh access token using refresh token"""
    
    payload = decode_token(token_data.refresh_token)
    verify_token_type(payload, "refresh")
    
    user_id = payload.get("sub")
    
    # Fetch user role
    query = "SELECT role FROM users WHERE id = :user_id AND is_active = TRUE"
    user = await database.fetch_one(query=query, values={"user_id": user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token
    new_access_token = create_access_token({"sub": user_id, "role": user["role"]})
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=m.UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information"""
    return m.UserResponse(**current_user)
