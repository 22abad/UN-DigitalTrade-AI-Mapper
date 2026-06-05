"""JWT authentication — register, login, and request guard.

Endpoints (registered in main.py):
    POST /auth/register  →  create user, return token
    POST /auth/login     →  verify password, return token

Guard:
    get_current_user  →  FastAPI Depends() that validates Bearer token
"""

from __future__ import annotations

import logging
import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

# ── Lazy imports (keep startup fast if optional deps missing) ─────────────────

def _bcrypt_lib():
    try:
        import bcrypt
        return bcrypt
    except ImportError as e:
        raise RuntimeError("bcrypt not installed. `pip install bcrypt`") from e


def _jose():
    try:
        from jose import JWTError, jwt
        return jwt, JWTError
    except ImportError as e:
        raise RuntimeError("python-jose not installed. `pip install python-jose[cryptography]`") from e


# ── Config ────────────────────────────────────────────────────────────────────

_ALGORITHM = "HS256"

def _secret() -> str:
    s = os.getenv("JWT_SECRET", "")
    if not s:
        raise RuntimeError("JWT_SECRET env var is not set.")
    return s

def _expire_hours() -> int:
    return int(os.getenv("JWT_EXPIRE_HOURS", "8"))
_bearer = HTTPBearer(auto_error=True)


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    email: str
    role: str


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    b = _bcrypt_lib()
    return b.hashpw(plain.encode(), b.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    b = _bcrypt_lib()
    return b.checkpw(plain.encode(), hashed.encode())


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(user_id: str, role: str, username: str) -> str:
    secret = _secret()
    jwt, _ = _jose()
    expire = datetime.now(timezone.utc) + timedelta(hours=_expire_hours())
    return jwt.encode({"sub": user_id, "role": role, "username": username, "exp": expire}, secret, algorithm=_ALGORITHM)


def _decode_token(token: str) -> dict[str, Any]:
    secret = _secret()
    jwt, JWTError = _jose()
    try:
        return jwt.decode(token, secret, algorithms=[_ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# ── DB helpers ────────────────────────────────────────────────────────────────

def _db_connect():
    import psycopg2
    url = os.getenv("DATABASE_URL")
    if url:
        return psycopg2.connect(url)
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "rdtii"),
        user=os.getenv("POSTGRES_USER", "rdtii_user"),
        password=os.getenv("POSTGRES_PASSWORD", "rdtii_password"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5433"),
    )


def get_user_by_email(email: str) -> dict | None:
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, email, role, password_hash, is_active "
                "FROM users WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {"id": str(row[0]), "username": row[1], "email": row[2],
            "role": row[3], "password_hash": row[4], "is_active": row[5]}


def create_user(username: str, email: str, password_hash: str) -> dict:
    import psycopg2
    with _db_connect() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO users (username, email, password_hash, role) "
                    "VALUES (%s, %s, %s, 'viewer') RETURNING id, username, email, role",
                    (username, email, password_hash),
                )
                row = cur.fetchone()
                conn.commit()
            except psycopg2.errors.UniqueViolation:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email or username already registered.",
                )
    return {"id": str(row[0]), "username": row[1], "email": row[2], "role": row[3]}


def update_last_login(user_id: str) -> None:
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,)
            )
            conn.commit()


# ── Reset-token DB helpers ────────────────────────────────────────────────────

_RESET_TOKEN_TTL_MINUTES = int(os.getenv("RESET_TOKEN_TTL_MINUTES", "60"))


def create_reset_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=_RESET_TOKEN_TTL_MINUTES)
    with _db_connect() as conn:
        with conn.cursor() as cur:
            # Invalidate any existing unused tokens for this user
            cur.execute(
                "UPDATE password_reset_tokens SET used = TRUE "
                "WHERE user_id = %s AND used = FALSE",
                (user_id,),
            )
            cur.execute(
                "INSERT INTO password_reset_tokens (user_id, token, expires_at) "
                "VALUES (%s, %s, %s)",
                (user_id, token, expires_at),
            )
            conn.commit()
    return token


def consume_reset_token(token: str) -> str:
    """Validate token and return user_id; raises 400 if invalid/expired/used."""
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, expires_at, used "
                "FROM password_reset_tokens WHERE token = %s",
                (token,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="Invalid reset token.")
            user_id, expires_at, used = str(row[0]), row[1], row[2]
            if used:
                raise HTTPException(status_code=400, detail="Reset token has already been used.")
            if expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="Reset token has expired.")
            cur.execute(
                "UPDATE password_reset_tokens SET used = TRUE WHERE token = %s",
                (token,),
            )
            conn.commit()
    return user_id


def update_password_hash(user_id: str, new_hash: str) -> None:
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (new_hash, user_id),
            )
            conn.commit()


# ── Email sender ──────────────────────────────────────────────────────────────

def send_reset_email(to_email: str, token: str) -> None:
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    reset_link = f"{frontend_url}/reset-password?token={token}"

    smtp_host = os.getenv("SMTP_HOST", "")
    if not smtp_host:
        # Dev fallback: log the link instead of sending
        logging.warning("SMTP_HOST not set — reset link: %s", reset_link)
        return

    msg = MIMEText(
        f"Click the link below to reset your SENTINEL password.\n\n"
        f"{reset_link}\n\n"
        f"This link expires in {_RESET_TOKEN_TTL_MINUTES} minutes. "
        f"If you did not request this, ignore this email.",
        "plain",
    )
    msg["Subject"] = "SENTINEL — Reset your password"
    msg["From"] = os.getenv("SMTP_FROM", smtp_host)
    msg["To"] = to_email

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        if smtp_user:
            server.login(smtp_user, smtp_pass)
        server.sendmail(msg["From"], [to_email], msg.as_string())


# ── FastAPI route handlers (mounted in main.py) ───────────────────────────────

async def register(req: RegisterRequest) -> TokenResponse:
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    hashed = hash_password(req.password)
    user = create_user(req.username, req.email, hashed)
    token = create_access_token(user["id"], user["role"], user["username"])
    return TokenResponse(access_token=token, user_id=user["id"],
                         username=user["username"], email=user["email"], role=user["role"])


async def login(req: LoginRequest) -> TokenResponse:
    user = get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled.")
    update_last_login(user["id"])
    token = create_access_token(user["id"], user["role"], user["username"])
    return TokenResponse(access_token=token, user_id=user["id"],
                         username=user["username"], email=user["email"], role=user["role"])


async def forgot_password(req: ForgotPasswordRequest) -> dict:
    user = get_user_by_email(req.email)
    if user:
        token = create_reset_token(user["id"])
        send_reset_email(req.email, token)
    # Always return 200 to avoid leaking whether email is registered
    return {"detail": "If that email is registered, a reset link has been sent."}


async def reset_password(req: ResetPasswordRequest) -> dict:
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    user_id = consume_reset_token(req.token)
    update_password_hash(user_id, hash_password(req.new_password))
    return {"detail": "Password updated successfully."}


# ── Request guard ─────────────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict[str, Any]:
    """FastAPI dependency — validates Bearer JWT, returns {user_id, role}."""
    payload = _decode_token(credentials.credentials)
    return {"user_id": payload["sub"], "role": payload["role"], "username": payload.get("username", "")}
