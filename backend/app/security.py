from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.config import settings

# Initialize Argon2 Password Hasher
ph = PasswordHasher()

def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return ph.hash(password)

def verify_password(hashed_password: str, password: str) -> bool:
    """Verify a password against an Argon2 hash."""
    try:
        ph.verify(hashed_password, password)
        return True
    except VerifyMismatchError:
        return False

def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a short-lived access JWT token."""
    to_encode = {
        "sub": user_id,
        "type": "access"
    }
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": int(expire.timestamp())})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a long-lived refresh JWT token."""
    to_encode = {
        "sub": user_id,
        "type": "refresh"
    }
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": int(expire.timestamp())})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token. Returns the payload or None if invalid."""
    try:
        # jwt.decode automatically validates expiration ('exp')
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        # Token is expired
        return None
    except jwt.PyJWTError:
        # Token is invalid (signature mismatch, malformed, etc.)
        return None
