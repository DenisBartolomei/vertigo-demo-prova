import os
import secrets
import hashlib
from typing import Optional, List
from datetime import datetime
from services.data_manager import db


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt"""
    salt = os.urandom(32)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + pwdhash.hex()


def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        salt = bytes.fromhex(stored_password[:64])
        stored_hash = stored_password[64:]
        pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return pwdhash.hex() == stored_hash
    except Exception:
        return False


def create_user(email: str, password: str, tenant_id: str, role: str = "hr", name: str = None) -> Optional[str]:
    """Create a new user and return user_id"""
    if db is None:
        raise RuntimeError("DB not available")
    
    # Check if user already exists
    existing_user = get_user_by_email(email)
    if existing_user:
        # Update existing user with new password and role
        hashed_password = hash_password(password)
        db["users"].update_one(
            {"_id": existing_user["_id"]},
            {
                "$set": {
                    "password_hash": hashed_password,
                    "tenant_id": tenant_id,
                    "role": role,
                    "name": name or email.split('@')[0],
                    "status": "active"
                }
            }
        )
        return existing_user["_id"]  # Return existing user_id
    
    user_id = secrets.token_urlsafe(12)
    hashed_password = hash_password(password)
    
    user_doc = {
        "_id": user_id,
        "email": email,
        "password_hash": hashed_password,
        "tenant_id": tenant_id,
        "role": role,
        "name": name or email.split('@')[0],
        "created_at": datetime.utcnow(),
        "last_login": None,
        "status": "active",
        "created_by": None  # Will be set by admin users
    }
    
    try:
        db["users"].insert_one(user_doc)
        return user_id
    except Exception as e:
        print(f"Error creating user: {e}")
        return None


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email"""
    if db is None:
        return None
    return db["users"].find_one({"email": email, "status": "active"})


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Get user by ID"""
    if db is None:
        return None
    return db["users"].find_one({"_id": user_id, "status": "active"})


def get_users_by_tenant(tenant_id: str) -> List[dict]:
    """Get all users for a tenant"""
    if db is None:
        return []
    return list(db["users"].find({"tenant_id": tenant_id, "status": "active"}))


def update_user_password(user_id: str, new_password: str) -> bool:
    """Update user password"""
    if db is None:
        return False
    
    hashed_password = hash_password(new_password)
    result = db["users"].update_one(
        {"_id": user_id},
        {"$set": {"password_hash": hashed_password}}
    )
    return result.modified_count > 0


def deactivate_user(user_id: str) -> bool:
    """Deactivate a user"""
    if db is None:
        return False
    
    result = db["users"].update_one(
        {"_id": user_id},
        {"$set": {"status": "inactive"}}
    )
    return result.modified_count > 0


def update_user_info(user_id: str, name: str = None, role: str = None) -> bool:
    """Update user information"""
    if db is None:
        return False
    
    update_data = {}
    if name:
        update_data["name"] = name
    if role:
        update_data["role"] = role
    
    if not update_data:
        return False
    
    result = db["users"].update_one(
        {"_id": user_id},
        {"$set": update_data}
    )
    return result.modified_count > 0


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authenticate user and return user data if successful"""
    user = get_user_by_email(email)
    if not user:
        return None
    
    if not verify_password(user["password_hash"], password):
        return None
    
    # Update last login
    try:
        db["users"].update_one(
            {"_id": user["_id"]}, 
            {"$set": {"last_login": datetime.utcnow()}}
        )
    except Exception:
        pass  # Don't fail auth if we can't update last login
    
    return user


def create_initial_admin_user(tenant_id: str, company_name: str) -> Optional[str]:
    """Create the initial admin user for a tenant"""
    # Use company name to generate initial admin email
    admin_email = f"admin@{company_name.lower().replace(' ', '')}.com"
    admin_password = secrets.token_urlsafe(12)  # Generate random password
    
    user_id = create_user(
        email=admin_email,
        password=admin_password,
        tenant_id=tenant_id,
        role="admin",
        name="Admin"
    )
    
    if user_id:
        print(f"Initial admin user created:")
        print(f"   Email: {admin_email}")
        print(f"   Password: {admin_password}")
        print(f"   Tenant: {tenant_id}")
        print(f"   WARNING: Please save these credentials securely!")
    
    return user_id