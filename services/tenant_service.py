import os
import secrets
from typing import Optional
from services.data_manager import db


def create_tenant(email: str, company_name: str) -> str:
    """Create a new tenant and return tenant_id"""
    if db is None:
        raise RuntimeError("DB not available")
    
    # Check if tenant already exists
    existing_tenant = get_tenant_by_email(email)
    if existing_tenant:
        return existing_tenant["_id"]  # Return existing tenant_id
    
    tenant_id = secrets.token_urlsafe(12)  # 16 chars, URL-safe
    
    tenant_doc = {
        "_id": tenant_id,
        "email": email,
        "company_name": company_name,
        "created_at": {"$date": {"$numberLong": str(int(__import__("time").time() * 1000))}},
        "status": "active"
    }
    
    db["tenants"].insert_one(tenant_doc)
    return tenant_id


def get_tenant_by_email(email: str) -> Optional[dict]:
    """Get tenant info by email"""
    if db is None:
        return None
    return db["tenants"].find_one({"email": email, "status": "active"})


def get_tenant_by_id(tenant_id: str) -> Optional[dict]:
    """Get tenant info by tenant_id"""
    if db is None:
        return None
    return db["tenants"].find_one({"_id": tenant_id, "status": "active"})


def get_tenant_collections(tenant_id: str) -> dict:
    """Get tenant-specific collection names"""
    return {
        "positions": f"{tenant_id}_positions_data",
        "sessions": f"{tenant_id}_sessions",
        "interview_links": f"{tenant_id}_interview_links"
    }


def ensure_tenant_collections(tenant_id: str):
    """Ensure tenant collections exist (MongoDB creates them on first write)"""
    collections = get_tenant_collections(tenant_id)
    for collection_name in collections.values():
        # MongoDB creates collections on first write, so we just ensure they exist
        db[collection_name].create_index("_id")


def create_tenant_if_not_exists(email: str, company_name: str) -> str:
    """Create tenant if it doesn't exist, return existing tenant_id if it does"""
    existing_tenant = get_tenant_by_email(email)
    if existing_tenant:
        return existing_tenant["_id"]
    return create_tenant(email, company_name)