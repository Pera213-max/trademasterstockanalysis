from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import User, get_db
from app.services.auth_service import (
    create_access_token,
    hash_password,
    verify_password,
    get_current_user,
)

router = APIRouter(prefix="/api/auth")


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    username: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    email = request.email.lower().strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address")
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    username = request.username.strip() if request.username else None
    if username == "":
        username = None

    if username:
        existing_username = db.query(User).filter(User.username == username).first()
        if existing_username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(request.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return {
        "success": True,
        "data": {
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
            },
        },
    }


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    email = request.email.lower().strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address")
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    token = create_access_token(user.id)
    return {
        "success": True,
        "data": {
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
            },
        },
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "success": True,
        "data": {
            "id": current_user.id,
            "email": current_user.email,
            "username": current_user.username,
        },
    }
