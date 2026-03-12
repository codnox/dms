from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from app.database import get_db, row_to_dict, rows_to_list
from app.models.device import DeviceCreate, DeviceUpdate, DeviceStatus, HolderType
from app.utils.helpers import get_pagination, generate_device_id


async def get_devices(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    device_type: Optional[str] = None,
    holder_id: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """Get all devices with pagination and filters"""
    async with get_db() as db:
        conditions = []
        params = []
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        if device_type:
            conditions.append("device_type = ?")
            params.append(device_type)
        if holder_id:
            conditions.append("current_holder_id = ?")
            params.append(holder_id)
        if search:
            conditions.append("(device_id LIKE ? OR serial_number LIKE ? OR mac_address LIKE ? OR model LIKE ?)")
            params.extend([f"%{search}%"] * 4)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        cursor = await db.execute(f"SELECT COUNT(*) FROM devices WHERE {where_clause}", params)
        total = (await cursor.fetchone())[0]
        
        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"SELECT * FROM devices WHERE {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()
        
        return {
            "data": rows_to_list(rows),
            "pagination": get_pagination(page, page_size, total)
        }


async def get_device_by_id(device_id: str) -> Optional[Dict[str, Any]]:
    """Get device by ID"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (int(device_id),))
        row = await cursor.fetchone()
        return row_to_dict(row)


async def get_device_by_serial(serial_number: str) -> Optional[Dict[str, Any]]:
    """Get device by serial number"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM devices WHERE serial_number = ?", (serial_number,))
        row = await cursor.fetchone()
        return row_to_dict(row)


