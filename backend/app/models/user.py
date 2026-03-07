from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"
    SUB_DISTRIBUTOR = "sub_distributor"
    CLUSTER = "cluster"
    OPERATOR = "operator"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    role: UserRole
    phone: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    parent_id: Optional[str] = None
    theme: Optional[str] = "light"
    compact_mode: Optional[bool] = False
    email_notifications: Optional[bool] = True
    push_notifications: Optional[bool] = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    permissions: Optional[Dict[str, bool]] = None


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    status: Optional[UserStatus] = None
    theme: Optional[str] = None
    compact_mode: Optional[bool] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    permissions: Optional[Dict[str, bool]] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    phone: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    parent_id: Optional[str] = None
    status: UserStatus
    is_verified: bool
    permissions: Optional[Dict[str, bool]] = None
    created_at: str
    updated_at: str
    last_login: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class UserPermissionUpdate(BaseModel):
    permissions: Dict[str, bool]
