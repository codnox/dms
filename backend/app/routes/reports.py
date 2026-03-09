from fastapi import APIRouter, HTTPException, status, Depends
from app.services import report_service
from app.middleware.auth_middleware import require_admin_or_manager

router = APIRouter()


@router.get("/inventory")
async def get_inventory_report(
    current_user: dict = Depends(require_admin_or_manager)
):
    """Get device inventory report"""
    try:
        report = await report_service.get_inventory_report()

        return {
            "success": True,
            "message": "Inventory report generated successfully",
            "data": report
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate inventory report: {str(e)}"
        )


@router.get("/distribution-summary")
async def get_distribution_summary(
    current_user: dict = Depends(require_admin_or_manager)
):
    """Get distribution summary report"""
    try:
        report = await report_service.get_distribution_summary()

        return {
            "success": True,
            "message": "Distribution summary generated successfully",
            "data": report
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate distribution summary: {str(e)}"
        )


@router.get("/defect-summary")
async def get_defect_summary(
    current_user: dict = Depends(require_admin_or_manager)
):
    """Get defect summary report"""
    try:
        report = await report_service.get_defect_summary()

        return {
            "success": True,
            "message": "Defect summary generated successfully",
            "data": report
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate defect summary: {str(e)}"
        )


@router.get("/return-summary")
async def get_return_summary(
    current_user: dict = Depends(require_admin_or_manager)
):
    """Get return summary report"""
    try:
        report = await report_service.get_return_summary()

        return {
            "success": True,
            "message": "Return summary generated successfully",
            "data": report
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate return summary: {str(e)}"
        )


@router.get("/user-activity")
async def get_user_activity_report(
    current_user: dict = Depends(require_admin_or_manager)
):
    """Get user activity report"""
    try:
        report = await report_service.get_user_activity_report()

        return {
            "success": True,
            "message": "User activity report generated successfully",
            "data": report
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate user activity report: {str(e)}"
        )


@router.get("/device-utilization")
async def get_device_utilization_report(
    current_user: dict = Depends(require_admin_or_manager)
):
    """Get device utilization report"""
    try:
        report = await report_service.get_device_utilization_report()

        return {
            "success": True,
            "message": "Device utilization report generated successfully",
            "data": report
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate device utilization report: {str(e)}"
        )


@router.post("/export")
async def export_report(
    export_data: dict,
    current_user: dict = Depends(require_admin_or_manager)
):
    """Export report (placeholder for actual export functionality)"""
    try:
        report_type = export_data.get("report_type", "inventory")
        format_type = export_data.get("format", "csv")

        return {
            "success": True,
            "message": f"{report_type} report exported as {format_type}",
            "data": {
                "report_type": report_type,
                "format": format_type,
                "download_url": f"/api/reports/download/{report_type}.{format_type}"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export report: {str(e)}"
        )
