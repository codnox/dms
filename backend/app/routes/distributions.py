from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import FileResponse
from typing import Optional
from pydantic import BaseModel
from app.models.distribution import DistributionCreate, DistributionStatusUpdate
from app.services import distribution_service
from app.middleware.auth_middleware import get_current_user, require_admin_or_manager, require_management

router = APIRouter()


class ReceiptConfirmation(BaseModel):
    received: bool
    notes: Optional[str] = None


@router.post("/sync-devices")
async def sync_distribution_devices(
    current_user: dict = Depends(require_admin_or_manager)
):
    """Sync device holders for all approved distributions (admin fix endpoint)"""
    try:
        result = await distribution_service.sync_approved_distributions(user=current_user)
        return {
            "success": True,
            "message": f"Synced {result['devices_synced']} device(s) from {result['total_distributions']} approved distribution(s)",
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("")
async def get_distributions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all distributions with pagination and filters"""
    try:
        # Filter by user for non-admin/manager/staff
        user_id = None
        if current_user["role"] not in ["admin", "manager", "staff"]:
            user_id = current_user["id"]

        result = await distribution_service.get_distributions(
            page=page,
            page_size=page_size,
            status=status,
            user_id=user_id,
            search=search
        )

        return {
            "success": True,
            "message": "Distributions retrieved successfully",
            "data": result["data"],
            "pagination": result["pagination"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve distributions: {str(e)}"
        )


@router.get("/pending")
async def get_pending_distributions(
    current_user: dict = Depends(require_management)
):
    """Get pending distributions for approval"""
    try:
        distributions = await distribution_service.get_pending_distributions()

        return {
            "success": True,
            "message": "Pending distributions retrieved successfully",
            "data": distributions
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve pending distributions: {str(e)}"
        )


@router.get("/{distribution_id}/manifest")
async def download_distribution_manifest(
    distribution_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Download generated Excel manifest for a distribution."""
    try:
        manifest = await distribution_service.get_distribution_manifest_file(distribution_id, current_user)
        if not manifest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Distribution manifest not found"
            )

        return FileResponse(
            path=manifest["path"],
            filename=manifest["filename"],
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download manifest for distribution '{distribution_id}': {str(e)}"
        )


@router.get("/{distribution_id}")
async def get_distribution(
    distribution_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get distribution by ID"""
    try:
        distribution = await distribution_service.get_distribution_by_id(distribution_id)

        if not distribution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Distribution not found"
            )

        return {
            "success": True,
            "message": "Distribution retrieved successfully",
            "data": distribution
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve distribution '{distribution_id}': {str(e)}"
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_distribution(
    dist_data: DistributionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new distribution request.
    - admin/manager/staff: can distribute PDIC devices to any sub-level user
    - sub_distributor: can distribute their held devices to clusters or operators under them
    - cluster: can distribute their held devices to operators under them
    - operator: can distribute their held devices to operators in the same cluster
    """
    
    try:
        distribution = await distribution_service.create_distribution(
            dist_data=dist_data,
            from_user=current_user
        )

        return {
            "success": True,
            "message": "Distribution created successfully",
            "data": distribution
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
            detail=f"Failed to create distribution: {str(e)}"
        )


@router.post("/{distribution_id}/receipt")
async def confirm_distribution_receipt(
    distribution_id: str,
    body: ReceiptConfirmation,
    current_user: dict = Depends(get_current_user)
):
    """Recipient confirms or disputes receipt of a distribution.
    - received=true  → Distribution becomes APPROVED; receiver can now redistribute devices
    - received=false → Distribution becomes DISPUTED; admin/manager + sender are notified
    """
    try:
        distribution = await distribution_service.confirm_receipt(
            distribution_id=distribution_id,
            received=body.received,
            user=current_user,
            notes=body.notes
        )
        action = "confirmed" if body.received else "disputed"
        return {
            "success": True,
            "message": f"Receipt {action} successfully",
            "data": distribution
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
            detail=f"Failed to confirm receipt: {str(e)}"
        )


@router.patch("/{distribution_id}/status")
async def update_distribution_status(
    distribution_id: str,
    status_update: DistributionStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update distribution status"""
    try:
        distribution = await distribution_service.update_distribution_status(
            distribution_id=distribution_id,
            status=status_update.status.value,
            user=current_user,
            notes=status_update.notes
        )

        if not distribution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Distribution not found"
            )

        return {
            "success": True,
            "message": "Distribution status updated successfully",
            "data": distribution
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
            detail=f"Failed to update distribution status '{distribution_id}': {str(e)}"
        )


@router.delete("/{distribution_id}")
async def cancel_distribution(
    distribution_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancel a distribution (only by creator)"""
    try:
        success = await distribution_service.cancel_distribution(
            distribution_id=distribution_id,
            user=current_user
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Distribution not found"
            )

        return {
            "success": True,
            "message": "Distribution cancelled successfully"
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
            detail=f"Failed to cancel distribution '{distribution_id}': {str(e)}"
        )
