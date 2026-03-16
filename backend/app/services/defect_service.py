from datetime import datetime
from typing import Optional, List, Dict, Any, Set
import json

from app.database import get_db, row_to_dict, rows_to_list
from app.models.defect import DefectCreate, DefectUpdate, DefectStatus, DefectSeverity
from app.models.device import DeviceStatus, DeviceCreate
from app.services import device_service, notification_service, return_service
from app.utils.helpers import get_pagination, generate_defect_id


def _parse_json_metadata(raw_metadata: Any) -> Dict[str, Any]:
    if isinstance(raw_metadata, dict):
        return raw_metadata
    if isinstance(raw_metadata, str) and raw_metadata.strip():
        try:
            parsed = json.loads(raw_metadata)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


async def _get_report_scope_user_ids(db, user: Dict[str, Any]) -> Optional[Set[str]]:
    role = user.get("role")
    user_id = str(user.get("id") or user.get("_id"))

    # Management roles can see all replacement mappings.
    if role in ["admin", "manager", "staff"]:
        return None

    scoped_ids: Set[str] = {user_id}
    if role == "cluster":
        cursor = await db.execute(
            "SELECT id FROM users WHERE parent_id = ? AND role = 'operator'",
            (int(user_id),)
        )
        for row in await cursor.fetchall():
            scoped_ids.add(str(row["id"]))
        return scoped_ids

    if role == "sub_distributor":
        cursor = await db.execute(
            "SELECT id FROM users WHERE parent_id = ? AND role = 'cluster'",
            (int(user_id),)
        )
        cluster_rows = await cursor.fetchall()
        cluster_ids = [row["id"] for row in cluster_rows]
        for cluster_id in cluster_ids:
            scoped_ids.add(str(cluster_id))

        if cluster_ids:
            placeholders = ",".join(["?"] * len(cluster_ids))
            cursor = await db.execute(
                f"SELECT id FROM users WHERE parent_id IN ({placeholders}) AND role = 'operator'",
                tuple(cluster_ids)
            )
            for row in await cursor.fetchall():
                scoped_ids.add(str(row["id"]))
        return scoped_ids

    # Operators and any other role fallback to own records.
    return scoped_ids