async def create_device(device_data: DeviceCreate, created_by: str, created_by_name: str) -> Dict[str, Any]:
    """Create a new device"""
    async with get_db() as db:
        # Check if serial number exists
        cursor = await db.execute("SELECT id FROM devices WHERE serial_number = ?", (device_data.serial_number,))
        if await cursor.fetchone():
            raise ValueError("Serial number already exists")
        
        # Check if MAC address exists
        cursor = await db.execute("SELECT id FROM devices WHERE mac_address = ?", (device_data.mac_address,))
        if await cursor.fetchone():
            raise ValueError("MAC address already exists")
        
        now = datetime.utcnow().isoformat()
        dev_id = generate_device_id(device_data.device_type.value)
        metadata_json = json.dumps(device_data.metadata) if device_data.metadata else None
        purchase_date = device_data.purchase_date.isoformat() if device_data.purchase_date else None
        warranty_expiry = device_data.warranty_expiry.isoformat() if device_data.warranty_expiry else None
        
        cursor = await db.execute(
            """INSERT INTO devices (device_id, device_type, model, serial_number, mac_address,
                manufacturer, status, current_location, current_holder_id, current_holder_name,
                current_holder_type, registered_by_name, purchase_date, warranty_expiry, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dev_id, device_data.device_type.value, device_data.model,
                device_data.serial_number, device_data.mac_address,
                device_data.manufacturer, DeviceStatus.AVAILABLE.value,
                "PDIC", None, "PDIC (Distribution)", HolderType.NOC.value,
                created_by_name,
                purchase_date, warranty_expiry, metadata_json, now, now
            )
        )
        await db.commit()
        new_id = str(cursor.lastrowid)
        
        # Add to history
        await _add_device_history(db, new_id, "registered", performed_by=created_by,
                                  performed_by_name=created_by_name, status_after=DeviceStatus.AVAILABLE.value,
                                  location="PDIC", notes="Device registered in system")
        await db.commit()
        
        return await get_device_by_id(new_id)


async def update_device(device_id: str, device_data: DeviceUpdate) -> Optional[Dict[str, Any]]:
    """Update device"""
    async with get_db() as db:
        update_fields = []
        params = []
        
        data = device_data.model_dump(exclude_unset=True)
        
        for field in ["model", "manufacturer", "current_location"]:
            if field in data and data[field] is not None:
                update_fields.append(f"{field} = ?")
                params.append(data[field])
        
        if "status" in data and data["status"] is not None:
            update_fields.append("status = ?")
            params.append(data["status"].value if hasattr(data["status"], "value") else data["status"])
        if "device_type" in data and data["device_type"] is not None:
            update_fields.append("device_type = ?")
            params.append(data["device_type"].value if hasattr(data["device_type"], "value") else data["device_type"])
        if "warranty_expiry" in data and data["warranty_expiry"] is not None:
            update_fields.append("warranty_expiry = ?")
            params.append(data["warranty_expiry"].isoformat() if hasattr(data["warranty_expiry"], "isoformat") else data["warranty_expiry"])
        if "metadata" in data and data["metadata"] is not None:
            update_fields.append("metadata = ?")
            params.append(json.dumps(data["metadata"]))
        
        if not update_fields:
            return await get_device_by_id(device_id)
        
        update_fields.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(int(device_id))
        
        await db.execute(f"UPDATE devices SET {', '.join(update_fields)} WHERE id = ?", params)
        await db.commit()
        
        return await get_device_by_id(device_id)


async def delete_device(device_id: str) -> bool:
    """Delete device"""
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM devices WHERE id = ?", (int(device_id),))
        if cursor.rowcount > 0:
            await db.execute("DELETE FROM device_history WHERE device_id = ?", (device_id,))
            await db.commit()
            return True
        return False


async def update_device_status(
    device_id: str,
    status: str,
    performed_by: str,
    performed_by_name: str,
    notes: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Update device status"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (int(device_id),))
        row = await cursor.fetchone()
        if not row:
            return None
        
        device = row_to_dict(row)
        old_status = device.get("status")
        now = datetime.utcnow().isoformat()
        
        await db.execute(
            "UPDATE devices SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, int(device_id))
        )
        
        await _add_device_history(db, device_id, "status_changed",
                                  performed_by=performed_by, performed_by_name=performed_by_name,
                                  status_before=old_status, status_after=status,
                                  location=device.get("current_location"),
                                  notes=notes or f"Status changed from {old_status} to {status}")
        await db.commit()
        
        return await get_device_by_id(device_id)


async def update_device_holder(
    device_id: str,
    holder_id: Optional[str],
    holder_name: Optional[str],
    holder_type: str,
    location: str,
    status: str,
    performed_by: str,
    performed_by_name: str,
    from_user_id: Optional[str] = None,
    from_user_name: Optional[str] = None,
    notes: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Update device holder (for distributions)"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (int(device_id),))
        row = await cursor.fetchone()
        if not row:
            return None
        
        device = row_to_dict(row)
        old_status = device.get("status")
        now = datetime.utcnow().isoformat()
        
        await db.execute(
            """UPDATE devices SET current_holder_id = ?, current_holder_name = ?,
                current_holder_type = ?, current_location = ?, status = ?, updated_at = ?
            WHERE id = ?""",
            (holder_id, holder_name, holder_type, location, status, now, int(device_id))
        )
        
        await _add_device_history(db, device_id, "distributed",
                                  from_user_id=from_user_id, from_user_name=from_user_name,
                                  to_user_id=holder_id, to_user_name=holder_name,
                                  performed_by=performed_by, performed_by_name=performed_by_name,
                                  status_before=old_status, status_after=status,
                                  location=location, notes=notes)
        await db.commit()
        
        return await get_device_by_id(device_id)


async def get_available_devices(holder_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get available devices for distribution (PDIC stock only)"""
    async with get_db() as db:
        if holder_id:
            cursor = await db.execute(
                "SELECT * FROM devices WHERE status = ? AND current_holder_id = ? LIMIT 100",
                (DeviceStatus.AVAILABLE.value, holder_id)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM devices WHERE status = ? LIMIT 100",
                (DeviceStatus.AVAILABLE.value,)
            )
        rows = await cursor.fetchall()
        return rows_to_list(rows)


async def get_held_devices(holder_id: str) -> List[Dict[str, Any]]:
    """Get all devices currently held by a user (any status) — for sub-level redistribution"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM devices WHERE current_holder_id = ? ORDER BY updated_at DESC LIMIT 200",
            (holder_id,)
        )
        rows = await cursor.fetchall()
        return rows_to_list(rows)


async def get_user_device_overview(user_id: str, user_role: str) -> Dict[str, Any]:
    """Get comprehensive device overview: devices in hand + under hierarchy + distribution stats"""
    async with get_db() as db:
        uid = int(user_id)

        # Devices directly held by this user
        cursor = await db.execute(
            "SELECT * FROM devices WHERE current_holder_id = ? ORDER BY updated_at DESC",
            (user_id,)
        )
        held_devices = rows_to_list(await cursor.fetchall())

        subordinate_devices = []
        if user_role == "sub_distributor":
            # Devices held by clusters directly under this sub_distributor
            cursor = await db.execute(
                """SELECT d.* FROM devices d
                   JOIN users u ON CAST(d.current_holder_id AS TEXT) = CAST(u.id AS TEXT)
                   WHERE u.parent_id = ? AND u.role = 'cluster'""",
                (uid,)
            )
            cluster_devices = rows_to_list(await cursor.fetchall())

            # Devices held by operators whose parent cluster belongs to this sub_distributor
            cursor = await db.execute(
                """SELECT d.* FROM devices d
                   JOIN users op ON CAST(d.current_holder_id AS TEXT) = CAST(op.id AS TEXT)
                   JOIN users cl ON op.parent_id = cl.id
                   WHERE cl.parent_id = ? AND op.role = 'operator'""",
                (uid,)
            )
            operator_devices = rows_to_list(await cursor.fetchall())
            subordinate_devices = cluster_devices + operator_devices

        elif user_role == "cluster":
            # Devices held by operators directly under this cluster
            cursor = await db.execute(
                """SELECT d.* FROM devices d
                   JOIN users u ON CAST(d.current_holder_id AS TEXT) = CAST(u.id AS TEXT)
                   WHERE u.parent_id = ? AND u.role = 'operator'""",
                (uid,)
            )
            subordinate_devices = rows_to_list(await cursor.fetchall())

        # Distribution stats from the distributions table
        cursor = await db.execute(
            "SELECT COUNT(*), COALESCE(SUM(device_count), 0) FROM distributions WHERE to_user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        total_distrib_received = int(row[0]) if row else 0
        total_devices_received = int(row[1]) if row else 0

        cursor = await db.execute(
            "SELECT COUNT(*), COALESCE(SUM(device_count), 0) FROM distributions WHERE from_user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        total_distrib_sent = int(row[0]) if row else 0
        total_devices_sent = int(row[1]) if row else 0

        all_under_me = held_devices + subordinate_devices

        return {
            "held_by_me": held_devices,
            "under_subordinates": subordinate_devices,
            "all_under_me": all_under_me,
            "stats": {
                "in_my_hand": len(held_devices),
                "under_subordinates": len(subordinate_devices),
                "total_in_chain": len(all_under_me),
                "total_devices_received": total_devices_received,
                "total_devices_sent": total_devices_sent,
                "total_distributions_received": total_distrib_received,
                "total_distributions_sent": total_distrib_sent,
            }
        }


async def get_device_history(device_id: str) -> List[Dict[str, Any]]:
    """Get device history"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM device_history WHERE device_id = ? ORDER BY timestamp DESC",
            (device_id,)
        )
        rows = await cursor.fetchall()
        return rows_to_list(rows)


