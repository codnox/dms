from datetime import datetime
from typing import Optional, List, Dict, Any

from app.database import get_db, row_to_dict, rows_to_list
from app.models.return_device import ReturnCreate, ReturnUpdate, ReturnStatus, ReturnReason
from app.models.device import DeviceStatus
from app.services import device_service, notification_service
from app.utils.helpers import get_pagination, generate_return_id


async def get_returns(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    reason: Optional[str] = None,
    requested_by: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """Get all return requests with pagination and filters"""
    async with get_db() as db:
        conditions = ["1=1"]
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        if reason:
            conditions.append("reason = ?")
            params.append(reason)
        if requested_by:
            conditions.append("requested_by = ?")
            params.append(requested_by)
        if search:
            conditions.append("(return_id LIKE ? OR device_serial LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like])

        where = " AND ".join(conditions)

        cursor = await db.execute(f"SELECT COUNT(*) FROM returns WHERE {where}", params)
        total = (await cursor.fetchone())[0]

        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"SELECT * FROM returns WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()

        return {
            "data": rows_to_list(rows),
            "pagination": get_pagination(page, page_size, total)
        }


async def get_return_by_id(return_id: str) -> Optional[Dict[str, Any]]:
    """Get return request by ID"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM returns WHERE id = ?", (int(return_id),))
        row = await cursor.fetchone()
        return row_to_dict(row) if row else None


async def create_return(return_data: ReturnCreate, requester: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new return request"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (int(return_data.device_id),))
        device = await cursor.fetchone()
        if not device:
            raise ValueError("Device not found")
        device = dict(device)

        cursor = await db.execute("SELECT * FROM users WHERE role IN ('admin', 'manager') LIMIT 1")
        return_to_user = await cursor.fetchone()
        if not return_to_user:
            raise ValueError("No admin/manager found to process return")
        return_to_user = dict(return_to_user)

        now = datetime.utcnow().isoformat()

        cursor = await db.execute(
            """INSERT INTO returns (return_id, device_id, device_serial, device_type,
            requested_by, requested_by_name, return_to, return_to_name, reason, description,
            status, request_date, approval_date, received_date, approved_by, approved_by_name,
            created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                generate_return_id(),
                return_data.device_id,
                device["serial_number"],
                device["device_type"],
                str(requester["_id"]),
                requester["name"],
                str(return_to_user["id"]),
                return_to_user["name"],
                return_data.reason.value,
                return_data.description,
                ReturnStatus.PENDING.value,
                now, None, None, None, None,
                now, now
            )
        )
        return_row_id = cursor.lastrowid

        # Create approval entry
        await db.execute(
            """INSERT INTO approvals (approval_type, entity_id, entity_type, requested_by,
            requested_by_name, status, priority, request_date, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "return", str(return_row_id), "return",
                str(requester["_id"]), requester["name"],
                "pending", "medium", now,
                return_data.description, now, now
            )
        )
        await db.commit()

    await notification_service.create_notification(
        user_id=str(return_to_user["id"]),
        title="New Return Request",
        message=f"A return request has been submitted by {requester['name']} for device {device['device_id']}",
        notification_type="info",
        category="return",
        link=f"/returns/{return_row_id}"
    )

    return await get_return_by_id(str(return_row_id))


async def update_return_status(
    return_id: str,
    status: str,
    user: Dict[str, Any],
    notes: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Update return request status"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM returns WHERE id = ?", (int(return_id),))
        return_req = await cursor.fetchone()
        if not return_req:
            return None
        return_req = dict(return_req)

        now = datetime.utcnow().isoformat()

        if status == ReturnStatus.APPROVED.value:
            await db.execute(
                "UPDATE returns SET status = ?, approval_date = ?, approved_by = ?, approved_by_name = ?, updated_at = ? WHERE id = ?",
                (status, now, str(user["_id"]), user["name"], now, int(return_id))
            )
            await db.execute(
                """UPDATE approvals SET status = 'approved', approved_by = ?, approved_by_name = ?,
                approval_date = ?, updated_at = ? WHERE entity_id = ? AND approval_type = 'return'""",
                (str(user["_id"]), user["name"], now, now, return_id)
            )

        elif status == ReturnStatus.RECEIVED.value:
            await db.execute(
                "UPDATE returns SET status = ?, received_date = ?, updated_at = ? WHERE id = ?",
                (status, now, now, int(return_id))
            )

        elif status == ReturnStatus.REJECTED.value:
            await db.execute(
                "UPDATE returns SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, int(return_id))
            )
            await db.execute(
                """UPDATE approvals SET status = 'rejected', approved_by = ?, approved_by_name = ?,
                approval_date = ?, rejection_reason = ?, updated_at = ?
                WHERE entity_id = ? AND approval_type = 'return'""",
                (str(user["_id"]), user["name"], now, notes, now, return_id)
            )
        else:
            await db.execute(
                "UPDATE returns SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, int(return_id))
            )

        await db.commit()

    if status == ReturnStatus.RECEIVED.value:
        await device_service.update_device_holder(
            device_id=return_req["device_id"],
            holder_id=None,
            holder_name=None,
            holder_type="noc",
            location="NOC",
            status=DeviceStatus.RETURNED.value,
            performed_by=str(user["_id"]),
            performed_by_name=user["name"],
            from_user_id=return_req["requested_by"],
            from_user_name=return_req["requested_by_name"],
            notes=f"Returned via {return_req['return_id']}"
        )

    await notification_service.create_notification(
        user_id=return_req["requested_by"],
        title=f"Return Request {status.capitalize()}",
        message=f"Your return request {return_req['return_id']} has been {status}",
        notification_type="success" if status in ["approved", "received"] else "warning",
        category="return",
        link=f"/returns/{return_id}"
    )

    return await get_return_by_id(return_id)


async def cancel_return(return_id: str, user_id: str) -> bool:
    """Cancel a return request (only by creator)"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM returns WHERE id = ?", (int(return_id),))
        return_req = await cursor.fetchone()
        if not return_req:
            return False
        return_req = dict(return_req)

        if return_req["requested_by"] != user_id:
            raise ValueError("Only the requester can cancel this return request")
        if return_req["status"] != ReturnStatus.PENDING.value:
            raise ValueError("Only pending return requests can be cancelled")

        await db.execute(
            "UPDATE returns SET status = ?, updated_at = ? WHERE id = ?",
            (ReturnStatus.CANCELLED.value, datetime.utcnow().isoformat(), int(return_id))
        )
        await db.execute(
            "DELETE FROM approvals WHERE entity_id = ? AND approval_type = 'return'",
            (return_id,)
        )
        await db.commit()
        return True


async def get_return_stats() -> Dict[str, Any]:
    """Get return statistics"""
    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM returns")
        total = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM returns WHERE status = 'pending'")
        pending = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM returns WHERE status = 'approved'")
        approved = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM returns WHERE status = 'received'")
        received = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM returns WHERE status = 'rejected'")
        rejected = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM returns WHERE reason = 'defective'")
        defective = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM returns WHERE reason = 'unused'")
        unused = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM returns WHERE reason = 'end_of_contract'")
        end_of_contract = (await cursor.fetchone())[0]

        return {
            "total": total,
            "by_status": {
                "pending": pending,
                "approved": approved,
                "received": received,
                "rejected": rejected
            },
            "by_reason": {
                "defective": defective,
                "unused": unused,
                "end_of_contract": end_of_contract
            }
        }