async def _enrich_defect_rows(db, defects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach defective and replacement device details to defect rows."""
    if not defects:
        return defects

    device_ids = set()
    for defect in defects:
        if defect.get("device_id"):
            device_ids.add(str(defect["device_id"]))
        if defect.get("replacement_device_id"):
            device_ids.add(str(defect["replacement_device_id"]))

    devices_map: Dict[str, Dict[str, Any]] = {}
    numeric_device_ids = [device_id for device_id in device_ids if str(device_id).isdigit()]
    if numeric_device_ids:
        placeholders = ",".join(["?"] * len(numeric_device_ids))
        cursor = await db.execute(
            f"SELECT * FROM devices WHERE id IN ({placeholders})",
            tuple(int(device_id) for device_id in numeric_device_ids)
        )
        for row in await cursor.fetchall():
            device = dict(row)
            devices_map[str(device["id"])] = device

    for defect in defects:
        defective_device = devices_map.get(str(defect.get("device_id")))
        replacement_device = devices_map.get(str(defect.get("replacement_device_id"))) if defect.get("replacement_device_id") else None

        defect["defective_device"] = defective_device
        defect["replacement_device"] = replacement_device
        defect["replacement_mapped"] = bool(replacement_device)

        # Keep top-level fields populated for list/report UIs that render direct columns.
        if defective_device:
            if not defect.get("device_serial"):
                defect["device_serial"] = defective_device.get("serial_number")
            if not defect.get("mac_address"):
                defect["mac_address"] = defective_device.get("mac_address")
            if not defect.get("device_type"):
                defect["device_type"] = defective_device.get("device_type")
            if not defect.get("device_name"):
                defect["device_name"] = defective_device.get("model") or defective_device.get("device_type")

    # Enrich with auto_return_status for replace-button gating
    auto_return_ids = [d.get("auto_return_id") for d in defects if d.get("auto_return_id")]
    if auto_return_ids:
        placeholders = ",".join(["?"] * len(auto_return_ids))
        cursor = await db.execute(
            f"SELECT return_id, status FROM returns WHERE return_id IN ({placeholders})",
            tuple(auto_return_ids)
        )
        return_status_map = {dict(r)["return_id"]: dict(r)["status"] for r in await cursor.fetchall()}
        for defect in defects:
            rid = defect.get("auto_return_id")
            defect["auto_return_status"] = return_status_map.get(rid) if rid else None

    return defects


async def get_defects(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    defect_type: Optional[str] = None,
    reported_by: Optional[str] = None,
    holder_user_id: Optional[str] = None,
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
            # Use CAST on both sides for type-safe comparison (SQLite may store as int or text)
            conditions.append("CAST(reported_by AS TEXT) = CAST(? AS TEXT)")
            params.append(str(reported_by))
        if holder_user_id:
            conditions.append(
                "(CAST(reported_by AS TEXT) = CAST(? AS TEXT) OR device_id IN (SELECT CAST(id AS TEXT) FROM devices WHERE current_holder_id = ?))"
            )
            params.extend([str(holder_user_id), str(holder_user_id)])
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
        data = await _enrich_defect_rows(db, data)

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
        enriched = await _enrich_defect_rows(db, [d])
        if enriched:
            return enriched[0]
        return d


async def create_defect(defect_data: DefectCreate, reporter: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new defect report"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (int(defect_data.device_id),))
        device = await cursor.fetchone()
        if not device:
            raise ValueError("Device not found")
        device = dict(device)

        # Prevent duplicate active defect reports for the same device
        cursor = await db.execute(
            "SELECT id, report_id, status FROM defects WHERE device_id = ? AND status NOT IN ('resolved', 'rejected') ORDER BY created_at DESC LIMIT 1",
            (defect_data.device_id,)
        )
        existing = await cursor.fetchone()
        if existing:
            existing = dict(existing)
            raise ValueError(
                f"Device already has an active defect report ({existing['report_id']}, status: {existing['status']}). "
                f"A new report can only be submitted after the existing defect is resolved."
            )

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

    # Update device status (also records history internally)
    await device_service.update_device_status(
        device_id=defect_data.device_id,
        status=DeviceStatus.DEFECTIVE.value,
        performed_by=str(reporter["_id"]),
        performed_by_name=reporter["name"],
        notes=f"Defect reported: {defect_data.defect_type.value} - {defect_data.severity.value}"
    )

    # Notify admins/managers/staff
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM users WHERE role IN ('admin', 'manager', 'staff')")
        admins = await cursor.fetchall()
        for admin in admins:
            admin = dict(admin)
            await notification_service.create_notification(
                user_id=str(admin["id"]),
                title="New Defect Report",
                message=f"A new {defect_data.severity.value} severity defect has been reported for device {device['device_id']}",
                notification_type="warning" if defect_data.severity.value in ["critical", "high"] else "info",
                category="defect",
                link=f"/defects?defectId={new_id}",
                metadata={"action": "new_defect_report", "defect_id": str(new_id)}
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
    """Update defect status. When approved, automatically creates a return request."""
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
        affected = cursor.rowcount

    if affected > 0:
        extra_msg = ""
        if status == DefectStatus.APPROVED.value:
            try:
                auto_return = await return_service.auto_create_defect_return(
                    device_id=defect["device_id"],
                    defect_id=defect_id,
                    defect_report_id=defect["report_id"],
                    requester_id=defect["reported_by"],
                    requester_name=defect["reported_by_name"]
                )
                if auto_return:
                    async with get_db() as db:
                        await db.execute(
                            "UPDATE defects SET auto_return_id = ? WHERE id = ?",
                            (auto_return["return_id"], int(defect_id))
                        )
                        await db.commit()
                    extra_msg = f" A return request ({auto_return['return_id']}) has been automatically created."
            except Exception:
                pass  # Don't fail status update if auto-return creation fails

        # Notify the reporter
        await notification_service.create_notification(
            user_id=defect["reported_by"],
            title="Defect Report Approved — Return Required" if status == DefectStatus.APPROVED.value else "Defect Status Updated",
            message=(
                f"Your defect report {defect['report_id']} has been approved. "
                f"Please return the defective device to PDIC as soon as possible.{extra_msg}"
            ) if status == DefectStatus.APPROVED.value else (
                f"Your defect report {defect['report_id']} status has been updated to {status}."
            ),
            notification_type="warning" if status == DefectStatus.APPROVED.value else "info",
            category="defect",
            link=f"/defects?defectId={defect_id}"
        )

        # Notify all admins/managers/staff when approved so they can confirm receipt
        if status == DefectStatus.APPROVED.value:
            async with get_db() as db:
                cursor = await db.execute("SELECT id FROM users WHERE role IN ('admin', 'manager', 'staff')")
                staff_rows = await cursor.fetchall()
            for row in staff_rows:
                row = dict(row)
                if str(row["id"]) != defect["reported_by"]:
                    await notification_service.create_notification(
                        user_id=str(row["id"]),
                        title="Defective Device Return — Pending Receipt",
                        message=(
                            f"Defect {defect['report_id']} approved. The operator has been instructed to return "
                            f"device to PDIC. Please confirm receipt when device arrives."
                        ),
                        notification_type="info",
                        category="return",
                        link=f"/returns"
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
                link=f"/defects?defectId={defect_id}"
            )
            return await get_defect_by_id(defect_id)
    return None


async def replace_defect_device(
    defect_id: str,
    replacement_device_id: Optional[str],
    mac_address: Optional[str],
    serial_number: Optional[str],
    register_device: Optional[Dict[str, Any]],
    notes: Optional[str],
    resolver: Dict[str, Any]
) -> Dict[str, Any]:
    """Replace a defective device by selecting existing stock or registering a new device."""
    resolver_id = str(resolver.get("_id") or resolver.get("id"))
    resolver_name = resolver.get("name") or "System"
    pre_created_device: Optional[Dict[str, Any]] = None

    if register_device:
        create_payload = DeviceCreate(**register_device)
        pre_created_device = await device_service.create_device(
            device_data=create_payload,
            created_by=resolver_id,
            created_by_name=resolver_name
        )

    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM defects WHERE id = ?", (int(defect_id),))
        defect = await cursor.fetchone()
        if not defect:
            raise ValueError("Defect report not found")
        defect = dict(defect)

        # Gate: defect must be in 'approved' status before replacement can proceed
        if defect.get("status") != DefectStatus.APPROVED.value:
            raise ValueError(
                f"Cannot replace device — defect must be in 'approved' status. "
                f"Current status: {defect.get('status')}"
            )

        # Gate: the linked return must be received at PDIC first
        auto_return_id = defect.get("auto_return_id")
        if auto_return_id:
            cursor = await db.execute(
                "SELECT status FROM returns WHERE return_id = ?", (auto_return_id,)
            )
            ret_row = await cursor.fetchone()
            if ret_row and dict(ret_row).get("status") != "received":
                raise ValueError(
                    "Cannot replace device — the defective device must be returned and received "
                    "at PDIC first. Please confirm return receipt before replacing."
                )

        cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (int(defect["device_id"]),))
        old_device = await cursor.fetchone()
        if not old_device:
            raise ValueError("Original defective device not found")
        old_device = dict(old_device)

        new_device = None
        if replacement_device_id:
            cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (int(replacement_device_id),))
            new_device = await cursor.fetchone()
            if not new_device:
                raise ValueError("Selected replacement device was not found")
            new_device = dict(new_device)
        elif pre_created_device:
            new_device = pre_created_device
        elif mac_address:
            cursor = await db.execute("SELECT * FROM devices WHERE mac_address = ?", (mac_address,))
            new_device = await cursor.fetchone()
        elif serial_number:
            cursor = await db.execute("SELECT * FROM devices WHERE serial_number = ?", (serial_number,))
            new_device = await cursor.fetchone()
        else:
            raise ValueError("Replacement target not provided")

        if not new_device:
            raise ValueError("Replacement device not found in system")
        if not isinstance(new_device, dict):
            new_device = dict(new_device)

        if str(new_device["id"]) == str(old_device["id"]):
            raise ValueError("Replacement device cannot be the same as the defective device")

        if new_device.get("status") not in [DeviceStatus.AVAILABLE.value, DeviceStatus.RETURNED.value]:
            raise ValueError(
                f"Replacement device must be available. Current status: {new_device.get('status')}"
            )

        original_holder_id = old_device.get("current_holder_id")
        original_holder_name = old_device.get("current_holder_name")
        original_holder_type = old_device.get("current_holder_type") or "operator"
        original_location = old_device.get("current_location") or "Field"

        resolution_note = notes or (
            f"Replaced with device {new_device.get('device_id')} "
            f"(Serial: {new_device.get('serial_number')}, MAC: {new_device.get('mac_address')})"
        )
        now = datetime.utcnow().isoformat()

        await db.execute(
            """UPDATE defects SET status = ?, replacement_device_id = ?, replacement_requested_at = ?,
            resolution = ?, resolved_by = ?, resolved_by_name = ?, resolved_at = ?, updated_at = ?
            WHERE id = ?""",
            (
                DefectStatus.REPLACEMENT_PENDING_CONFIRMATION.value,
                str(new_device["id"]),
                now,
                resolution_note,
                None,
                None,
                None,
                now,
                int(defect_id)
            )
        )
        await db.commit()

    old_device_metadata = _parse_json_metadata(old_device.get("metadata"))
    old_device_metadata["replaced_by"] = {
        "device_id": str(new_device.get("id")),
        "device_code": new_device.get("device_id"),
        "serial_number": new_device.get("serial_number"),
        "defect_id": str(defect_id),
        "defect_report_id": defect.get("report_id"),
        "replaced_at": datetime.utcnow().isoformat(),
        "replaced_by_user_id": resolver_id,
        "replaced_by_user_name": resolver_name
    }
    async with get_db() as db:
        await db.execute(
            "UPDATE devices SET metadata = ?, updated_at = ? WHERE id = ?",
            (json.dumps(old_device_metadata), datetime.utcnow().isoformat(), int(old_device["id"]))
        )
        await db.commit()

    # Mark the old device status as replaced and keep replacement linkage in metadata.
    await device_service.update_device_status(
        device_id=defect["device_id"],
        status=DeviceStatus.REPLACED.value,
        performed_by=resolver_id,
        performed_by_name=resolver_name,
        notes=f"Device replaced by {new_device.get('device_id')} for defect {defect.get('report_id')}"
    )

    holder_user_id = str(original_holder_id) if original_holder_id else None
    holder_user_name = original_holder_name or defect.get("reported_by_name") or "Operator"

    recipient_ids = set()
    if holder_user_id:
        recipient_ids.add(holder_user_id)
    if defect.get("reported_by"):
        recipient_ids.add(str(defect["reported_by"]))

    for recipient_id in recipient_ids:
        await notification_service.create_notification(
            user_id=recipient_id,
            title="Replacement Device Ready - Confirmation Required",
            message=(
                f"Operator update for {holder_user_name}: replacement device {new_device.get('device_id')} "
                f"(Serial: {new_device.get('serial_number')}) is prepared for defect {defect['report_id']}. "
                "Confirm only after you physically receive the replacement device. "
                "Do not confirm before receiving it."
            ),
            notification_type="warning",
            category="defect",
            link="/replacement-confirmation"
        )

    return await get_defect_by_id(defect_id)


async def confirm_replacement_receipt(
    defect_id: str,
    confirmer: Dict[str, Any],
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Operator confirms replacement receipt; then replacement is assigned to their account."""
    confirmer_id = str(confirmer.get("_id") or confirmer.get("id"))
    confirmer_name = confirmer.get("name") or "Operator"

    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM defects WHERE id = ?", (int(defect_id),))
        defect = await cursor.fetchone()
        if not defect:
            raise ValueError("Defect report not found")
        defect = dict(defect)

        if defect.get("status") != DefectStatus.REPLACEMENT_PENDING_CONFIRMATION.value:
            raise ValueError("Replacement confirmation is not pending for this defect")

        replacement_device_id = defect.get("replacement_device_id")
        if not replacement_device_id:
            raise ValueError("No replacement device is linked to this defect")

        cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (int(defect["device_id"]),))
        old_device = await cursor.fetchone()
        if not old_device:
            raise ValueError("Original defective device not found")
        old_device = dict(old_device)

        holder_user_id = str(old_device.get("current_holder_id")) if old_device.get("current_holder_id") else None
        reporter_user_id = str(defect.get("reported_by")) if defect.get("reported_by") else None
        allowed_confirmer_ids = {uid for uid in [holder_user_id, reporter_user_id] if uid}
        if confirmer_id not in allowed_confirmer_ids:
            raise ValueError("Only the current operator/holder can confirm replacement receipt")

        cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (int(replacement_device_id),))
        new_device = await cursor.fetchone()
        if not new_device:
            raise ValueError("Replacement device not found")
        new_device = dict(new_device)

        if new_device.get("status") not in [DeviceStatus.AVAILABLE.value, DeviceStatus.RETURNED.value]:
            raise ValueError(
                f"Replacement device is not available for confirmation. Current status: {new_device.get('status')}"
            )

        now = datetime.utcnow().isoformat()

        await db.execute(
            """UPDATE defects SET status = ?, replacement_confirmed_at = ?, replacement_confirmed_by = ?,
            replacement_confirmed_by_name = ?, resolved_by = ?, resolved_by_name = ?, resolved_at = ?,
            updated_at = ?, resolution = COALESCE(?, resolution)
            WHERE id = ?""",
            (
                DefectStatus.RESOLVED.value,
                now,
                confirmer_id,
                confirmer_name,
                confirmer_id,
                confirmer_name,
                now,
                now,
                notes,
                int(defect_id)
            )
        )
        await db.commit()

    # Assign replacement device to the CONFIRMING OPERATOR (not old_device holder which may be stale)
    updated_device = await device_service.update_device_holder(
        device_id=str(new_device["id"]),
        holder_id=confirmer_id,
        holder_name=confirmer_name,
        holder_type="operator",
        location=confirmer_name,
        status=DeviceStatus.IN_USE.value,
        performed_by=confirmer_id,
        performed_by_name=confirmer_name,
        from_user_id=None,
        from_user_name=None,
        notes=f"Replacement confirmed and activated for defect {defect.get('report_id')}"
    )

    if not updated_device:
        raise ValueError(
            "Replacement device holder transfer failed — device may not exist. "
            "Please contact admin to manually reassign the device."
        )

    # Notify management that receipt was confirmed
    async with get_db() as db:
        cursor = await db.execute("SELECT id FROM users WHERE role IN ('admin', 'manager', 'staff')")
        recipients = await cursor.fetchall()

    for row in recipients:
        row = dict(row)
        await notification_service.create_notification(
            user_id=str(row["id"]),
            title="Replacement Receipt Confirmed",
            message=(
                f"Operator {confirmer_name} confirmed receipt of replacement device "
                f"for defect {defect.get('report_id')}."
            ),
            notification_type="success",
            category="defect",
            link="/defects"
        )

    return await get_defect_by_id(defect_id)


