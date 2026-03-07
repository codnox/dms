from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from app.database import get_db, row_to_dict, rows_to_list
from app.models.defect import DefectCreate, DefectUpdate, DefectStatus, DefectSeverity
from app.models.device import DeviceStatus
from app.services import device_service, notification_service
from app.utils.helpers import get_pagination, generate_defect_id


async def get_defects(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    defect_type: Optional[str] = None,
    reported_by: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """Get all defect reports with pagination and filters"""
    async with get_db() as db:
        conditions = ["1=1"]
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        if defect_type:
            conditions.append("defect_type = ?")
            params.append(defect_type)
        if reported_by:
            conditions.append("reported_by = ?")
            params.append(reported_by)
        if search:
            conditions.append("(report_id LIKE ? OR device_serial LIKE ? OR description LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like, like])

        where = " AND ".join(conditions)

        cursor = await db.execute(f"SELECT COUNT(*) FROM defects WHERE {where}", params)
        total = (await cursor.fetchone())[0]

        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"SELECT * FROM defects WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()
        data = rows_to_list(rows)
        for d in data:
            if isinstance(d.get("images"), str):
                d["images"] = json.loads(d["images"])

        return {
            "data": data,
            "pagination": get_pagination(page, page_size, total)
        }


async def get_defect_by_id(defect_id: str) -> Optional[Dict[str, Any]]:
    """Get defect report by ID"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM defects WHERE id = ?", (int(defect_id),))
        row = await cursor.fetchone()
        if not row:
            return None
        d = row_to_dict(row)
        if isinstance(d.get("images"), str):
            d["images"] = json.loads(d["images"])
        return d


async def create_defect(defect_data: DefectCreate, reporter: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new defect report"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (int(defect_data.device_id),))
        device = await cursor.fetchone()
        if not device:
            raise ValueError("Device not found")
        device = dict(device)

        now = datetime.utcnow().isoformat()
        images_json = json.dumps(defect_data.images or [])

        cursor = await db.execute(
            """INSERT INTO defects (report_id, device_id, device_serial, device_type,
            reported_by, reported_by_name, defect_type, severity, description, symptoms,
            status, resolution, resolved_by, resolved_by_name, resolved_at, images,
            created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                generate_defect_id(),
                defect_data.device_id,
                device["serial_number"],
                device["device_type"],
                str(reporter["_id"]),
                reporter["name"],
                defect_data.defect_type.value,
                defect_data.severity.value,
                defect_data.description,
                defect_data.symptoms,
                DefectStatus.REPORTED.value,
                None, None, None, None,
                images_json,
                now, now
            )
        )
        await db.commit()
        new_id = cursor.lastrowid

    # Update device status
    await device_service.update_device_status(
        device_id=defect_data.device_id,
        status=DeviceStatus.DEFECTIVE.value,
        performed_by=str(reporter["_id"]),
        performed_by_name=reporter["name"],
        notes=f"Defect reported"
    )

    await device_service.add_device_history(
        device_id=defect_data.device_id,
        action="defect_reported",
        status_before=device["status"],
        status_after=DeviceStatus.DEFECTIVE.value,
        location=device.get("current_location"),
        notes=f"Defect: {defect_data.defect_type.value} - {defect_data.severity.value}",
        performed_by=str(reporter["_id"]),
        performed_by_name=reporter["name"]
    )

    # Notify admins/managers
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM users WHERE role IN ('admin', 'manager')")
        admins = await cursor.fetchall()
        for admin in admins:
            admin = dict(admin)
            await notification_service.create_notification(
                user_id=str(admin["id"]),
                title="New Defect Report",
                message=f"A new {defect_data.severity.value} severity defect has been reported for device {device['device_id']}",
                notification_type="warning" if defect_data.severity.value in ["critical", "high"] else "info",
                category="defect",
                link=f"/defects/{new_id}"
            )

    return await get_defect_by_id(str(new_id))


async def update_defect(defect_id: str, defect_data: DefectUpdate) -> Optional[Dict[str, Any]]:
    """Update defect report"""
    update_dict = {k: v for k, v in defect_data.model_dump().items() if v is not None}

    if not update_dict:
        return await get_defect_by_id(defect_id)

    if "defect_type" in update_dict:
        update_dict["defect_type"] = update_dict["defect_type"].value
    if "severity" in update_dict:
        update_dict["severity"] = update_dict["severity"].value
    if "status" in update_dict:
        update_dict["status"] = update_dict["status"].value

    update_dict["updated_at"] = datetime.utcnow().isoformat()

    async with get_db() as db:
        set_clause = ", ".join(f"{k} = ?" for k in update_dict)
        values = list(update_dict.values()) + [int(defect_id)]
        cursor = await db.execute(f"UPDATE defects SET {set_clause} WHERE id = ?", values)
        await db.commit()
        if cursor.rowcount > 0:
            return await get_defect_by_id(defect_id)
    return None


async def delete_defect(defect_id: str) -> bool:
    """Delete defect report"""
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM defects WHERE id = ?", (int(defect_id),))
        await db.commit()
        return cursor.rowcount > 0


async def update_defect_status(
    defect_id: str,
    status: str,
    user: Dict[str, Any],
    notes: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Update defect status"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM defects WHERE id = ?", (int(defect_id),))
        defect = await cursor.fetchone()
        if not defect:
            return None
        defect = dict(defect)

        now = datetime.utcnow().isoformat()
        cursor = await db.execute(
            "UPDATE defects SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, int(defect_id))
        )
        await db.commit()

        if cursor.rowcount > 0:
            await notification_service.create_notification(
                user_id=defect["reported_by"],
                title="Defect Status Updated",
                message=f"Your defect report {defect['report_id']} status has been updated to {status}",
                notification_type="info",
                category="defect",
                link=f"/defects/{defect_id}"
            )
            return await get_defect_by_id(defect_id)
    return None


async def resolve_defect(
    defect_id: str,
    resolution: str,
    resolver: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Resolve a defect report"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM defects WHERE id = ?", (int(defect_id),))
        defect = await cursor.fetchone()
        if not defect:
            return None
        defect = dict(defect)

        now = datetime.utcnow().isoformat()
        cursor = await db.execute(
            """UPDATE defects SET status = ?, resolution = ?, resolved_by = ?,
            resolved_by_name = ?, resolved_at = ?, updated_at = ? WHERE id = ?""",
            (DefectStatus.RESOLVED.value, resolution, str(resolver["_id"]),
             resolver["name"], now, now, int(defect_id))
        )
        await db.commit()

        if cursor.rowcount > 0:
            await device_service.update_device_status(
                device_id=defect["device_id"],
                status=DeviceStatus.MAINTENANCE.value,
                performed_by=str(resolver["_id"]),
                performed_by_name=resolver["name"],
                notes=f"Defect resolved: {defect['report_id']}"
            )

            await notification_service.create_notification(
                user_id=defect["reported_by"],
                title="Defect Resolved",
                message=f"Your defect report {defect['report_id']} has been resolved",
                notification_type="success",
                category="defect",
                link=f"/defects/{defect_id}"
            )
            return await get_defect_by_id(defect_id)
    return None


async def get_defect_stats() -> Dict[str, Any]:
    """Get defect statistics"""
    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM defects")
        total = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM defects WHERE status = 'reported'")
        reported = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM defects WHERE status = 'under_review'")
        under_review = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM defects WHERE status = 'resolved'")
        resolved = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM defects WHERE severity = 'critical'")
        critical = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM defects WHERE severity = 'high'")
        high = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM defects WHERE severity = 'medium'")
        medium = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM defects WHERE severity = 'low'")
        low = (await cursor.fetchone())[0]

        return {
            "total": total,
            "by_status": {
                "reported": reported,
                "under_review": under_review,
                "resolved": resolved
            },
            "by_severity": {
                "critical": critical,
                "high": high,
                "medium": medium,
                "low": low
            }
        }