async def _add_device_history(
    db, device_id: str, action: str,
    performed_by: str = None, performed_by_name: str = None,
    from_user_id: str = None, from_user_name: str = None,
    to_user_id: str = None, to_user_name: str = None,
    status_before: str = None, status_after: str = None,
    location: str = None, notes: str = None
):
    """Add device history entry (uses existing db connection)"""
    now = datetime.utcnow().isoformat()
    await db.execute(
        """INSERT INTO device_history (device_id, action, from_user_id, from_user_name,
            to_user_id, to_user_name, status_before, status_after, location, notes,
            performed_by, performed_by_name, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (device_id, action, from_user_id, from_user_name, to_user_id, to_user_name,
         status_before, status_after, location, notes, performed_by, performed_by_name, now)
    )


async def repair_device_holder_from_history(device_id: str) -> Optional[Dict[str, Any]]:
    """Repair device holder by applying the most recent 'distributed' history entry.
    Use when a device's current_holder has been corrupted by a double-approval."""
    async with get_db() as db:
        # Find the most recent distributed action
        cursor = await db.execute(
            """SELECT * FROM device_history
               WHERE device_id = ? AND action = 'distributed'
               ORDER BY timestamp DESC LIMIT 1""",
            (device_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        entry = row_to_dict(row)

        to_user_id   = entry.get("to_user_id")
        to_user_name = entry.get("to_user_name")
        if not to_user_id:
            return None

        # Look up the user to determine role-based holder_type and device status
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (int(to_user_id),))
        user_row = await cursor.fetchone()
        if not user_row:
            return None
        recipient = row_to_dict(user_row)

        role_to_type = {
            "admin": "noc", "manager": "noc", "staff": "staff",
            "sub_distributor": "sub_distributor", "cluster": "cluster", "operator": "operator"
        }
        holder_type   = role_to_type.get(recipient["role"], "noc")
        device_status = DeviceStatus.IN_USE.value if recipient["role"] == "operator" else DeviceStatus.DISTRIBUTED.value
        now = datetime.utcnow().isoformat()

        await db.execute(
            """UPDATE devices
               SET current_holder_id = ?, current_holder_name = ?,
                   current_holder_type = ?, current_location = ?,
                   status = ?, updated_at = ?
               WHERE id = ?""",
            (str(to_user_id), to_user_name, holder_type, to_user_name,
             device_status, now, int(device_id))
        )
        await db.commit()

    return await get_device_by_id(device_id)


async def track_device_by_serial(serial_number: str) -> Optional[Dict[str, Any]]:
    """Track device by serial number with full history"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM devices WHERE serial_number = ?", (serial_number,))
        row = await cursor.fetchone()
        if not row:
            return None
        
        device = row_to_dict(row)
        
        cursor = await db.execute(
            "SELECT * FROM device_history WHERE device_id = ? ORDER BY timestamp DESC LIMIT 50",
            (device["id"],)
        )
        history_rows = await cursor.fetchall()
        device["history"] = rows_to_list(history_rows)
        
        return device


async def get_device_stats() -> Dict[str, int]:
    """Get device statistics"""
    async with get_db() as db:
        stats = {}
        for key in ["total", "available", "distributed", "in_use", "defective", "returned"]:
            if key == "total":
                cursor = await db.execute("SELECT COUNT(*) FROM devices")
            else:
                cursor = await db.execute("SELECT COUNT(*) FROM devices WHERE status = ?", (key,))
            stats[key] = (await cursor.fetchone())[0]
        return stats