async def enquire_replacement_status(
    defect_id: str,
    enquirer: Dict[str, Any],
    message: str
) -> Dict[str, Any]:
    """Operator sends an enquiry about replacement status to management roles."""
    enquirer_id = str(enquirer.get("_id") or enquirer.get("id"))
    enquirer_name = enquirer.get("name") or "Operator"

    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM defects WHERE id = ?", (int(defect_id),))
        defect = await cursor.fetchone()
        if not defect:
            raise ValueError("Defect report not found")
        defect = dict(defect)

        if defect.get("status") not in [
            DefectStatus.REPLACEMENT_PENDING_CONFIRMATION.value,
            DefectStatus.REPLACEMENT_WAITING_FOR_DEVICE.value
        ]:
            raise ValueError("Enquiry is only allowed for replacement-pending defects")

        cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (int(defect["device_id"]),))
        old_device = await cursor.fetchone()
        if not old_device:
            raise ValueError("Original defective device not found")
        old_device = dict(old_device)

        holder_user_id = str(old_device.get("current_holder_id")) if old_device.get("current_holder_id") else None
        reporter_user_id = str(defect.get("reported_by")) if defect.get("reported_by") else None
        allowed_ids = {uid for uid in [holder_user_id, reporter_user_id] if uid}
        if enquirer_id not in allowed_ids:
            raise ValueError("Only the operator involved in this defect can send an enquiry")

        cursor = await db.execute("SELECT id FROM users WHERE role IN ('staff', 'manager', 'admin')")
        management_users = await cursor.fetchall()

    for manager_row in management_users:
        manager_user_id = str(dict(manager_row)["id"])
        await notification_service.create_notification(
            user_id=manager_user_id,
            title="Replacement Enquiry from Operator",
            message=(
                f"{enquirer_name} sent an enquiry for {defect.get('report_id')}: {message}"
            ),
            notification_type="warning",
            category="defect",
            link="/defects",
            metadata={
                "action": "replacement_enquiry",
                "defect_id": str(defect_id),
                "report_id": defect.get("report_id"),
                "message": message,
                "enquirer_id": enquirer_id,
                "enquirer_name": enquirer_name
            }
        )

    return await get_defect_by_id(defect_id)


