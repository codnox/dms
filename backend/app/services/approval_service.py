from datetime import datetime
from typing import Optional, List, Dict, Any

from app.database import get_db, row_to_dict, rows_to_list
from app.models.approval import ApprovalStatus, ApprovalType
from app.services import notification_service
from app.utils.helpers import get_pagination


async def _get_entity_details(db, approval_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
    """Get entity details for an approval"""
    table_map = {"distribution": "distributions", "return": "returns", "defect": "defects"}
    table = table_map.get(approval_type)
    if not table:
        return None
    cursor = await db.execute(f"SELECT * FROM {table} WHERE id = ?", (int(entity_id),))
    row = await cursor.fetchone()
    if not row:
        return None
    entity = row_to_dict(row)

    if approval_type == "distribution":
        return {
            "distribution_id": entity.get("distribution_id"),
            "device_count": entity.get("device_count"),
            "from_user_name": entity.get("from_user_name"),
            "to_user_name": entity.get("to_user_name")
        }
    elif approval_type == "return":
        return {
            "return_id": entity.get("return_id"),
            "device_serial": entity.get("device_serial"),
            "reason": entity.get("reason"),
            "requested_by_name": entity.get("requested_by_name")
        }
    elif approval_type == "defect":
        return {
            "report_id": entity.get("report_id"),
            "device_serial": entity.get("device_serial"),
            "defect_type": entity.get("defect_type"),
            "severity": entity.get("severity")
        }
    return None


async def get_approvals(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    approval_type: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """Get all pending approvals with pagination"""
    async with get_db() as db:
        conditions = []
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        else:
            conditions.append("status = ?")
            params.append(ApprovalStatus.PENDING.value)
        if approval_type:
            conditions.append("approval_type = ?")
            params.append(approval_type)
        if search:
            conditions.append("requested_by_name LIKE ?")
            params.append(f"%{search}%")

        where = " AND ".join(conditions) if conditions else "1=1"

        cursor = await db.execute(f"SELECT COUNT(*) FROM approvals WHERE {where}", params)
        total = (await cursor.fetchone())[0]

        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"SELECT * FROM approvals WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()

        enriched = []
        for row in rows:
            approval_data = row_to_dict(row)
            details = await _get_entity_details(db, approval_data.get("approval_type", ""), approval_data.get("entity_id", ""))
            if details:
                approval_data["entity_details"] = details
            enriched.append(approval_data)

        return {
            "data": enriched,
            "pagination": get_pagination(page, page_size, total)
        }


async def get_approval_by_id(approval_id: str) -> Optional[Dict[str, Any]]:
    """Get approval by ID with entity details"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM approvals WHERE id = ?", (int(approval_id),))
        row = await cursor.fetchone()
        if not row:
            return None

        approval_data = row_to_dict(row)

        # Get full entity details
        table_map = {"distribution": "distributions", "return": "returns", "defect": "defects"}
        table = table_map.get(approval_data.get("approval_type"))
        if table and approval_data.get("entity_id"):
            cursor = await db.execute(f"SELECT * FROM {table} WHERE id = ?", (int(approval_data["entity_id"]),))
            entity_row = await cursor.fetchone()
            if entity_row:
                approval_data["entity_details"] = row_to_dict(entity_row)

        return approval_data


async def approve_request(
    approval_id: str,
    approver: Dict[str, Any],
    notes: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Approve a pending request"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM approvals WHERE id = ?", (int(approval_id),))
        approval = await cursor.fetchone()
        if not approval:
            return None
        approval = dict(approval)

        if approval["status"] != ApprovalStatus.PENDING.value:
            raise ValueError("This request has already been processed")

        now = datetime.utcnow().isoformat()

        await db.execute(
            """UPDATE approvals SET status = ?, approved_by = ?, approved_by_name = ?,
            approval_date = ?, notes = ?, updated_at = ? WHERE id = ?""",
            (ApprovalStatus.APPROVED.value, str(approver["_id"]), approver["name"],
             now, notes, now, int(approval_id))
        )

        # Update related entity
        entity_id = approval["entity_id"]
        if approval["approval_type"] == "distribution":
            await db.execute(
                """UPDATE distributions SET status = 'approved', approval_date = ?,
                approved_by = ?, approved_by_name = ?, updated_at = ? WHERE id = ?""",
                (now, str(approver["_id"]), approver["name"], now, int(entity_id))
            )
        elif approval["approval_type"] == "return":
            await db.execute(
                """UPDATE returns SET status = 'approved', approval_date = ?,
                approved_by = ?, approved_by_name = ?, updated_at = ? WHERE id = ?""",
                (now, str(approver["_id"]), approver["name"], now, int(entity_id))
            )
        elif approval["approval_type"] == "defect":
            await db.execute(
                "UPDATE defects SET status = 'approved', updated_at = ? WHERE id = ?",
                (now, int(entity_id))
            )

        await db.commit()

    await notification_service.create_notification(
        user_id=approval["requested_by"],
        title="Request Approved",
        message=f"Your {approval['approval_type']} request has been approved by {approver['name']}",
        notification_type="success",
        category="approval"
    )

    return await get_approval_by_id(approval_id)


async def reject_request(
    approval_id: str,
    approver: Dict[str, Any],
    rejection_reason: Optional[str] = None,
    notes: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Reject a pending request"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM approvals WHERE id = ?", (int(approval_id),))
        approval = await cursor.fetchone()
        if not approval:
            return None
        approval = dict(approval)

        if approval["status"] != ApprovalStatus.PENDING.value:
            raise ValueError("This request has already been processed")

        now = datetime.utcnow().isoformat()

        await db.execute(
            """UPDATE approvals SET status = ?, approved_by = ?, approved_by_name = ?,
            approval_date = ?, rejection_reason = ?, notes = ?, updated_at = ? WHERE id = ?""",
            (ApprovalStatus.REJECTED.value, str(approver["_id"]), approver["name"],
             now, rejection_reason, notes, now, int(approval_id))
        )

        entity_id = approval["entity_id"]
        if approval["approval_type"] == "distribution":
            await db.execute(
                "UPDATE distributions SET status = 'rejected', notes = ?, updated_at = ? WHERE id = ?",
                (rejection_reason, now, int(entity_id))
            )
        elif approval["approval_type"] == "return":
            await db.execute(
                "UPDATE returns SET status = 'rejected', updated_at = ? WHERE id = ?",
                (now, int(entity_id))
            )
        elif approval["approval_type"] == "defect":
            await db.execute(
                "UPDATE defects SET status = 'rejected', updated_at = ? WHERE id = ?",
                (now, int(entity_id))
            )

        await db.commit()

    await notification_service.create_notification(
        user_id=approval["requested_by"],
        title="Request Rejected",
        message=f"Your {approval['approval_type']} request has been rejected by {approver['name']}. Reason: {rejection_reason or 'No reason provided'}",
        notification_type="error",
        category="approval"
    )

    return await get_approval_by_id(approval_id)


async def get_approval_stats() -> Dict[str, int]:
    """Get approval statistics"""
    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM approvals WHERE status = 'pending'")
        pending = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM approvals WHERE status = 'approved'")
        approved = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM approvals WHERE status = 'rejected'")
        rejected = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM approvals WHERE approval_type = 'distribution' AND status = 'pending'")
        dist_pending = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM approvals WHERE approval_type = 'return' AND status = 'pending'")
        ret_pending = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM approvals WHERE approval_type = 'defect' AND status = 'pending'")
        def_pending = (await cursor.fetchone())[0]

        return {
            "total_pending": pending,
            "approved": approved,
            "rejected": rejected,
            "by_type": {
                "distributions": dist_pending,
                "returns": ret_pending,
                "defects": def_pending
            }
        }
