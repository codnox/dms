from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional
from pydantic import BaseModel
from app.database import get_db, row_to_dict, rows_to_list
from app.middleware.auth_middleware import get_current_user, require_admin, require_admin_or_manager
from app.utils.security import get_password_hash
from app.utils.helpers import get_pagination
from app.services import device_service
from datetime import datetime
import uuid

router = APIRouter()


class ChangeRequestCreate(BaseModel):
    request_type: str  # 'email_change', 'password_reset', 'both', 'device_status_change'
    new_email: Optional[str] = None
    new_password: Optional[str] = None
    device_id: Optional[str] = None
    requested_status: Optional[str] = None
    reason: Optional[str] = None


class ReviewRequest(BaseModel):
    action: str  # 'approve' or 'reject'
    review_note: Optional[str] = None
    # Admin can override the values on approval
    new_email: Optional[str] = None
    new_password: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_change_request(
    data: ChangeRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    """Submit a change request"""
    VALID_TYPES = ["email_change", "password_reset", "both", "device_status_change"]
    if data.request_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid request_type")

    if data.request_type == "device_status_change":
        if current_user["role"] not in ["staff", "manager"]:
            raise HTTPException(status_code=403, detail="Only staff and managers can submit device status change requests")
        if not data.device_id:
            raise HTTPException(status_code=400, detail="device_id required for device_status_change")
        if not data.requested_status:
            raise HTTPException(status_code=400, detail="requested_status required for device_status_change")
        if not data.reason:
            raise HTTPException(status_code=400, detail="reason required for device_status_change")
    else:
        if current_user["role"] not in ["staff", "manager"]:
            raise HTTPException(status_code=403, detail="Only staff and managers can submit change requests")
        if data.request_type in ["email_change", "both"] and not data.new_email:
            raise HTTPException(status_code=400, detail="new_email required for email_change")
        if data.request_type in ["password_reset", "both"] and not data.new_password:
            raise HTTPException(status_code=400, detail="new_password required for password_reset")
        if data.new_password and len(data.new_password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    try:
        now = datetime.utcnow().isoformat()
        request_id = f"CR-{uuid.uuid4().hex[:8].upper()}"

        async with get_db() as db:
            await db.execute(
                """INSERT INTO change_requests
                   (request_id, requested_by, requested_by_name, requested_by_role,
                    request_type, new_email, new_password, device_id, requested_status,
                    reason, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
                (
                    request_id,
                    int(current_user["id"]),
                    current_user["name"],
                    current_user["role"],
                    data.request_type,
                    data.new_email,
                    data.new_password,
                    data.device_id,
                    data.requested_status,
                    data.reason,
                    now, now
                )
            )
            await db.commit()

        return {"success": True, "message": "Change request submitted successfully", "data": {"request_id": request_id}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit change request: {str(e)}"
        )


@router.get("")
async def get_change_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: dict = Depends(get_current_user)
):
    """Get change requests - admin sees all, manager sees staff requests only"""
    role = current_user["role"]
    if role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        async with get_db() as db:
            conditions = []
            params = []

            if role == "manager":
                # Manager only sees staff requests
                conditions.append("requested_by_role = 'staff'")

            if status_filter:
                conditions.append("status = ?")
                params.append(status_filter)

            where = " AND ".join(conditions) if conditions else "1=1"

            cursor = await db.execute(f"SELECT COUNT(*) FROM change_requests WHERE {where}", params)
            total = (await cursor.fetchone())[0]

            offset = (page - 1) * page_size
            cursor = await db.execute(
                f"SELECT * FROM change_requests WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                params + [page_size, offset]
            )
            rows = await cursor.fetchall()
            items = rows_to_list(rows)

        return {
            "success": True,
            "data": items,
            "pagination": get_pagination(page, page_size, total)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve change requests: {str(e)}"
        )


@router.patch("/{request_id}/review")
async def review_change_request(
    request_id: str,
    review: ReviewRequest,
    current_user: dict = Depends(get_current_user)
):
    """Approve or reject a change request"""
    role = current_user["role"]
    if role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if review.action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")

    try:
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM change_requests WHERE request_id = ?", (request_id,)
            )
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Request not found")

            req = row_to_dict(row)

            # Managers can only review staff requests
            if role == "manager" and req["requested_by_role"] != "staff":
                raise HTTPException(status_code=403, detail="Managers can only review staff requests")

            if req["status"] != "pending":
                raise HTTPException(status_code=400, detail="Request already reviewed")

            now = datetime.utcnow().isoformat()

            if review.action == "approve":
                if req["request_type"] == "device_status_change":
                    # Apply device status change
                    dev_id = req.get("device_id")
                    new_dev_status = req.get("requested_status")
                    if dev_id and new_dev_status:
                        await device_service.update_device_status(
                            device_id=dev_id,
                            status=new_dev_status,
                            performed_by=current_user["id"],
                            performed_by_name=current_user["name"],
                            notes=f"Approved via change request {request_id}"
                        )
                else:
                    # Use override values if provided, else use original request values
                    email_to_set = review.new_email or req.get("new_email")
                    password_to_set = review.new_password or req.get("new_password")

                    update_fields = []
                    update_params = []

                    if req["request_type"] in ["email_change", "both"] and email_to_set:
                        # Check email uniqueness
                        cursor = await db.execute(
                            "SELECT id FROM users WHERE email = ? AND id != ?",
                            (email_to_set.lower(), req["requested_by"])
                        )
                        if await cursor.fetchone():
                            raise HTTPException(status_code=400, detail="Email already in use by another user")
                        update_fields.append("email = ?")
                        update_params.append(email_to_set.lower())

                    if req["request_type"] in ["password_reset", "both"] and password_to_set:
                        if len(password_to_set) < 6:
                            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
                        update_fields.append("password_hash = ?")
                        update_params.append(get_password_hash(password_to_set))

                    if update_fields:
                        update_fields.append("updated_at = ?")
                        update_params.append(now)
                        update_params.append(req["requested_by"])
                        await db.execute(
                            f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?",
                            update_params
                        )

            # Update the request status
            await db.execute(
                """UPDATE change_requests SET status = ?, reviewed_by = ?, reviewed_by_name = ?,
                   review_note = ?, updated_at = ? WHERE request_id = ?""",
                (review.action + "d", int(current_user["id"]), current_user["name"],
                 review.review_note, now, request_id)
            )
            await db.commit()

        return {"success": True, "message": f"Request {review.action}d successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review change request '{request_id}': {str(e)}"
        )