async def resend_replacement_confirmation(
    defect_id: str,
    sender: Dict[str, Any]
) -> Dict[str, Any]:
    """Resend replacement confirmation notification to operator/reporter."""
    sender_name = sender.get("name") or "Management"

    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM defects WHERE id = ?", (int(defect_id),))
        defect = await cursor.fetchone()
        if not defect:
            raise ValueError("Defect report not found")
        defect = dict(defect)

        if defect.get("status") != DefectStatus.REPLACEMENT_PENDING_CONFIRMATION.value:
            raise ValueError("Resend confirmation is only available for pending confirmation defects")

        cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (int(defect["device_id"]),))
        old_device = await cursor.fetchone()
        if not old_device:
            raise ValueError("Original defective device not found")
        old_device = dict(old_device)

        cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (int(defect["replacement_device_id"]),))
        replacement_device = await cursor.fetchone()
        if not replacement_device:
            raise ValueError("Replacement device not found")
        replacement_device = dict(replacement_device)

        holder_user_id = str(old_device.get("current_holder_id")) if old_device.get("current_holder_id") else None
        reporter_user_id = str(defect.get("reported_by")) if defect.get("reported_by") else None
        recipient_ids = {uid for uid in [holder_user_id, reporter_user_id] if uid}

    for recipient_id in recipient_ids:
        await notification_service.create_notification(
            user_id=recipient_id,
            title="Replacement Confirmation Reminder",
            message=(
                f"{sender_name} resent the confirmation reminder for defect {defect.get('report_id')}. "
                f"Please confirm only after receiving replacement device {replacement_device.get('device_id')} physically."
            ),
            notification_type="warning",
            category="defect",
            link="/replacement-confirmation",
            metadata={
                "action": "replacement_confirmation_resent",
                "defect_id": str(defect_id),
                "report_id": defect.get("report_id"),
                "replacement_device_id": str(replacement_device.get("id")),
                "replacement_device_code": replacement_device.get("device_id")
            }
        )

    return await get_defect_by_id(defect_id)


