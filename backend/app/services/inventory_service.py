from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.database import get_db, row_to_dict, rows_to_list
from app.models.inventory import (
    InventoryItemCreate,
    InventoryItemUpdate,
    MovementType,
    PurchaseOrderCreate,
    PurchaseOrderStatus,
    ReceiptCreate,
    StockAdjustmentCreate,
)
from app.utils.helpers import (
    generate_inventory_item_id,
    generate_inventory_movement_id,
    generate_inventory_receipt_id,
    generate_purchase_order_id,
    get_pagination,
)


def _resolve_actor(user: Dict[str, Any]) -> Dict[str, str]:
    """Normalize authenticated user payload to stable actor id/name values."""
    actor_id = user.get("id") or user.get("_id") or user.get("user_id") or user.get("sub")
    if actor_id in (None, ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user id is missing",
        )

    actor_name = user.get("name") or user.get("email") or "System"
    return {"id": str(actor_id), "name": str(actor_name)}


async def get_dashboard_summary() -> Dict[str, Any]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM external_inventory_items WHERE status = 'active'"
        )
        total_skus = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COALESCE(SUM(quantity_on_hand), 0) FROM external_inventory_items WHERE status = 'active'"
        )
        total_units = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM external_inventory_items WHERE status = 'active' AND quantity_on_hand <= reorder_level"
        )
        low_stock_items = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM inventory_purchase_orders WHERE status IN ('draft', 'submitted', 'partially_received')"
        )
        pending_purchase_orders = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COALESCE(SUM(quantity_on_hand * COALESCE(price, unit_cost, 0)), 0) FROM external_inventory_items WHERE status = 'active'"
        )
        inventory_value = float((await cursor.fetchone())[0] or 0)

        cursor = await db.execute(
            """SELECT * FROM inventory_stock_movements
               ORDER BY created_at DESC
               LIMIT 8"""
        )
        recent_movements = rows_to_list(await cursor.fetchall())

    return {
        "total_skus": total_skus,
        "total_units": total_units,
        "low_stock_items": low_stock_items,
        "pending_purchase_orders": pending_purchase_orders,
        "inventory_value": inventory_value,
        "recent_movements": recent_movements,
    }


async def get_items(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    device_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    low_stock_only: bool = False,
) -> Dict[str, Any]:
    async with get_db() as db:
        conditions = ["1=1"]
        params: List[Any] = []

        if search:
            like = f"%{search}%"
            conditions.append(
                "(item_id LIKE ? OR name LIKE ? OR serial_number LIKE ? OR mac_id LIKE ? OR supplier_name LIKE ? OR location LIKE ?)"
            )
            params.extend([like, like, like, like, like, like])

        if device_type:
            conditions.append("device_type = ?")
            params.append(device_type)

        if status_filter:
            conditions.append("status = ?")
            params.append(status_filter)

        if low_stock_only:
            conditions.append("quantity_on_hand <= reorder_level")

        where_clause = " AND ".join(conditions)

        cursor = await db.execute(
            f"SELECT COUNT(*) FROM external_inventory_items WHERE {where_clause}",
            params,
        )
        total = (await cursor.fetchone())[0]

        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"""SELECT *,
                  CASE WHEN quantity_on_hand <= reorder_level THEN 1 ELSE 0 END AS is_low_stock
                FROM external_inventory_items
                WHERE {where_clause}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        )
        rows = await cursor.fetchall()

        return {
            "data": rows_to_list(rows),
            "pagination": get_pagination(page, page_size, total),
        }


async def get_item_by_inventory_id(inventory_id: str) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM external_inventory_items WHERE inventory_id = ?",
            (inventory_id,),
        )
        row = await cursor.fetchone()
        return row_to_dict(row) if row else None


async def create_item(item_data: InventoryItemCreate, user: Dict[str, Any]) -> Dict[str, Any]:
    actor = _resolve_actor(user)

    async with get_db() as db:
        now = datetime.utcnow().isoformat()
        inventory_id = generate_inventory_item_id()

        cursor = await db.execute(
            """INSERT INTO external_inventory_items (
                   inventory_id, item_id, name, serial_number, mac_id, device_type, price,
                   sku, category, unit, quantity_on_hand, reorder_level,
                   unit_cost, supplier_name, location, status,
                   notes, image_url, created_by, created_at, updated_at
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)""",
            (
                inventory_id,
                item_data.item_id,
                item_data.name,
                item_data.serial_number,
                item_data.mac_id,
                item_data.device_type,
                item_data.price,
                item_data.item_id,
                item_data.device_type,
                item_data.unit,
                item_data.quantity_on_hand,
                item_data.reorder_level,
                item_data.price,
                item_data.supplier_name,
                item_data.location,
                item_data.notes,
                item_data.image_url,
                actor["id"],
                now,
                now,
            ),
        )

        if item_data.quantity_on_hand > 0:
            await db.execute(
                """INSERT INTO inventory_stock_movements (
                       movement_id, item_inventory_id, item_sku, item_name,
                       movement_type, quantity, reference_type, reference_id,
                       notes, performed_by, performed_by_name, created_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    generate_inventory_movement_id(),
                    inventory_id,
                    item_data.item_id,
                    item_data.name,
                    MovementType.ADJUSTMENT_IN.value,
                    item_data.quantity_on_hand,
                    "initial_stock",
                    inventory_id,
                    "Initial stock on item creation",
                    actor["id"],
                    actor["name"],
                    now,
                ),
            )

        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM external_inventory_items WHERE id = ?",
            (cursor.lastrowid,),
        )
        return row_to_dict(await cursor.fetchone())


