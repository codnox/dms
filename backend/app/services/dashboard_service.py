from datetime import datetime
from typing import Dict, Any, Optional
from datetime import timedelta

from app.database import get_database
from app.services import device_service, distribution_service, defect_service, return_service, user_service, approval_service, operator_service
from app.utils.helpers import serialize_docs


async def get_dashboard_stats(user: Dict[str, Any]) -> Dict[str, Any]:
    """Get dashboard statistics based on user role"""
    db = get_database()
    role = user.get("role")
    user_id = str(user.get("_id"))
    
    stats = {}
    
    if role in ["admin", "manager"]:
        # Full stats for admin/manager
        device_stats = await device_service.get_device_stats()
        dist_stats = await distribution_service.get_distribution_stats()
        defect_stats = await defect_service.get_defect_stats()
        return_stats = await return_service.get_return_stats()
        user_stats = await user_service.get_user_stats()
        approval_stats = await approval_service.get_approval_stats()
        
        # Calculate this month's distributions
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)
        distributions_this_month = await db.distributions.count_documents({
            "created_at": {"$gte": month_start}
        })
        
        # Flatten stats for easy frontend access
        stats = {
            # Device stats (flattened)
            "total_devices": device_stats.get("total", 0),
            "available_devices": device_stats.get("available", 0),
            "distributed_devices": device_stats.get("distributed", 0),
            "in_use_devices": device_stats.get("in_use", 0),
            "defective_devices": device_stats.get("defective", 0),
            "returned_devices": device_stats.get("returned", 0),
            # Active devices = available + distributed + in_use (not defective or returned)
            "active_devices": (
                device_stats.get("available", 0) + 
                device_stats.get("distributed", 0) + 
                device_stats.get("in_use", 0)
            ),
            
            # Distribution stats (flattened)
            "total_distributions": dist_stats.get("total", 0),
            "pending_distributions": dist_stats.get("pending", 0),
            "approved_distributions": dist_stats.get("approved", 0),
            "delivered_distributions": dist_stats.get("delivered", 0),
            "rejected_distributions": dist_stats.get("rejected", 0),
            "distribution_this_month": distributions_this_month,
            
            # Defect stats (flattened)
            "total_defects": defect_stats.get("total", 0),
            "defect_reports": defect_stats.get("total", 0),  # Alias for compatibility
            "reported_defects": defect_stats.get("by_status", {}).get("reported", 0),
            "under_review_defects": defect_stats.get("by_status", {}).get("under_review", 0),
            "resolved_defects": defect_stats.get("by_status", {}).get("resolved", 0),
            
            # Return stats (flattened)
            "total_returns": return_stats.get("total", 0),
            "return_requests": return_stats.get("total", 0),  # Alias for compatibility
            "pending_returns": return_stats.get("by_status", {}).get("pending", 0),
            "approved_returns": return_stats.get("by_status", {}).get("approved", 0),
            "received_returns": return_stats.get("by_status", {}).get("received", 0),
            "rejected_returns": return_stats.get("by_status", {}).get("rejected", 0),
            
            # User stats (flattened)
            "total_users": user_stats.get("total", 0),
            "active_users": user_stats.get("active", 0),
            
            # Approval stats (flattened)
            "pending_approvals": approval_stats.get("total_pending", 0),
            "total_approved": approval_stats.get("approved", 0),
            "total_rejected": approval_stats.get("rejected", 0),
            
            # Also include nested objects for detailed breakdowns if needed
            "devices": device_stats,
            "distributions": dist_stats,
            "defects": defect_stats,
            "returns": return_stats,
            "users": user_stats,
            "approvals": approval_stats
        }
    
    elif role == "distributor":
        # Stats for distributor
        # Devices they have
        my_devices = await db.devices.count_documents({"current_holder_id": user_id})
        available_devices = await db.devices.count_documents({"current_holder_id": user_id, "status": "available"})
        
        # Distributions
        sent = await db.distributions.count_documents({"from_user_id": user_id})
        received = await db.distributions.count_documents({"to_user_id": user_id})
        pending = await db.distributions.count_documents({"from_user_id": user_id, "status": "pending"})
        
        stats = {
            "my_devices": my_devices,
            "available_devices": available_devices,
            "distributions_sent": sent,
            "distributions_received": received,
            "pending_distributions": pending
        }
    
    elif role == "sub_distributor":
        # Stats for sub-distributor
        my_devices = await db.devices.count_documents({"current_holder_id": user_id})
        operator_stats = await operator_service.get_operator_stats(user_id)
        
        # Distributions
        sent = await db.distributions.count_documents({"from_user_id": user_id})
        received = await db.distributions.count_documents({"to_user_id": user_id})
        
        stats = {
            "my_devices": my_devices,
            "operators": operator_stats,
            "distributions_sent": sent,
            "distributions_received": received
        }
    
    elif role == "operator":
        # Stats for operator
        my_devices = await db.devices.count_documents({"current_holder_id": user_id})
        my_defects = await db.defects.count_documents({"reported_by": user_id})
        my_returns = await db.returns.count_documents({"requested_by": user_id})
        
        stats = {
            "my_devices": my_devices,
            "my_defects": my_defects,
            "my_returns": my_returns
        }
    
    return stats


