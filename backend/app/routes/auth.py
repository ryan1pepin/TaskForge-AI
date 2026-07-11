from typing import Optional
import secrets
from datetime import datetime, timezone, timedelta
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db import get_db_session
from app.models import User, RefreshToken
from app.schemas import UserRegister, UserLogin, TokenResponse
from app.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

def hash_token(token: str) -> str:
    """Helper to compute SHA256 hash of a token string for secure DB lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegister, 
    response: Response, 
    db: AsyncSession = Depends(get_db_session)
):
    # Check if user already exists
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )

    # Create new user
    hashed_pwd = hash_password(payload.password)
    new_user = User(email=payload.email, password_hash=hashed_pwd)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Issue access & refresh tokens
    access_token = create_access_token(user_id=str(new_user.id))
    raw_refresh = secrets.token_urlsafe(32)
    refresh_hash = hash_token(raw_refresh)
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    db_refresh_token = RefreshToken(
        user_id=new_user.id,
        token_hash=refresh_hash,
        expires_at=expires_at
    )
    db.add(db_refresh_token)
    await db.commit()

    # Set HTTP-only Cookie for refresh token
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production (requires HTTPS)
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    )

    return TokenResponse(access_token=access_token)

@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLogin, 
    response: Response, 
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user or not verify_password(user.password_hash, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Issue access & refresh tokens
    access_token = create_access_token(user_id=str(user.id))
    raw_refresh = secrets.token_urlsafe(32)
    refresh_hash = hash_token(raw_refresh)
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=expires_at
    )
    db.add(db_refresh_token)
    await db.commit()

    # Set HTTP-only Cookie
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        samesite="lax",
        secure=False,  # False for local HTTP dev
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    )

    return TokenResponse(access_token=access_token)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db_session)
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing"
        )

    token_hash = hash_token(refresh_token)
    
    # Query database for the refresh token
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    result = await db.execute(stmt)
    db_token = result.scalars().first()

    if not db_token:
        # Token not found
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Replay Attack Detection: If token is already revoked, revoke ALL active tokens for that user!
    if db_token.revoked_at is not None:
        delete_stmt = select(RefreshToken).where(RefreshToken.user_id == db_token.user_id)
        tokens_res = await db.execute(delete_stmt)
        user_tokens = tokens_res.scalars().all()
        for t in user_tokens:
            t.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        
        response.delete_cookie("refresh_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session compromised. Please log in again."
        )

    # Check token expiration
    # Ensure timezone aware datetime checks
    now_utc = datetime.now(timezone.utc)
    if db_token.expires_at.replace(tzinfo=timezone.utc) < now_utc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )

    # Perform Token Rotation: Revoke current token, issue new token
    db_token.revoked_at = now_utc
    
    new_raw_refresh = secrets.token_urlsafe(32)
    new_refresh_hash = hash_token(new_raw_refresh)
    new_expires_at = now_utc + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    new_db_token = RefreshToken(
        user_id=db_token.user_id,
        token_hash=new_refresh_hash,
        expires_at=new_expires_at
    )
    db.add(new_db_token)
    await db.commit()

    # Generate new access token
    new_access_token = create_access_token(user_id=str(db_token.user_id))

    # Update Cookie
    response.set_cookie(
        key="refresh_token",
        value=new_raw_refresh,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    )

    return TokenResponse(access_token=new_access_token)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db_session)
):
    if refresh_token:
        token_hash = hash_token(refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await db.execute(stmt)
        db_token = result.scalars().first()
        if db_token:
            db_token.revoked_at = datetime.now(timezone.utc)
            await db.commit()

    response.delete_cookie("refresh_token")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
