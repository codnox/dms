from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from typing import Optional
from app.models.user import UserCreate, UserUpdate, UserStatus
from app.services import user_service
from app.middleware.auth_middleware import get_current_user, require_admin, require_admin_or_manager
from app.core.audit import audit_logger

router = APIRouter()


@router.get("")
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    role: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    parent_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get users - admins/managers see all; sub_distributor/cluster see their children"""
    creator_role = current_user["role"]

    # Staff can only access recipient lists used in distribution flows.
    if creator_role == "staff":
        allowed_staff_roles = {"sub_distributor", "cluster", "operator"}
        if role is None:
            raise HTTPException(
                status_code=403,
                detail="Staff must filter by role"
            )
        if role not in allowed_staff_roles:
            raise HTTPException(
                status_code=403,
                detail="Staff can only view sub distributors, clusters, and operators"
            )

    # sub_distributor and cluster only see their own children
    # admin/manager may optionally pass parent_id to filter by a specific parent
    parent_id_filter = None
    parent_ids_in_filter = None

    if creator_role == "sub_distributor":
        if role == "operator":
            # Operators live under clusters, not directly under the sub_distributor.
            # Get all cluster IDs that belong to this sub_distributor first.
            clusters_result = await user_service.get_users(
                role="cluster", parent_id=str(current_user["id"]), page_size=1000
            )
            parent_ids_in_filter = [int(c["id"]) for c in clusters_result["data"]]
        else:
            parent_id_filter = str(current_user["id"])
    elif creator_role == "cluster":
        parent_id_filter = str(current_user["id"])
    elif creator_role == "operator":
        if role == "operator":
            # Operators can see sibling operators in the same cluster
            parent_id_filter = str(current_user.get("parent_id", ""))
        else:
            raise HTTPException(status_code=403, detail="Operators can only list operators")
    elif creator_role in ["admin", "manager"] and parent_id:
        parent_id_filter = parent_id

    # Managers should never see admin accounts in list responses.
    if creator_role == "manager" and role == "admin":
        return {
            "success": True,
            "message": "Users retrieved successfully",
            "data": [],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": 0,
                "total_pages": 0,
                "has_next": False,
                "has_prev": page > 1,
            }
        }

    try:
        result = await user_service.get_users(
            page=page,
            page_size=page_size,
            role=role,
            status=status_filter,
            search=search,
            parent_id=parent_id_filter,
            parent_ids_in=parent_ids_in_filter,
        )

        data = result["data"]
        if creator_role == "manager":
            data = [u for u in data if u.get("role") != "admin"]

        return {
            "success": True,
            "message": "Users retrieved successfully",
            "data": data,
            "pagination": result["pagination"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {str(e)}"
        )


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get user by ID"""
    # Users can only view themselves unless admin/manager
    if current_user["role"] not in ["admin", "manager", "staff"] and current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile"
        )

    try:
        user = await user_service.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if current_user.get("role") == "manager" and user.get("role") == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers cannot view admin details"
            )

        return {
            "success": True,
            "message": "User retrieved successfully",
            "data": user
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user '{user_id}': {str(e)}"
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new user - role-based permissions"""
    creator_role = current_user["role"]
    target_role = user_data.role.value

    # Who can create whom
    allowed_by_role = {
        "admin":            ["admin", "manager", "staff", "sub_distributor", "cluster", "operator"],
        "manager":          ["staff", "sub_distributor", "cluster", "operator"],
        "sub_distributor":  ["cluster", "operator"],
        "cluster":          ["operator"],
    }

    if creator_role not in allowed_by_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create users"
        )

    if target_role not in allowed_by_role[creator_role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You cannot create a user with role '{target_role}'"
        )

    # Operator must always be linked to a valid cluster parent.
    if target_role == "operator":
        if not user_data.parent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must select a cluster to assign the operator to"
            )
        cluster = await user_service.get_user_by_id(user_data.parent_id)
        if not cluster or cluster.get("role") != "cluster":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cluster selected"
            )

    # Auto-assign parent_id for sub_distributor and cluster creators
    if creator_role == "sub_distributor":
        if target_role == "cluster" and not user_data.parent_id:
            # Cluster goes directly under this sub_distributor
            user_data = user_data.model_copy(update={"parent_id": str(current_user["id"])})
        elif target_role == "operator":
            # Validate the selected cluster belongs to this sub_distributor
            if str(cluster.get("parent_id")) != str(current_user["id"]):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="The selected cluster does not belong to your sub-distribution"
                )
    elif creator_role == "cluster" and not user_data.parent_id:
        user_data = user_data.model_copy(update={"parent_id": str(current_user["id"])})

    try:
        user = await user_service.create_user(user_data, creator_role=creator_role)

        return {
            "success": True,
            "message": "User created successfully",
            "data": user
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user"""
    # Users can only update themselves unless admin/manager
    if current_user["role"] not in ["admin", "manager", "staff"] and current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )

    # Non-admins can't change status
    if current_user["role"] not in ["admin", "manager", "staff"] and user_data.status:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot change account status"
        )

    try:
        user = await user_service.update_user(user_id, user_data)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {
            "success": True,
            "message": "User updated successfully",
            "data": user
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user '{user_id}': {str(e)}"
        )


