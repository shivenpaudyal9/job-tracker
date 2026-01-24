"""
Authentication Router
Handles user registration, login, and profile management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.models import User
from app.auth import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_DAYS
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterResponse(BaseModel):
    message: str
    user: UserResponse
    access_token: str
    token_type: str = "bearer"


class ProfileUpdate(BaseModel):
    name: Optional[str] = None


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Validate password
    if len(data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )

    # Create user
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        name=data.name,
        created_at=datetime.now(timezone.utc)
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Create access token (sub must be string for JWT)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    )

    return RegisterResponse(
        message="Registration successful",
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            is_outlook_connected=user.is_outlook_connected,
            created_at=user.created_at
        ),
        access_token=access_token
    )


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password
    Returns JWT access token
    """
    user = authenticate_user(db, data.email, data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    # Create access token (sub must be string for JWT)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    )

    return Token(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            is_outlook_connected=user.is_outlook_connected,
            created_at=user.created_at
        )
    )


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user profile
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        is_outlook_connected=current_user.is_outlook_connected,
        created_at=current_user.created_at
    )


@router.patch("/me", response_model=UserResponse)
def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user profile
    """
    if data.name is not None:
        current_user.name = data.name

    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        is_outlook_connected=current_user.is_outlook_connected,
        created_at=current_user.created_at
    )


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """
    Logout - client should discard token
    Server-side we could blacklist token if needed
    """
    return {"message": "Logged out successfully"}
