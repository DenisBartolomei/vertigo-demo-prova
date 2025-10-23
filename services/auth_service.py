import os
import time
from typing import Optional

import jwt  # PyJWT
from .tenant_service import get_tenant_by_email, create_tenant
from .user_service import authenticate_user, create_user, get_user_by_email


JWT_SECRET = os.getenv("JWT_SECRET", "change_me_dev_secret")
JWT_ALG = "HS256"
JWT_TTL_SECONDS = int(os.getenv("JWT_TTL_SECONDS", "3600"))  # 1 hour for automatic logout


def authenticate_hr(email: str, password: str) -> Optional[dict]:
    """
    Authenticate HR user using the user management system.
    Returns user data if authentication is successful, None otherwise.
    """
    # Try the new user authentication system first
    user = authenticate_user(email, password)
    if user:
        return user
    
    # Fallback to legacy environment variable authentication for backward compatibility
    env_email = os.getenv("HR_ADMIN_EMAIL")
    env_password = os.getenv("HR_ADMIN_PASSWORD")
    if env_email and env_password and email == env_email and password == env_password:
        # Create a temporary user object for legacy auth
        return {
            "_id": "legacy_admin",
            "email": email,
            "tenant_id": "default_tenant",
            "role": "admin",
            "name": "Legacy Admin"
        }
    
    return None


def create_jwt(sub: str, tenant_id: str, role: str = "hr") -> str:
    now = int(time.time())
    payload = {"sub": sub, "tenant_id": tenant_id, "iat": now, "exp": now + JWT_TTL_SECONDS, "role": role}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def verify_jwt(token: str) -> Optional[dict]:
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return data
    except jwt.ExpiredSignatureError:
        # Token expired - this is expected for automatic logout
        return None
    except Exception:
        return None


def is_token_expired(token: str) -> bool:
    """Check if token is expired without raising exception"""
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG], options={"verify_exp": False})
        # If we get here, token is valid but we need to check expiration manually
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG], options={"verify_exp": False})
        exp = payload.get("exp", 0)
        return time.time() > exp
    except Exception:
        return True


def refresh_jwt(token: str) -> Optional[str]:
    """Refresh JWT token if it's still valid but close to expiration"""
    try:
        # Decode without verifying expiration to check if token is still valid
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG], options={"verify_exp": False})
        
        # Check if token is close to expiration (less than 10 minutes left)
        exp = payload.get("exp", 0)
        time_left = exp - time.time()
        
        if time_left > 0 and time_left < 600:  # Less than 10 minutes left
            # Create new token with same payload but new expiration
            return create_jwt(
                sub=payload.get("sub"),
                tenant_id=payload.get("tenant_id"),
                role=payload.get("role", "hr")
            )
        
        return None  # Token doesn't need refresh yet
    except Exception:
        return None


def get_or_create_tenant_for_email(email: str, company_name: str = None) -> str:
    """Get existing tenant or create new one for email"""
    tenant = get_tenant_by_email(email)
    if tenant:
        return tenant["_id"]
    
    # Create new tenant
    if not company_name:
        company_name = email.split("@")[1].split(".")[0].title()  # Extract domain as company
    return create_tenant(email, company_name)