async def mark_replacement_waiting(
    defect_id: str,
    manager: Dict[str, Any],
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Mark replacement status as waiting for shipment from PDIC."""
    manager_name = manager.get("name") or "Management"

    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM defects WHERE id = ?", (int(defect_id),))
        defect = await cursor.fetchone()
        if not defect:
            raise ValueError("Defect report not found")
        defect = dict(defect)

        if defect.get("status") != DefectStatus.REPLACEMENT_PENDING_CONFIRMATION.value:
            raise ValueError("Only pending confirmation defects can be marked as waiting")

        now = datetime.utcnow().isoformat()
        waiting_note = notes or "Device is being shipped, please wait"
        await db.execute(
            "UPDATE defects SET status = ?, resolution = COALESCE(?, resolution), updated_at = ? WHERE id = ?",
            (
                DefectStatus.REPLACEMENT_WAITING_FOR_DEVICE.value,
                waiting_note,
                now,
                int(defect_id)
            )
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (int(defect["device_id"]),))
        old_device = await cursor.fetchone()
        old_device = dict(old_device) if old_device else {}

        holder_user_id = str(old_device.get("current_holder_id")) if old_device.get("current_holder_id") else None
        reporter_user_id = str(defect.get("reported_by")) if defect.get("reported_by") else None
        recipient_ids = {uid for uid in [holder_user_id, reporter_user_id] if uid}

    for recipient_id in recipient_ids:
        await notification_service.create_notification(
            user_id=recipient_id,
            title="Replacement Shipment In Progress",
            message=(
                f"Update from {manager_name} on defect {defect.get('report_id')}: "
                "Device is being shipped, please wait"
            ),
            notification_type="info",
            category="defect",
            link="/defects",
            metadata={
                "action": "replacement_waiting",
                "defect_id": str(defect_id),
                "report_id": defect.get("report_id"),
                "notes": waiting_note
            }
        )

    return await get_defect_by_id(defect_id)


async def get_replacement_defects(
    current_user: Dict[str, Any],
    page: int = 1,
    page_size: int = 100
) -> Dict[str, Any]:
    """Return defects that have replacement mapping with hierarchy-aware scope."""
    async with get_db() as db:
        conditions = ["replacement_device_id IS NOT NULL"]
        params: List[Any] = []

        scoped_user_ids = await _get_report_scope_user_ids(db, current_user)
        if scoped_user_ids is not None:
            placeholders = ",".join(["?"] * len(scoped_user_ids))
            conditions.append(f"CAST(reported_by AS TEXT) IN ({placeholders})")
            params.extend(list(scoped_user_ids))

        where = " AND ".join(conditions)

        cursor = await db.execute(f"SELECT COUNT(*) FROM defects WHERE {where}", params)
        total = (await cursor.fetchone())[0]

        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"SELECT * FROM defects WHERE {where} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()
        data = rows_to_list(rows)
        data = await _enrich_defect_rows(db, data)

        return {
            "data": data,
            "pagination": get_pagination(page, page_size, total)
        }


async def get_pending_replacement_defects(
    current_user: Dict[str, Any],
    page: int = 1,
    page_size: int = 100
) -> Dict[str, Any]:
    """Return defective devices awaiting replacement assignment."""
    async with get_db() as db:
        conditions = [
            "status = 'approved'",
            "replacement_device_id IS NULL",
        ]
        params: List[Any] = []

        scoped_user_ids = await _get_report_scope_user_ids(db, current_user)
        if scoped_user_ids is not None:
            placeholders = ",".join(["?"] * len(scoped_user_ids))
            conditions.append(f"CAST(reported_by AS TEXT) IN ({placeholders})")
            params.extend(list(scoped_user_ids))

        where = " AND ".join(conditions)

        cursor = await db.execute(f"SELECT COUNT(*) FROM defects WHERE {where}", params)
        total = (await cursor.fetchone())[0]

        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"SELECT * FROM defects WHERE {where} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()
        data = rows_to_list(rows)
        data = await _enrich_defect_rows(db, data)

        # Annotate whether defect is ready for immediate replacement assignment.
        for defect in data:
            auto_return_status = defect.get("auto_return_status")
            defect["replacement_ready"] = auto_return_status in [None, "received"]

        return {
            "data": data,
            "pagination": get_pagination(page, page_size, total)
        }


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
