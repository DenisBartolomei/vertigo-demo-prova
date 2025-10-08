import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from services.data_manager import db


COLLECTION = "interview_links"
TTL_HOURS = int(os.getenv("INTERVIEW_LINK_TTL_HOURS", "168"))  # 7 days default


def _hash_token(token: str) -> str:
    pepper = os.getenv("TOKEN_PEPPER", "vertigo_pepper")
    return hashlib.sha256((pepper + token).encode("utf-8")).hexdigest()


def issue_interview_token(session_id: str, collection_name: str = COLLECTION) -> str:
    if db is None:
        raise RuntimeError("DB not available")
    token = secrets.token_urlsafe(24)
    token_hash = _hash_token(token)
    expires_at = datetime.utcnow() + timedelta(hours=TTL_HOURS)
    db[collection_name].insert_one({
        "token_hash": token_hash,
        "session_id": session_id,
        "expires_at": expires_at,
        "revoked": False,
        "uses": 0,
        "max_uses": 100,  # allow re-entry across devices before finish
    })
    return token


def resolve_token(token: str, collection_name: str = COLLECTION) -> Optional[str]:
    if db is None:
        return None
    token_hash = _hash_token(token)
    doc = db[collection_name].find_one({"token_hash": token_hash, "revoked": False})
    if not doc:
        return None
    if doc.get("expires_at") and datetime.utcnow() > doc["expires_at"]:
        return None
    
    # Check if interview has started - if so, token should be expired
    if doc.get("interview_started"):
        return None
    
    # increment uses (best-effort)
    try:
        db[collection_name].update_one({"_id": doc["_id"]}, {"$inc": {"uses": 1}})
    except Exception:
        pass
    return doc.get("session_id")


def resolve_token_global(token: str) -> Optional[tuple[str, str]]:
    """Resolve token across all tenant collections, returns (session_id, tenant_id)"""
    if db is None:
        return None
    token_hash = _hash_token(token)
    
    # Search all interview_links collections
    collections = db.list_collection_names()
    interview_collections = [c for c in collections if c.endswith("_interview_links")]
    
    for coll_name in interview_collections:
        doc = db[coll_name].find_one({"token_hash": token_hash, "revoked": False})
        if doc:
            if doc.get("expires_at") and datetime.utcnow() > doc["expires_at"]:
                continue
            # Check if interview has started - if so, token should be expired
            if doc.get("interview_started"):
                continue
            # increment uses (best-effort)
            try:
                db[coll_name].update_one({"_id": doc["_id"]}, {"$inc": {"uses": 1}})
            except Exception:
                pass
            # Extract tenant_id from collection name
            tenant_id = coll_name.replace("_interview_links", "")
            return doc.get("session_id"), tenant_id
    
    return None


def mark_interview_started(token: str, collection_name: str = COLLECTION) -> bool:
    """Mark token as interview started, making it expire for future uses"""
    if db is None:
        return False
    token_hash = _hash_token(token)
    try:
        result = db[collection_name].update_one(
            {"token_hash": token_hash, "revoked": False},
            {"$set": {"interview_started": True, "started_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    except Exception:
        return False


def mark_interview_started_global(token: str) -> bool:
    """Mark token as interview started across all tenant collections"""
    if db is None:
        return False
    token_hash = _hash_token(token)
    
    # Search all interview_links collections
    collections = db.list_collection_names()
    interview_collections = [c for c in collections if c.endswith("_interview_links")]
    
    for coll_name in interview_collections:
        try:
            result = db[coll_name].update_one(
                {"token_hash": token_hash, "revoked": False},
                {"$set": {"interview_started": True, "started_at": datetime.utcnow()}}
            )
            if result.modified_count > 0:
                return True
        except Exception:
            continue
    
    return False