async def update_item(
    inventory_id: str,
    item_data: InventoryItemUpdate,
    user: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    actor = _resolve_actor(user)

    update_dict = {k: v for k, v in item_data.model_dump().items() if v is not None}
    if not update_dict:
        return await get_item_by_inventory_id(inventory_id)

    if "status" in update_dict:
        update_dict["status"] = update_dict["status"].value

    async with get_db() as db:
        existing_cursor = await db.execute(
            "SELECT * FROM external_inventory_items WHERE inventory_id = ?",
            (inventory_id,),
        )
        existing = await existing_cursor.fetchone()
        if not existing:
            return None

        existing_dict = row_to_dict(existing)

        if "item_id" in update_dict:
            update_dict["sku"] = update_dict["item_id"]
        if "device_type" in update_dict:
            update_dict["category"] = update_dict["device_type"]
        if "price" in update_dict:
            update_dict["unit_cost"] = update_dict["price"]

        old_qty = int(existing_dict.get("quantity_on_hand") or 0)
        new_qty = int(update_dict.get("quantity_on_hand", old_qty))
        qty_delta = new_qty - old_qty

        update_dict["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in update_dict.keys()])

        await db.execute(
            f"UPDATE external_inventory_items SET {set_clause} WHERE inventory_id = ?",
            list(update_dict.values()) + [inventory_id],
        )

        if qty_delta != 0:
            movement_type = (
                MovementType.ADJUSTMENT_IN.value
                if qty_delta > 0
                else MovementType.ADJUSTMENT_OUT.value
            )
            await db.execute(
                """INSERT INTO inventory_stock_movements (
                       movement_id, item_inventory_id, item_sku, item_name,
                       movement_type, quantity, reference_type, reference_id,
                       notes, performed_by, performed_by_name, created_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    generate_inventory_movement_id(),
                    inventory_id,
                    update_dict.get("item_id", existing_dict.get("item_id") or existing_dict.get("sku")),
                    update_dict.get("name", existing_dict["name"]),
                    movement_type,
                    abs(qty_delta),
                    "manual_adjustment",
                    inventory_id,
                    f"Quantity adjusted from {old_qty} to {new_qty}",
                    actor["id"],
                    actor["name"],
                    datetime.utcnow().isoformat(),
                ),
            )

        await db.commit()

    return await get_item_by_inventory_id(inventory_id)


async def update_item_image(inventory_id: str, image_url: str) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM external_inventory_items WHERE inventory_id = ?",
            (inventory_id,),
        )
        existing = await cursor.fetchone()
        if not existing:
            return None

        await db.execute(
            "UPDATE external_inventory_items SET image_url = ?, updated_at = ? WHERE inventory_id = ?",
            (image_url, datetime.utcnow().isoformat(), inventory_id),
        )
        await db.commit()

    return await get_item_by_inventory_id(inventory_id)


async def get_purchase_orders(
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    async with get_db() as db:
        conditions = ["1=1"]
        params: List[Any] = []

        if status_filter:
            conditions.append("status = ?")
            params.append(status_filter)

        if search:
            like = f"%{search}%"
            conditions.append("(po_id LIKE ? OR supplier_name LIKE ? OR ordered_by_name LIKE ?)")
            params.extend([like, like, like])

        where_clause = " AND ".join(conditions)

        cursor = await db.execute(
            f"SELECT COUNT(*) FROM inventory_purchase_orders WHERE {where_clause}",
            params,
        )
        total = (await cursor.fetchone())[0]

        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"""SELECT po.*,
                       (SELECT COUNT(*) FROM inventory_po_lines pol WHERE pol.po_id = po.po_id) AS line_count,
                       (SELECT COALESCE(SUM(pol.quantity_ordered), 0) FROM inventory_po_lines pol WHERE pol.po_id = po.po_id) AS total_quantity
                FROM inventory_purchase_orders po
                WHERE {where_clause}
                ORDER BY po.created_at DESC
                LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        )
        rows = rows_to_list(await cursor.fetchall())

        for row in rows:
            lines_cursor = await db.execute(
                "SELECT * FROM inventory_po_lines WHERE po_id = ? ORDER BY id ASC",
                (row["po_id"],),
            )
            row["lines"] = rows_to_list(await lines_cursor.fetchall())

        return {
            "data": rows,
            "pagination": get_pagination(page, page_size, total),
        }


async def create_purchase_order(po_data: PurchaseOrderCreate, user: Dict[str, Any]) -> Dict[str, Any]:
    actor = _resolve_actor(user)

    if not po_data.lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Purchase order must include at least one line item",
        )

    async with get_db() as db:
        now = datetime.utcnow().isoformat()
        po_id = generate_purchase_order_id()
        total_amount = 0.0

        normalized_lines: List[Dict[str, Any]] = []
        for line in po_data.lines:
            item_cursor = await db.execute(
                "SELECT id, inventory_id, item_id, name, price, unit_cost, status FROM external_inventory_items WHERE inventory_id = ?",
                (line.item_inventory_id,),
            )
            item_row = await item_cursor.fetchone()
            if not item_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Item '{line.item_inventory_id}' not found",
                )

            item = row_to_dict(item_row)
            if item.get("status") != "active":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item '{line.item_inventory_id}' is not active",
                )

            unit_cost = float(
                line.unit_cost
                if line.unit_cost is not None
                else item.get("price")
                if item.get("price") is not None
                else item.get("unit_cost")
                or 0
            )
            line_total = float(line.quantity_ordered) * unit_cost
            total_amount += line_total

            normalized_lines.append(
                {
                    "item_inventory_id": item["inventory_id"],
                    "item_sku": item.get("item_id") or item.get("sku"),
                    "item_name": item["name"],
                    "quantity_ordered": int(line.quantity_ordered),
                    "unit_cost": unit_cost,
                    "line_total": line_total,
                }
            )

        await db.execute(
            """INSERT INTO inventory_purchase_orders (
                   po_id, supplier_name, status, expected_date, ordered_by,
                   ordered_by_name, total_amount, notes, created_at, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                po_id,
                po_data.supplier_name,
                po_data.status.value,
                po_data.expected_date,
                actor["id"],
                actor["name"],
                total_amount,
                po_data.notes,
                now,
                now,
            ),
        )

        for line in normalized_lines:
            await db.execute(
                """INSERT INTO inventory_po_lines (
                       po_id, item_inventory_id, item_sku, item_name,
                       quantity_ordered, unit_cost, line_total, created_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    po_id,
                    line["item_inventory_id"],
                    line["item_sku"],
                    line["item_name"],
                    line["quantity_ordered"],
                    line["unit_cost"],
                    line["line_total"],
                    now,
                ),
            )

        await db.commit()

    result = await get_purchase_order_by_id(po_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create purchase order",
        )
    return result