@router.delete("/{user_id}")
async def delete_user(
    request: Request,
    user_id: str,
    current_user: dict = Depends(require_admin)
):
    """Delete user (admin only)"""
    # Prevent self-deletion
    if current_user["id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    try:
        success = await user_service.delete_user(user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        audit_logger.warning(
            "USER_DELETE | actor_id=%s | actor_email=%s | target_user_id=%s | ip=%s",
            current_user.get("id"),
            current_user.get("email"),
            user_id,
            request.client.host if request.client else "unknown",
        )

        return {
            "success": True,
            "message": "User deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user '{user_id}': {str(e)}"
        )


@router.patch("/{user_id}/status")
async def update_user_status(
    request: Request,
    user_id: str,
    status_update: dict,
    current_user: dict = Depends(require_admin)
):
    """Update user status (admin only)"""
    status_value = status_update.get("status")
    
    if status_value not in ["active", "inactive", "suspended"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status value"
        )

    try:
        user = await user_service.update_user_status(user_id, status_value)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        audit_logger.info(
            "USER_STATUS_UPDATE | actor_id=%s | actor_email=%s | target_user_id=%s | status=%s | ip=%s",
            current_user.get("id"),
            current_user.get("email"),
            user_id,
            status_value,
            request.client.host if request.client else "unknown",
        )

        return {
            "success": True,
            "message": "User status updated successfully",
            "data": user
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update status for user '{user_id}': {str(e)}"
        )


@router.patch("/{user_id}/credentials")
async def admin_update_credentials(
    request: Request,
    user_id: str,
    data: dict,
    current_user: dict = Depends(require_admin)
):
    """Admin reset user email/password directly"""
    from app.utils.security import get_password_hash as _hash
    from app.database import get_db as _db
    from datetime import datetime as _dt, timezone as _timezone

    try:
        async with _db() as db:
            update_fields = []
            params = []

            if "email" in data and data["email"]:
                cursor = await db.execute(
                    "SELECT id FROM users WHERE email = ? AND id != ?",
                    (data["email"].lower(), int(user_id))
                )
                if await cursor.fetchone():
                    raise HTTPException(status_code=400, detail="Email already in use")
                update_fields.append("email = ?")
                params.append(data["email"].lower())

            if "password" in data and data["password"]:
                if len(data["password"]) < 6:
                    raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
                update_fields.append("password_hash = ?")
                params.append(_hash(data["password"]))

            if not update_fields:
                raise HTTPException(status_code=400, detail="No data to update")

            update_fields.append("updated_at = ?")
            params.append(_dt.now(_timezone.utc).replace(tzinfo=None).isoformat())
            params.append(int(user_id))

            cursor = await db.execute(
                f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?", params
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")
            await db.commit()

        user = await user_service.get_user_by_id(user_id)

        if "password" in data and data["password"]:
            audit_logger.warning(
                "PASSWORD_RESET_BY_ADMIN | actor_id=%s | actor_email=%s | target_user_id=%s | ip=%s",
                current_user.get("id"),
                current_user.get("email"),
                user_id,
                request.client.host if request.client else "unknown",
            )

        if "email" in data and data["email"]:
            audit_logger.info(
                "EMAIL_CHANGE_BY_ADMIN | actor_id=%s | actor_email=%s | target_user_id=%s | ip=%s",
                current_user.get("id"),
                current_user.get("email"),
                user_id,
                request.client.host if request.client else "unknown",
            )

        return {"success": True, "message": "Credentials updated", "data": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update credentials for user '{user_id}': {str(e)}"
        )


@router.get("/role/{role}")
async def get_users_by_role(
    role: str,
    current_user: dict = Depends(require_admin_or_manager)
):
    """Get all users by role"""
    try:
        if current_user.get("role") == "manager" and role == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers cannot view admin details"
            )

        users = await user_service.get_users_by_role(role)

        return {
            "success": True,
            "message": "Users retrieved successfully",
            "data": users
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users by role '{role}': {str(e)}"
        )
