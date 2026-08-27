import os
import uuid
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, SessionLocal
from models import User, LoginAttempt

JWT_ALGORITHM = "HS256"
router = APIRouter(prefix="/api/auth", tags=["auth"])


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _secret():
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {"sub": user_id, "email": email, "role": role, "type": "access",
               "exp": datetime.now(timezone.utc) + timedelta(hours=12)}
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = (await db.execute(select(User).where(User.id == payload["sub"]))).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


class LoginRequest(BaseModel):
    email: str
    password: str


def _user_out(user: User):
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response,
                db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    identifier = f"{request.client.host if request.client else 'unknown'}:{email}"
    attempt = (await db.execute(select(LoginAttempt).where(
        LoginAttempt.identifier == identifier))).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if attempt and attempt.locked_until and attempt.locked_until > now:
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        if not attempt:
            attempt = LoginAttempt(identifier=identifier, attempts=0)
            db.add(attempt)
        attempt.attempts += 1
        if attempt.attempts >= 5:
            attempt.locked_until = now + timedelta(minutes=15)
            attempt.attempts = 0
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if attempt:
        attempt.attempts = 0
        attempt.locked_until = None
        await db.commit()
    token = create_access_token(user.id, user.email, user.role)
    response.set_cookie(key="access_token", value=token, httponly=True, secure=True,
                        samesite="none", max_age=43200, path="/")
    return {**_user_out(user), "access_token": token}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return _user_out(user)


async def seed_users():
    accounts = [
        (os.environ.get("OPERATOR_EMAIL", "operator@settlesense.dev"),
         os.environ.get("OPERATOR_PASSWORD", "operator123"), "Finance Operator", "operator"),
        (os.environ.get("REVIEWER_EMAIL", "reviewer@settlesense.dev"),
         os.environ.get("REVIEWER_PASSWORD", "reviewer123"), "Exception Reviewer", "reviewer"),
    ]
    async with SessionLocal() as db:
        for email, password, name, role in accounts:
            email = email.strip().lower()
            existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if existing is None:
                db.add(User(id=f"user_{uuid.uuid4().hex[:10]}", email=email,
                            password_hash=hash_password(password), name=name, role=role))
            elif not verify_password(password, existing.password_hash):
                existing.password_hash = hash_password(password)
        await db.commit()
