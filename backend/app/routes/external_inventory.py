from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.middleware.auth_middleware import require_management
from app.models.inventory import (
    InventoryItemCreate,
    InventoryItemUpdate,
    PurchaseOrderCreate,
    ReceiptCreate,
    StockAdjustmentCreate,
)
from app.services import inventory_service

router = APIRouter()


@router.get("/dashboard")
async def get_external_inventory_dashboard(
    current_user: dict = Depends(require_management),
):
    try:
        data = await inventory_service.get_dashboard_summary()
        return {
            "success": True,
            "message": "External inventory dashboard retrieved successfully",
            "data": data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve external inventory dashboard: {str(e)}",
        )


@router.get("/items")
async def get_external_inventory_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    low_stock_only: bool = False,
    current_user: dict = Depends(require_management),
):
    try:
        result = await inventory_service.get_items(
            page=page,
            page_size=page_size,
            search=search,
            category=category,
            status_filter=status_filter,
            low_stock_only=low_stock_only,
        )
        return {
            "success": True,
            "message": "External inventory items retrieved successfully",
            "data": result["data"],
            "pagination": result["pagination"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve external inventory items: {str(e)}",
        )


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def create_external_inventory_item(
    item_data: InventoryItemCreate,
    current_user: dict = Depends(require_management),
):
    try:
        item = await inventory_service.create_item(item_data=item_data, user=current_user)
        return {
            "success": True,
            "message": "External inventory item created successfully",
            "data": item,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create external inventory item: {str(e)}",
        )


@router.put("/items/{inventory_id}")
async def update_external_inventory_item(
    inventory_id: str,
    item_data: InventoryItemUpdate,
    current_user: dict = Depends(require_management),
):
    try:
        updated = await inventory_service.update_item(
            inventory_id=inventory_id,
            item_data=item_data,
            user=current_user,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="External inventory item not found",
            )

        return {
            "success": True,
            "message": "External inventory item updated successfully",
            "data": updated,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update external inventory item '{inventory_id}': {str(e)}",
        )


@router.post("/adjustments")
async def create_external_inventory_adjustment(
    payload: StockAdjustmentCreate,
    current_user: dict = Depends(require_management),
):
    try:
        updated_item = await inventory_service.create_stock_adjustment(
            payload=payload,
            user=current_user,
        )
        return {
            "success": True,
            "message": "Stock adjustment applied successfully",
            "data": updated_item,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply stock adjustment: {str(e)}",
        )


@router.get("/purchase-orders")
async def get_external_inventory_purchase_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    current_user: dict = Depends(require_management),
):
    try:
        result = await inventory_service.get_purchase_orders(
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            search=search,
        )
        return {
            "success": True,
            "message": "External inventory purchase orders retrieved successfully",
            "data": result["data"],
            "pagination": result["pagination"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve purchase orders: {str(e)}",
        )


@router.post("/purchase-orders", status_code=status.HTTP_201_CREATED)
async def create_external_inventory_purchase_order(
    po_data: PurchaseOrderCreate,
    current_user: dict = Depends(require_management),
):
    try:
        po = await inventory_service.create_purchase_order(po_data=po_data, user=current_user)
        return {
            "success": True,
            "message": "Purchase order created successfully",
            "data": po,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create purchase order: {str(e)}",
        )


@router.post("/purchase-orders/{po_id}/receive")
async def receive_external_inventory_purchase_order(
    po_id: str,
    receipt_data: ReceiptCreate,
    current_user: dict = Depends(require_management),
):
    try:
        po = await inventory_service.receive_purchase_order(
            po_id=po_id,
            receipt_data=receipt_data,
            user=current_user,
        )
        return {
            "success": True,
            "message": "Purchase order receipt recorded successfully",
            "data": po,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to receive purchase order '{po_id}': {str(e)}",
        )


@router.get("/receipts")
async def get_external_inventory_receipts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    po_id: Optional[str] = None,
    current_user: dict = Depends(require_management),
):
    try:
        result = await inventory_service.get_receipts(
            page=page,
            page_size=page_size,
            po_id=po_id,
        )
        return {
            "success": True,
            "message": "External inventory receipts retrieved successfully",
            "data": result["data"],
            "pagination": result["pagination"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve receipts: {str(e)}",
        )


@router.get("/movements")
async def get_external_inventory_movements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_inventory_id: Optional[str] = None,
    movement_type: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(require_management),
):
    try:
        result = await inventory_service.get_stock_movements(
            page=page,
            page_size=page_size,
            item_inventory_id=item_inventory_id,
            movement_type=movement_type,
            search=search,
        )
        return {
            "success": True,
            "message": "External inventory movements retrieved successfully",
            "data": result["data"],
            "pagination": result["pagination"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve stock movements: {str(e)}",
        )
