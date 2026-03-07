from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from app.database import get_db, rows_to_list


async def _count(db, table: str, condition: str = "1=1", params=()) -> int:
    cursor = await db.execute(f"SELECT COUNT(*) FROM {table} WHERE {condition}", params)
    return (await cursor.fetchone())[0]


async def get_inventory_report() -> Dict[str, Any]:
    """Generate device inventory report"""
    async with get_db() as db:
        total = await _count(db, "devices")

        by_status = {}
        for status in ["available", "distributed", "in_use", "defective", "returned", "maintenance"]:
            by_status[status] = await _count(db, "devices", "status = ?", (status,))

        # By type
        cursor = await db.execute("SELECT DISTINCT device_type FROM devices")
        dtypes = [r[0] for r in await cursor.fetchall()]
        by_type = {}
        for dtype in dtypes:
            by_type[dtype] = await _count(db, "devices", "device_type = ?", (dtype,))

        # By holder type
        cursor = await db.execute("SELECT DISTINCT current_holder_type FROM devices WHERE current_holder_type IS NOT NULL")
        htypes = [r[0] for r in await cursor.fetchall()]
        by_location = {}
        for htype in htypes:
            by_location[htype] = await _count(db, "devices", "current_holder_type = ?", (htype,))

        return {
            "total_devices": total,
            "by_status": by_status,
            "by_type": by_type,
            "by_location": by_location,
            "generated_at": datetime.utcnow().isoformat()
        }


async def get_distribution_summary() -> Dict[str, Any]:
    """Generate distribution summary report"""
    async with get_db() as db:
        total = await _count(db, "distributions")

        by_status = {}
        for status in ["pending", "approved", "in_transit", "delivered", "rejected", "cancelled"]:
            by_status[status] = await _count(db, "distributions", "status = ?", (status,))

        by_month = []
        now = datetime.utcnow()
        for i in range(5, -1, -1):
            month_start = datetime(now.year, now.month, 1) - timedelta(days=i * 30)
            month_end = month_start + timedelta(days=30)
            count = await _count(db, "distributions", "created_at >= ? AND created_at < ?",
                                 (month_start.isoformat(), month_end.isoformat()))
            by_month.append({"month": month_start.strftime("%B %Y"), "count": count})

        # Top distributors
        cursor = await db.execute(
            """SELECT to_user_name, SUM(device_count) as total
            FROM distributions WHERE status = 'delivered'
            GROUP BY to_user_name ORDER BY total DESC LIMIT 5"""
        )
        top = await cursor.fetchall()

        return {
            "total": total,
            "by_status": by_status,
            "by_month": by_month,
            "top_distributors": [{"name": r[0], "devices": r[1]} for r in top],
            "generated_at": datetime.utcnow().isoformat()
        }


async def get_defect_summary() -> Dict[str, Any]:
    """Generate defect summary report"""
    async with get_db() as db:
        total = await _count(db, "defects")

        by_status = {}
        for status in ["reported", "under_review", "approved", "rejected", "resolved"]:
            by_status[status] = await _count(db, "defects", "status = ?", (status,))

        by_severity = {}
        for severity in ["critical", "high", "medium", "low"]:
            by_severity[severity] = await _count(db, "defects", "severity = ?", (severity,))

        by_type = {}
        for defect_type in ["hardware", "software", "physical_damage", "performance", "connectivity", "other"]:
            by_type[defect_type] = await _count(db, "defects", "defect_type = ?", (defect_type,))

        by_month = []
        now = datetime.utcnow()
        for i in range(5, -1, -1):
            month_start = datetime(now.year, now.month, 1) - timedelta(days=i * 30)
            month_end = month_start + timedelta(days=30)
            count = await _count(db, "defects", "created_at >= ? AND created_at < ?",
                                 (month_start.isoformat(), month_end.isoformat()))
            by_month.append({"month": month_start.strftime("%B %Y"), "count": count})

        return {
            "total": total,
            "by_status": by_status,
            "by_severity": by_severity,
            "by_type": by_type,
            "by_month": by_month,
            "generated_at": datetime.utcnow().isoformat()
        }


async def get_return_summary() -> Dict[str, Any]:
    """Generate return summary report"""
    async with get_db() as db:
        total = await _count(db, "returns")

        by_status = {}
        for status in ["pending", "approved", "in_transit", "received", "rejected", "cancelled"]:
            by_status[status] = await _count(db, "returns", "status = ?", (status,))

        by_reason = {}
        for reason in ["defective", "unused", "end_of_contract", "upgrade", "other"]:
            by_reason[reason] = await _count(db, "returns", "reason = ?", (reason,))

        by_month = []
        now = datetime.utcnow()
        for i in range(5, -1, -1):
            month_start = datetime(now.year, now.month, 1) - timedelta(days=i * 30)
            month_end = month_start + timedelta(days=30)
            count = await _count(db, "returns", "created_at >= ? AND created_at < ?",
                                 (month_start.isoformat(), month_end.isoformat()))
            by_month.append({"month": month_start.strftime("%B %Y"), "count": count})

        return {
            "total": total,
            "by_status": by_status,
            "by_reason": by_reason,
            "by_month": by_month,
            "generated_at": datetime.utcnow().isoformat()
        }


async def get_user_activity_report() -> Dict[str, Any]:
    """Generate user activity report"""
    async with get_db() as db:
        by_role = {}
        for role in ["admin", "manager", "staff", "sub_distributor", "cluster", "operator"]:
            by_role[role] = await _count(db, "users", "role = ?", (role,))

        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        active_users = await _count(db, "users", "last_login >= ?", (thirty_days_ago,))
        total_users = await _count(db, "users")

        cursor = await db.execute("SELECT * FROM device_history ORDER BY timestamp DESC LIMIT 50")
        rows = await cursor.fetchall()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "by_role": by_role,
            "recent_activities": rows_to_list(rows),
            "generated_at": datetime.utcnow().isoformat()
        }


async def get_device_utilization_report() -> Dict[str, Any]:
    """Generate device utilization report"""
    async with get_db() as db:
        total_devices = await _count(db, "devices")
        in_use = await _count(db, "devices", "status IN ('distributed', 'in_use')")
        available = await _count(db, "devices", "status = 'available'")
        defective = await _count(db, "devices", "status = 'defective'")

        utilization_rate = (in_use / total_devices * 100) if total_devices > 0 else 0

        return {
            "total_devices": total_devices,
            "in_use": in_use,
            "available": available,
            "defective": defective,
            "utilization_rate": round(utilization_rate, 2),
            "generated_at": datetime.utcnow().isoformat()
        }