async def get_recent_activities(user: Dict[str, Any], limit: int = 10) -> list:
    """Get recent activities based on user role"""
    db = get_database()
    role = user.get("role")
    user_id = str(user.get("_id"))
    
    activities = []
    
    if role in ["admin", "manager"]:
        # Get recent device history
        cursor = db.device_history.find({}).sort("timestamp", -1).limit(limit)
        history = await cursor.to_list(length=limit)
        
        for h in history:
            activities.append({
                "id": str(h["_id"]),
                "action": h["action"],
                "description": f"{h.get('performed_by_name', 'Unknown')} {h['action']} device",
                "user_name": h.get("performed_by_name", "Unknown"),
                "timestamp": h["timestamp"],
                "category": "device",
                "link": None
            })
    else:
        # Get activities related to this user
        cursor = db.device_history.find({
            "$or": [
                {"performed_by": user_id},
                {"from_user_id": user_id},
                {"to_user_id": user_id}
            ]
        }).sort("timestamp", -1).limit(limit)
        history = await cursor.to_list(length=limit)
        
        for h in history:
            activities.append({
                "id": str(h["_id"]),
                "action": h["action"],
                "description": f"{h['action'].replace('_', ' ').title()}",
                "user_name": h.get("performed_by_name", "Unknown"),
                "timestamp": h["timestamp"],
                "category": "device",
                "link": None
            })
    
    return activities


async def get_distribution_chart_data() -> list:
    """Get distribution data for charts"""
    db = get_database()
    
    from datetime import timedelta
    
    data = []
    now = datetime.utcnow()
    
    for i in range(11, -1, -1):
        month_start = datetime(now.year, now.month, 1) - timedelta(days=i*30)
        month_end = month_start + timedelta(days=30)
        
        count = await db.distributions.count_documents({
            "status": "delivered",
            "created_at": {"$gte": month_start, "$lt": month_end}
        })
        
        data.append({
            "month": month_start.strftime("%b"),
            "distributions": count
        })
    
    return data


async def get_defect_chart_data() -> list:
    """Get defect data for charts"""
    db = get_database()
    
    from datetime import timedelta
    
    data = []
    now = datetime.utcnow()
    
    for i in range(11, -1, -1):
        month_start = datetime(now.year, now.month, 1) - timedelta(days=i*30)
        month_end = month_start + timedelta(days=30)
        
        reported = await db.defects.count_documents({
            "created_at": {"$gte": month_start, "$lt": month_end}
        })
        resolved = await db.defects.count_documents({
            "status": "resolved",
            "resolved_at": {"$gte": month_start, "$lt": month_end}
        })
        
        data.append({
            "month": month_start.strftime("%b"),
            "reported": reported,
            "resolved": resolved
        })
    
    return data


async def get_system_alerts(user: Dict[str, Any]) -> list:
    """Get system alerts for dashboard"""
    db = get_database()
    role = user.get("role")
    
    alerts = []
    
    if role in ["admin", "manager"]:
        # Critical defects
        critical_defects = await db.defects.count_documents({
            "severity": "critical",
            "status": {"$ne": "resolved"}
        })
        if critical_defects > 0:
            alerts.append({
                "type": "error",
                "title": "Critical Defects",
                "message": f"{critical_defects} critical defect(s) require attention",
                "link": "/defects?severity=critical"
            })
        
        # Pending approvals
        pending_approvals = await db.approvals.count_documents({"status": "pending"})
        if pending_approvals > 0:
            alerts.append({
                "type": "warning",
                "title": "Pending Approvals",
                "message": f"{pending_approvals} request(s) waiting for approval",
                "link": "/approvals"
            })
        
        # Low device stock
        available_devices = await db.devices.count_documents({"status": "available"})
        if available_devices < 10:
            alerts.append({
                "type": "warning",
                "title": "Low Device Stock",
                "message": f"Only {available_devices} devices available in stock",
                "link": "/devices"
            })
    
    return alerts
