from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from app.database import get_db, row_to_dict, rows_to_list
from app.models.distribution import DistributionCreate, DistributionStatus
from app.models.device import DeviceStatus
from app.services import device_service, notification_service
from app.utils.helpers import get_pagination, generate_distribution_id


async def get_distributions(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    from_user_id: Optional[str] = None,
    to_user_id: Optional[str] = None,
    user_id: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """Get all distributions with pagination and filters"""
    async with get_db() as db:
        conditions = []
        params = []
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        if from_user_id:
            conditions.append("from_user_id = ?")
            params.append(from_user_id)
        if to_user_id:
            conditions.append("to_user_id = ?")
            params.append(to_user_id)
        if user_id:
            conditions.append("(from_user_id = ? OR to_user_id = ?)")
            params.extend([user_id, user_id])
        if search:
            conditions.append("(distribution_id LIKE ? OR from_user_name LIKE ? OR to_user_name LIKE ?)")
            params.extend([f"%{search}%"] * 3)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        cursor = await db.execute(f"SELECT COUNT(*) FROM distributions WHERE {where_clause}", params)
        total = (await cursor.fetchone())[0]
        
        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"SELECT * FROM distributions WHERE {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()
        
        result = []
        for r in rows_to_list(rows):
            if r.get("device_ids"):
                try:
                    r["device_ids"] = json.loads(r["device_ids"])
                except (json.JSONDecodeError, TypeError):
                    r["device_ids"] = []
            result.append(r)
        
        return {
            "data": result,
            "pagination": get_pagination(page, page_size, total)
        }


async def get_distribution_by_id(distribution_id: str) -> Optional[Dict[str, Any]]:
    """Get distribution by ID"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM distributions WHERE id = ?", (int(distribution_id),))
        row = await cursor.fetchone()
        if row:
            d = row_to_dict(row)
            if d.get("device_ids"):
                try:
                    d["device_ids"] = json.loads(d["device_ids"])
                except (json.JSONDecodeError, TypeError):
                    d["device_ids"] = []
            return d
        return None


async def create_distribution(dist_data: DistributionCreate, from_user: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new distribution request"""
    async with get_db() as db:
        # Get recipient user
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (int(dist_data.to_user_id),))
        to_user = await cursor.fetchone()
        if not to_user:
            raise ValueError("Recipient user not found")
        to_user = row_to_dict(to_user)
        
        # Validate devices exist and are available
        for dev_id in dist_data.device_ids:
            cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (int(dev_id),))
            device = await cursor.fetchone()
            if not device:
                raise ValueError(f"Device {dev_id} not found")
            device = row_to_dict(device)
            if device["status"] != DeviceStatus.AVAILABLE.value:
                raise ValueError(f"Device {device['device_id']} is not available")
        
        role_to_type = {
            "admin": "noc", "manager": "noc", "staff": "staff",
            "sub_distributor": "sub_distributor", "cluster": "cluster", "operator": "operator"
        }
        
        now = datetime.utcnow().isoformat()
        from_user_id = str(from_user.get("id", from_user.get("_id", "")))
        
        cursor = await db.execute(
            """INSERT INTO distributions (distribution_id, device_ids, device_count,
                from_user_id, from_user_name, from_user_type, to_user_id, to_user_name, to_user_type,
                status, request_date, notes, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                generate_distribution_id(), json.dumps(dist_data.device_ids),
                len(dist_data.device_ids), from_user_id, from_user["name"],
                role_to_type.get(from_user["role"], "noc"),
                str(to_user["id"]), to_user["name"],
                role_to_type.get(to_user["role"], "staff"),
                DistributionStatus.PENDING.value, now, dist_data.notes,
                from_user_id, now, now
            )
        )
        new_id = str(cursor.lastrowid)
        
        # Create approval entry
        await db.execute(
            """INSERT INTO approvals (approval_type, entity_id, entity_type, requested_by,
                requested_by_name, status, priority, request_date, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("distribution", new_id, "distribution", from_user_id, from_user["name"],
             "pending", "medium", now, dist_data.notes, now, now)
        )
        await db.commit()
    
    # Send notification
    await notification_service.create_notification(
        user_id=str(to_user["id"]),
        title="New Distribution Request",
        message=f"New distribution request from {from_user['name']} for {len(dist_data.device_ids)} device(s)",
        notification_type="info", category="distribution",
        link=f"/distributions/{new_id}"
    )
    
    return await get_distribution_by_id(new_id)


async def update_distribution_status(
    distribution_id: str, status: str, user: Dict[str, Any], notes: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Update distribution status"""
    dist = await get_distribution_by_id(distribution_id)
    if not dist:
        return None
    
    now = datetime.utcnow().isoformat()
    user_id = str(user.get("id", user.get("_id", "")))
    
    async with get_db() as db:
        update_fields = ["status = ?", "updated_at = ?"]
        params = [status, now]
        
        if status == DistributionStatus.APPROVED.value:
            update_fields.extend(["approval_date = ?", "approved_by = ?", "approved_by_name = ?"])
            params.extend([now, user_id, user["name"]])
            
            await db.execute(
                """UPDATE approvals SET status = 'approved', approved_by = ?, approved_by_name = ?,
                    approval_date = ?, updated_at = ? WHERE entity_id = ? AND approval_type = 'distribution'""",
                (user_id, user["name"], now, now, distribution_id)
            )
        
        elif status == DistributionStatus.DELIVERED.value:
            update_fields.append("delivery_date = ?")
            params.append(now)
        
        elif status == DistributionStatus.REJECTED.value:
            await db.execute(
                """UPDATE approvals SET status = 'rejected', approved_by = ?, approved_by_name = ?,
                    approval_date = ?, rejection_reason = ?, updated_at = ?
                    WHERE entity_id = ? AND approval_type = 'distribution'""",
                (user_id, user["name"], now, notes, now, distribution_id)
            )
        
        if notes:
            update_fields.append("notes = ?")
            params.append(notes)
        
        params.append(int(distribution_id))
        await db.execute(f"UPDATE distributions SET {', '.join(update_fields)} WHERE id = ?", params)
        await db.commit()
    
    # Update device holders on approval/delivery
    if status in [DistributionStatus.APPROVED.value, DistributionStatus.DELIVERED.value]:
        device_ids = dist.get("device_ids", [])
        for dev_id in device_ids:
            await device_service.update_device_holder(
                device_id=dev_id, holder_id=dist["to_user_id"],
                holder_name=dist["to_user_name"], holder_type=dist.get("to_user_type", "staff"),
                location=dist["to_user_name"], status=DeviceStatus.DISTRIBUTED.value,
                performed_by=user_id, performed_by_name=user["name"],
                from_user_id=dist["from_user_id"], from_user_name=dist["from_user_name"],
                notes=f"Distributed via {dist['distribution_id']}"
            )
    
    # Notification
    await notification_service.create_notification(
        user_id=dist["from_user_id"],
        title=f"Distribution {status.capitalize()}",
        message=f"Distribution {dist['distribution_id']} has been {status}",
        notification_type="success" if status in ["approved", "delivered"] else "warning",
        category="distribution", link=f"/distributions/{distribution_id}"
    )
    
    return await get_distribution_by_id(distribution_id)


async def cancel_distribution(distribution_id: str, user_id: str) -> bool:
    """Cancel a distribution"""
    dist = await get_distribution_by_id(distribution_id)
    if not dist:
        return False
    if dist["created_by"] != user_id:
        raise ValueError("Only the creator can cancel this distribution")
    if dist["status"] != DistributionStatus.PENDING.value:
        raise ValueError("Only pending distributions can be cancelled")
    
    async with get_db() as db:
        now = datetime.utcnow().isoformat()
        await db.execute(
            "UPDATE distributions SET status = ?, updated_at = ? WHERE id = ?",
            (DistributionStatus.CANCELLED.value, now, int(distribution_id))
        )
        await db.execute(
            "DELETE FROM approvals WHERE entity_id = ? AND approval_type = 'distribution'",
            (distribution_id,)
        )
        await db.commit()
    return True


async def get_pending_distributions() -> List[Dict[str, Any]]:
    """Get all pending distributions"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM distributions WHERE status = ? ORDER BY created_at DESC",
            (DistributionStatus.PENDING.value,)
        )
        rows = await cursor.fetchall()
        result = []
        for r in rows_to_list(rows):
            if r.get("device_ids"):
                try:
                    r["device_ids"] = json.loads(r["device_ids"])
                except (json.JSONDecodeError, TypeError):
                    r["device_ids"] = []
            result.append(r)
        return result


async def get_distribution_stats() -> Dict[str, int]:
    """Get distribution statistics"""
    async with get_db() as db:
        stats = {}
        for key in ["total", "pending", "approved", "delivered", "rejected"]:
            if key == "total":
                cursor = await db.execute("SELECT COUNT(*) FROM distributions")
            else:
                cursor = await db.execute("SELECT COUNT(*) FROM distributions WHERE status = ?", (key,))
            stats[key] = (await cursor.fetchone())[0]
        return stats


async def sync_approved_distributions(user: Dict[str, Any]) -> Dict[str, Any]:
    """Re-process all approved distributions to sync device holders."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM distributions WHERE status = ?", (DistributionStatus.APPROVED.value,))
        rows = await cursor.fetchall()
    
    distributions = rows_to_list(rows)
    synced_count = 0
    errors = []
    user_id = str(user.get("id", user.get("_id", "system")))
    
    for dist in distributions:
        device_ids = dist.get("device_ids", "[]")
        if isinstance(device_ids, str):
            try:
                device_ids = json.loads(device_ids)
            except (json.JSONDecodeError, TypeError):
                device_ids = []
        
        for dev_id in device_ids:
            try:
                await device_service.update_device_holder(
                    device_id=dev_id, holder_id=dist["to_user_id"],
                    holder_name=dist["to_user_name"],
                    holder_type=dist.get("to_user_type", "staff"),
                    location=dist["to_user_name"],
                    status=DeviceStatus.DISTRIBUTED.value,
                    performed_by=user_id, performed_by_name=user.get("name", "System"),
                    from_user_id=dist.get("from_user_id"),
                    from_user_name=dist.get("from_user_name"),
                    notes=f"Synced from approved distribution {dist.get('distribution_id', '')}"
                )
                synced_count += 1
            except Exception as e:
                errors.append(f"Device {dev_id}: {str(e)}")
    
    return {"total_distributions": len(distributions), "devices_synced": synced_count, "errors": errors}
