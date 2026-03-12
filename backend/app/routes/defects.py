from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional
from app.models.defect import DefectCreate, DefectUpdate, DefectResolve, DefectStatusUpdate, ReplaceDeviceRequest
from app.services import defect_service
from app.middleware.auth_middleware import get_current_user, require_admin_or_manager

router = APIRouter()


@router.get("")
async def get_defects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    defect_type: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all defect reports with pagination and filters"""
    try:
        # Filter by reporter for non-admin/manager
        reported_by = None
        if current_user["role"] not in ["admin", "manager", "staff"]:
            reported_by = current_user["id"]

        result = await defect_service.get_defects(
            page=page,
            page_size=page_size,
            status=status,
            severity=severity,
            defect_type=defect_type,
            reported_by=reported_by,
            search=search
        )

        return {
            "success": True,
            "message": "Defect reports retrieved successfully",
            "data": result["data"],
            "pagination": result["pagination"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve defect reports: {str(e)}"
        )


@router.get("/{defect_id}")
async def get_defect(
    defect_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get defect report by ID"""
    try:
        defect = await defect_service.get_defect_by_id(defect_id)

        if not defect:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Defect report not found"
            )

        return {
            "success": True,
            "message": "Defect report retrieved successfully",
            "data": defect
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve defect report '{defect_id}': {str(e)}"
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_defect(
    defect_data: DefectCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new defect report"""
    try:
        defect = await defect_service.create_defect(
            defect_data=defect_data,
            reporter=current_user
        )

        return {
            "success": True,
            "message": "Defect report created successfully",
            "data": defect
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create defect report: {str(e)}"
        )


@router.put("/{defect_id}")
async def update_defect(
    defect_id: str,
    defect_data: DefectUpdate,
    current_user: dict = Depends(require_admin_or_manager)
):
    """Update defect report"""
    try:
        defect = await defect_service.update_defect(defect_id, defect_data)

        if not defect:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Defect report not found"
            )

        return {
            "success": True,
            "message": "Defect report updated successfully",
            "data": defect
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update defect report '{defect_id}': {str(e)}"
        )


@router.delete("/{defect_id}")
async def delete_defect(
    defect_id: str,
    current_user: dict = Depends(require_admin_or_manager)
):
    """Delete defect report"""
    try:
        success = await defect_service.delete_defect(defect_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Defect report not found"
            )

        return {
            "success": True,
            "message": "Defect report deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete defect report '{defect_id}': {str(e)}"
        )


@router.patch("/{defect_id}/status")
async def update_defect_status(
    defect_id: str,
    status_update: DefectStatusUpdate,
    current_user: dict = Depends(require_admin_or_manager)
):
    """Update defect status"""
    try:
        defect = await defect_service.update_defect_status(
            defect_id=defect_id,
            status=status_update.status.value,
            user=current_user,
            notes=status_update.notes
        )

        if not defect:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Defect report not found"
            )

        return {
            "success": True,
            "message": "Defect status updated successfully",
            "data": defect
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update defect status '{defect_id}': {str(e)}"
        )


@router.patch("/{defect_id}/resolve")
async def resolve_defect(
    defect_id: str,
    resolve_data: DefectResolve,
    current_user: dict = Depends(require_admin_or_manager)
):
    """Resolve a defect report"""
    try:
        defect = await defect_service.resolve_defect(
            defect_id=defect_id,
            resolution=resolve_data.resolution,
            resolver=current_user
        )

        if not defect:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Defect report not found"
            )

        return {
            "success": True,
            "message": "Defect resolved successfully",
            "data": defect
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve defect '{defect_id}': {str(e)}"
        )


@router.post("/{defect_id}/replace")
async def replace_defect_device(
    defect_id: str,
    replace_data: ReplaceDeviceRequest,
    current_user: dict = Depends(require_admin_or_manager)
):
    """Replace a defective device with a new one mapped to the same operator via MAC or serial number"""
    if not replace_data.mac_address and not replace_data.serial_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide mac_address or serial_number for the replacement device"
        )
    try:
        defect = await defect_service.replace_defect_device(
            defect_id=defect_id,
            mac_address=replace_data.mac_address,
            serial_number=replace_data.serial_number,
            notes=replace_data.notes,
            resolver=current_user
        )
        return {
            "success": True,
            "message": "Device replaced successfully and assigned to the original operator",
            "data": defect
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to replace device for defect '{defect_id}': {str(e)}"
        )