async def get_purchase_order_by_id(po_id: str) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM inventory_purchase_orders WHERE po_id = ?",
            (po_id,),
        )
        order_row = await cursor.fetchone()
        if not order_row:
            return None

        po = row_to_dict(order_row)
        lines_cursor = await db.execute(
            "SELECT * FROM inventory_po_lines WHERE po_id = ? ORDER BY id ASC",
            (po_id,),
        )
        po["lines"] = rows_to_list(await lines_cursor.fetchall())

        receipts_cursor = await db.execute(
            "SELECT * FROM inventory_receipts WHERE po_id = ? ORDER BY created_at DESC",
            (po_id,),
        )
        receipts = rows_to_list(await receipts_cursor.fetchall())

        for receipt in receipts:
            receipt_lines_cursor = await db.execute(
                "SELECT * FROM inventory_receipt_lines WHERE receipt_id = ? ORDER BY id ASC",
                (receipt["receipt_id"],),
            )
            receipt["lines"] = rows_to_list(await receipt_lines_cursor.fetchall())

        po["receipts"] = receipts
        return po


async def receive_purchase_order(
    po_id: str,
    receipt_data: ReceiptCreate,
    user: Dict[str, Any],
) -> Dict[str, Any]:
    actor = _resolve_actor(user)

    if not receipt_data.lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Receipt must include at least one line item",
        )

    async with get_db() as db:
        po_cursor = await db.execute(
            "SELECT * FROM inventory_purchase_orders WHERE po_id = ?",
            (po_id,),
        )
        po_row = await po_cursor.fetchone()
        if not po_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase order not found",
            )

        po = row_to_dict(po_row)
        if po["status"] in [PurchaseOrderStatus.CANCELLED.value, PurchaseOrderStatus.RECEIVED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot receive a purchase order in '{po['status']}' status",
            )

        po_lines_cursor = await db.execute(
            "SELECT * FROM inventory_po_lines WHERE po_id = ?",
            (po_id,),
        )
        po_lines = rows_to_list(await po_lines_cursor.fetchall())
        po_line_map = {line["item_inventory_id"]: line for line in po_lines}

        now = datetime.utcnow().isoformat()
        receipt_id = generate_inventory_receipt_id()

        await db.execute(
            """INSERT INTO inventory_receipts (
                   receipt_id, po_id, supplier_name, received_by, received_by_name, notes, created_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                receipt_id,
                po_id,
                po.get("supplier_name"),
                actor["id"],
                actor["name"],
                receipt_data.notes,
                now,
            ),
        )

        for line in receipt_data.lines:
            item_id = line.item_inventory_id
            if item_id not in po_line_map:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item '{item_id}' does not belong to this purchase order",
                )

            item_cursor = await db.execute(
                "SELECT * FROM external_inventory_items WHERE inventory_id = ?",
                (item_id,),
            )
            item_row = await item_cursor.fetchone()
            if not item_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Item '{item_id}' not found",
                )

            item = row_to_dict(item_row)
            unit_cost = float(
                line.unit_cost
                if line.unit_cost is not None
                else po_line_map[item_id].get("unit_cost")
                or item.get("price")
                or item.get("unit_cost")
                or 0
            )
            line_total = float(line.quantity_received) * unit_cost

            await db.execute(
                """INSERT INTO inventory_receipt_lines (
                       receipt_id, item_inventory_id, item_sku, item_name,
                       quantity_received, unit_cost, line_total
                   ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt_id,
                    item_id,
                    item.get("item_id") or item.get("sku"),
                    item.get("name"),
                    int(line.quantity_received),
                    unit_cost,
                    line_total,
                ),
            )

            current_qty = int(item.get("quantity_on_hand") or 0)
            consume_qty = int(line.quantity_received)
            if consume_qty > current_qty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for item '{item.get('item_id') or item_id}'. On hand: {current_qty}, requested: {consume_qty}",
                )

            new_qty = current_qty - consume_qty
            await db.execute(
                """UPDATE external_inventory_items
                   SET quantity_on_hand = ?, price = ?, unit_cost = ?, updated_at = ?
                   WHERE inventory_id = ?""",
                (new_qty, unit_cost, unit_cost, now, item_id),
            )

            await db.execute(
                """INSERT INTO inventory_stock_movements (
                       movement_id, item_inventory_id, item_sku, item_name,
                       movement_type, quantity, reference_type, reference_id,
                       notes, performed_by, performed_by_name, created_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    generate_inventory_movement_id(),
                    item_id,
                    item.get("item_id") or item.get("sku"),
                    item.get("name"),
                    MovementType.OUT.value,
                    consume_qty,
                    "purchase_submit",
                    receipt_id,
                    receipt_data.notes or f"Stock submitted against PO {po_id}",
                    actor["id"],
                    actor["name"],
                    now,
                ),
            )

        ordered_cursor = await db.execute(
            "SELECT COALESCE(SUM(quantity_ordered), 0) FROM inventory_po_lines WHERE po_id = ?",
            (po_id,),
        )
        total_ordered_qty = int((await ordered_cursor.fetchone())[0] or 0)

        received_cursor = await db.execute(
            """SELECT COALESCE(SUM(quantity_received), 0)
               FROM inventory_receipt_lines irl
               JOIN inventory_receipts ir ON irl.receipt_id = ir.receipt_id
               WHERE ir.po_id = ?""",
            (po_id,),
        )
        total_received_qty = int((await received_cursor.fetchone())[0] or 0)

        new_status = (
            PurchaseOrderStatus.RECEIVED.value
            if total_received_qty >= total_ordered_qty and total_ordered_qty > 0
            else PurchaseOrderStatus.PARTIALLY_RECEIVED.value
        )

        await db.execute(
            "UPDATE inventory_purchase_orders SET status = ?, updated_at = ? WHERE po_id = ?",
            (new_status, now, po_id),
        )

        await db.commit()

    po = await get_purchase_order_by_id(po_id)
    if not po:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load updated purchase order",
        )
    return po


async def get_receipts(
    page: int = 1,
    page_size: int = 20,
    po_id: Optional[str] = None,
) -> Dict[str, Any]:
    async with get_db() as db:
        conditions = ["1=1"]
        params: List[Any] = []

        if po_id:
            conditions.append("po_id = ?")
            params.append(po_id)

        where_clause = " AND ".join(conditions)

        cursor = await db.execute(
            f"SELECT COUNT(*) FROM inventory_receipts WHERE {where_clause}",
            params,
        )
        total = (await cursor.fetchone())[0]

        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"""SELECT * FROM inventory_receipts
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        )
        receipts = rows_to_list(await cursor.fetchall())

        for receipt in receipts:
            lines_cursor = await db.execute(
                "SELECT * FROM inventory_receipt_lines WHERE receipt_id = ? ORDER BY id ASC",
                (receipt["receipt_id"],),
            )
            receipt["lines"] = rows_to_list(await lines_cursor.fetchall())

        return {
            "data": receipts,
            "pagination": get_pagination(page, page_size, total),
        }


