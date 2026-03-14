from fastapi import APIRouter, HTTPException, status, Depends
from app.services import dashboard_service
from app.middleware.auth_middleware import get_current_user

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user)
):
    """Get dashboard statistics based on user role"""
    try:
        stats = await dashboard_service.get_dashboard_stats(current_user)

        return {
            "success": True,
            "message": "Dashboard stats retrieved successfully",
            "data": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard stats: {str(e)}"
        )


@router.get("/recent-activities")
async def get_recent_activities(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get recent activities for dashboard"""
    try:
        activities = await dashboard_service.get_recent_activities(current_user, limit)

        return {
            "success": True,
            "message": "Recent activities retrieved successfully",
            "data": activities
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recent activities: {str(e)}"
        )


@router.get("/charts/distributions")
async def get_distribution_chart_data(
    current_user: dict = Depends(get_current_user)
):
    """Get distribution chart data"""
    try:
        data = await dashboard_service.get_distribution_chart_data()

        return {
            "success": True,
            "message": "Distribution chart data retrieved successfully",
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve distribution chart data: {str(e)}"
        )


@router.get("/charts/defects")
async def get_defect_chart_data(
    current_user: dict = Depends(get_current_user)
):
    """Get defect chart data"""
    try:
        data = await dashboard_service.get_defect_chart_data()

        return {
            "success": True,
            "message": "Defect chart data retrieved successfully",
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve defect chart data: {str(e)}"
        )


@router.get("/alerts")
async def get_system_alerts(
    current_user: dict = Depends(get_current_user)
):
    """Get system alerts for dashboard"""
    try:
        alerts = await dashboard_service.get_system_alerts(current_user)

        return {
            "success": True,
            "message": "System alerts retrieved successfully",
            "data": alerts
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve system alerts: {str(e)}"
        )


@router.get("/advanced-metrics")
async def get_advanced_dashboard_metrics(
    current_user: dict = Depends(get_current_user)
):
    """Get advanced management analytics for graph-heavy dashboards."""
    try:
        data = await dashboard_service.get_advanced_dashboard_metrics(current_user)

        return {
            "success": True,
            "message": "Advanced dashboard metrics retrieved successfully",
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve advanced dashboard metrics: {str(e)}"
        )
