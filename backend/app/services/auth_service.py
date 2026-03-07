from datetime import datetime, timedelta
from typing import Optional
import json

from app.database import get_db, row_to_dict
from app.models.auth import TokenData
from app.utils.security import verify_password, get_password_hash, create_access_token, decode_token
from app.config import settings


async def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authenticate user with email and password"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.lower(),)
        )
        row = await cursor.fetchone()
        
        if not row:
            return None
        
        user = row_to_dict(row)
        
        if not verify_password(password, user["password_hash"]):
            return None
        
        # Update last login
        now = datetime.utcnow().isoformat()
        await db.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (now, int(user["id"]))
        )
        await db.commit()
        
        return user


async def create_user_token(user: dict) -> dict:
    """Create access token for user"""
    token_data = {
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "name": user["name"]
    }
    
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
            "name": user["name"],
            "role": user["role"]
        }
    }


async def get_current_user_from_token(token: str) -> Optional[dict]:
    """Get current user from JWT token"""
    token_data = decode_token(token)
    
    if token_data is None or token_data.user_id is None:
        return None
    
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM users WHERE id = ?",
            (int(token_data.user_id),)
        )
        row = await cursor.fetchone()
        
        if row is None:
            return None
        
        user = row_to_dict(row)
        
        # Parse permissions JSON
        if user.get("permissions"):
            try:
                user["permissions"] = json.loads(user["permissions"])
            except (json.JSONDecodeError, TypeError):
                user["permissions"] = {}
        else:
            user["permissions"] = {}
        
        # Don't return password hash
        user.pop("password_hash", None)
        
        return user


async def change_user_password(user_id: str, current_password: str, new_password: str) -> bool:
    """Change user password"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM users WHERE id = ?",
            (int(user_id),)
        )
        row = await cursor.fetchone()
        
        if not row:
            return False
        
        user = row_to_dict(row)
        
        if not verify_password(current_password, user["password_hash"]):
            return False
        
        new_hash = get_password_hash(new_password)
        now = datetime.utcnow().isoformat()
        
        await db.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (new_hash, now, int(user_id))
        )
        await db.commit()
        
        return True