async def get_stock_movements(
    page: int = 1,
    page_size: int = 20,
    item_inventory_id: Optional[str] = None,
    movement_type: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    async with get_db() as db:
        conditions = ["1=1"]
        params: List[Any] = []

        if item_inventory_id:
            conditions.append("item_inventory_id = ?")
            params.append(item_inventory_id)

        if movement_type:
            conditions.append("movement_type = ?")
            params.append(movement_type)

        if search:
            like = f"%{search}%"
            conditions.append("(item_sku LIKE ? OR item_name LIKE ? OR reference_id LIKE ? OR notes LIKE ?)")
            params.extend([like, like, like, like])

        where_clause = " AND ".join(conditions)

        cursor = await db.execute(
            f"SELECT COUNT(*) FROM inventory_stock_movements WHERE {where_clause}",
            params,
        )
        total = (await cursor.fetchone())[0]

        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"""SELECT * FROM inventory_stock_movements
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        )
        movements = rows_to_list(await cursor.fetchall())

        return {
            "data": movements,
            "pagination": get_pagination(page, page_size, total),
        }


async def create_stock_adjustment(
    payload: StockAdjustmentCreate,
    user: Dict[str, Any],
) -> Dict[str, Any]:
    actor = _resolve_actor(user)

    if payload.quantity_change == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity change must be non-zero",
        )

    async with get_db() as db:
        item_cursor = await db.execute(
            "SELECT * FROM external_inventory_items WHERE inventory_id = ?",
            (payload.item_inventory_id,),
        )
        item_row = await item_cursor.fetchone()
        if not item_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found",
            )

        item = row_to_dict(item_row)
        current_qty = int(item.get("quantity_on_hand") or 0)
        new_qty = current_qty + payload.quantity_change
        if new_qty < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Adjustment would result in negative stock",
            )

        now = datetime.utcnow().isoformat()
        await db.execute(
            """UPDATE external_inventory_items
               SET quantity_on_hand = ?, updated_at = ?
               WHERE inventory_id = ?""",
            (new_qty, now, payload.item_inventory_id),
        )

        movement_type = (
            MovementType.ADJUSTMENT_IN.value
            if payload.quantity_change > 0
            else MovementType.ADJUSTMENT_OUT.value
        )
        await db.execute(
            """INSERT INTO inventory_stock_movements (
                   movement_id, item_inventory_id, item_sku, item_name,
                   movement_type, quantity, reference_type, reference_id,
                   notes, performed_by, performed_by_name, created_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                generate_inventory_movement_id(),
                payload.item_inventory_id,
                item.get("item_id") or item.get("sku"),
                item.get("name"),
                movement_type,
                abs(payload.quantity_change),
                "manual_adjustment",
                payload.item_inventory_id,
                payload.reason,
                actor["id"],
                actor["name"],
                now,
            ),
        )

        await db.commit()

    updated = await get_item_by_inventory_id(payload.item_inventory_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load updated item",
        )
    return updated
