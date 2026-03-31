from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional
from app.models.defect import (
    DefectCreate,
    DefectUpdate,
    DefectResolve,
    DefectStatusUpdate,
    ReplaceDeviceRequest,
    ReplacementConfirmationRequest,
    DefectEnquiryRequest,
    DefectActionRequest,
)
from app.services import defect_service
from app.middleware.auth_middleware import get_current_user, require_admin_or_manager, require_management, require_any_role

router = APIRouter()


@router.get("/replacements")
async def get_replacement_defects(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=300),
    current_user: dict = Depends(require_any_role)
):
    """Get all replacement mappings (defects with replacement_device_id), scoped by hierarchy."""
    try:
        result = await defect_service.get_replacement_defects(
            current_user=current_user,
            page=page,
            page_size=page_size
        )

        return {
            "success": True,
            "message": "Replacement mappings retrieved successfully",
            "data": result["data"],
            "pagination": result["pagination"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve replacement mappings: {str(e)}"
        )


@router.get("/replacements/pending")
async def get_pending_replacement_defects(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=300),
    current_user: dict = Depends(require_any_role)
):
    """Get defective devices waiting for replacement assignment."""
    try:
        result = await defect_service.get_pending_replacement_defects(
            current_user=current_user,
            page=page,
            page_size=page_size
        )

        return {
            "success": True,
            "message": "Pending replacement defects retrieved successfully",
            "data": result["data"],
            "pagination": result["pagination"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve pending replacement defects: {str(e)}"
        )


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
        # Determine scope based on user role.
        # Always cast id to str to avoid SQLite integer/text type mismatches (422 cause).
        user_id_str = str(current_user["id"])
        reported_by = None
        holder_user_id = None

        role = current_user.get("role", "")
        if role == "operator":
            # holder_user_id condition in the service already covers:
            # "defects reported by me" OR "defects where my device is the holder"
            # Setting both reported_by AND holder_user_id would AND them, over-filtering.
            holder_user_id = user_id_str
        elif role == "cluster":
            # Show defects for devices in their possession or under their hierarchy
            holder_user_id = user_id_str
        elif role == "sub_distributor":
            # Sub distributor visibility is handled by service-side hierarchy filters.
            # Do not set reported_by here, otherwise results are over-filtered to self-only.
            pass
        elif role not in ["admin", "manager", "staff"]:
            # Any other non-management role: show only their own reported defects
            reported_by = user_id_str

        result = await defect_service.get_defects(
            page=page,
            page_size=page_size,
            status=status,
            severity=severity,
            defect_type=defect_type,
            reported_by=reported_by,
            holder_user_id=holder_user_id,
            search=search,
            visibility_user=current_user
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


@router.post("/{defect_id}/forward-to-management")
async def forward_defect_to_management(
    defect_id: str,
    action_data: DefectActionRequest,
    current_user: dict = Depends(require_any_role)
):
    """Allow sub distributor to forward a routed defect to manager/admin queue."""
    try:
        defect = await defect_service.forward_defect_to_management(
            defect_id=defect_id,
            forwarder=current_user,
            notes=action_data.notes
        )
        return {
            "success": True,
            "message": "Defect forwarded to manager/admin successfully",
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
            detail=f"Failed to forward defect '{defect_id}': {str(e)}"
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
    current_user: dict = Depends(require_management)
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
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
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
    current_user: dict = Depends(require_management)
):
    """Replace a defective device by selecting an existing device or registering a new one."""
    if not any([
        replace_data.replacement_device_id,
        replace_data.mac_address,
        replace_data.serial_number,
        replace_data.register_device
    ]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide replacement_device_id, mac_address, serial_number, or register_device"
        )
    try:
        defect = await defect_service.replace_defect_device(
            defect_id=defect_id,
            replacement_device_id=replace_data.replacement_device_id,
            mac_address=replace_data.mac_address,
            serial_number=replace_data.serial_number,
            register_device=replace_data.register_device.model_dump() if replace_data.register_device else None,
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


@router.post("/{defect_id}/replacement/confirm")
async def confirm_replacement_receipt(
    defect_id: str,
    confirmation_data: ReplacementConfirmationRequest,
    current_user: dict = Depends(require_any_role)
):
    """Confirm replacement device receipt (operator confirmation)."""
    try:
        defect = await defect_service.confirm_replacement_receipt(
            defect_id=defect_id,
            confirmer=current_user,
            notes=confirmation_data.notes
        )
        return {
            "success": True,
            "message": "Replacement receipt confirmed successfully",
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
            detail=f"Failed to confirm replacement receipt for defect '{defect_id}': {str(e)}"
        )


@router.post("/{defect_id}/enquire")
async def enquire_replacement_status(
    defect_id: str,
    enquiry_data: DefectEnquiryRequest,
    current_user: dict = Depends(require_any_role)
):
    """Operator sends replacement-status enquiry to management users."""
    if current_user.get("role") not in {"operator", "cluster", "sub_distributor"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only operator, cluster, or sub distributor users can send replacement enquiries"
        )

    try:
        defect = await defect_service.enquire_replacement_status(
            defect_id=defect_id,
            enquirer=current_user,
            message=enquiry_data.message
        )
        return {
            "success": True,
            "message": "Replacement enquiry sent successfully",
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
            detail=f"Failed to send replacement enquiry for defect '{defect_id}': {str(e)}"
        )


@router.post("/{defect_id}/resend-confirmation")
async def resend_replacement_confirmation(
    defect_id: str,
    current_user: dict = Depends(require_management)
):
    """Resend replacement confirmation reminder to the operator."""
    try:
        defect = await defect_service.resend_replacement_confirmation(
            defect_id=defect_id,
            sender=current_user
        )
        return {
            "success": True,
            "message": "Replacement confirmation resent successfully",
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
            detail=f"Failed to resend replacement confirmation for defect '{defect_id}': {str(e)}"
        )


@router.post("/{defect_id}/mark-waiting")
async def mark_replacement_waiting(
    defect_id: str,
    action_data: DefectActionRequest,
    current_user: dict = Depends(require_management)
):
    """Mark replacement status as waiting for PDIC shipment."""
    try:
        defect = await defect_service.mark_replacement_waiting(
            defect_id=defect_id,
            manager=current_user,
            notes=action_data.notes
        )
        return {
            "success": True,
            "message": "Replacement status updated to waiting",
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
            detail=f"Failed to mark replacement waiting for defect '{defect_id}': {str(e)}"
        )
