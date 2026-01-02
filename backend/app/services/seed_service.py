from datetime import datetime, timedelta
import random
from app.database import get_database
from app.utils.security import get_password_hash


# Real company names, device manufacturers, and locations
DEVICE_MANUFACTURERS = ["Huawei", "ZTE", "Nokia", "Cisco", "TP-Link", "D-Link", "Ubiquiti", "Aruba"]
DEVICE_MODELS = {
    "ONU": ["HG8310M", "HG8546M", "MA5671", "F601", "F660", "EG8145V5"],
    "ONT": ["ZTE F670L", "Nokia G-010G-P", "Huawei EG8145X6", "ZTE F680"],
    "Router": ["Archer AX55", "RT-AX86U", "DIR-882", "UAP-AC-PRO"],
    "Modem": ["SB8200", "MB8600", "CM1000", "TC4400"]
}

LOCATIONS = [
    "Dhaka - Gulshan", "Dhaka - Dhanmondi", "Dhaka - Mirpur", "Dhaka - Uttara",
    "Chittagong - Agrabad", "Chittagong - Panchlaish", "Sylhet - Zindabazar",
    "Rajshahi - Shaheb Bazar", "Khulna - Sonadanga", "Barisal - Sadar",
    "Rangpur - Jahaj Company More", "Comilla - Kandirpar", "Narayanganj - Chasara",
    "Gazipur - Tongi", "Cox's Bazar - Kolatoli"
]

DEPARTMENTS = ["Operations", "Technical Support", "Sales", "Logistics", "Customer Service", "Field Operations"]

DISTRIBUTION_NOTES = [
    "Urgent deployment for new area coverage",
    "Routine monthly distribution",
    "Emergency replacement for faulty devices",
    "Expansion project Phase 2",
    "Customer demand fulfillment",
    "Warehouse stock replenishment"
]

DEFECT_TYPES = [
    "Hardware Failure", "Software Malfunction", "Physical Damage", 
    "Network Connectivity Issues", "Power Supply Failure", "Configuration Error"
]

DEFECT_DESCRIPTIONS = [
    "Device not powering on after recent power outage",
    "Intermittent network disconnections reported",
    "Physical damage to housing - crack on top panel",
    "Unable to establish PPPoE connection",
    "LED indicators not functioning properly",
    "Device overheating during operation",
    "Port malfunction - Ethernet ports not working",
    "Firmware update failed - device bricked"
]


async def seed_initial_data():
    """Seed initial admin account"""
    db = get_database()
    
    # Check if admin already exists
    existing_admin = await db.users.find_one({"role": "admin"})
    if existing_admin:
        print("📦 Admin account already exists, skipping seed")
        return
    
    print("🌱 Creating admin account...")
    
    now = datetime.utcnow()
    
    # Create admin user
    admin_user = {
        "email": "admin@dms.com",
        "password_hash": get_password_hash("admin123"),
        "name": "System Administrator",
        "role": "admin",
        "phone": "+1234567890",
        "department": "IT",
        "location": "Head Office",
        "status": "active",
        "is_verified": True,
        "created_at": now,
        "updated_at": now,
        "last_login": None
    }
    
    result = await db.users.insert_one(admin_user)
    print(f"✅ Admin account created: admin@dms.com / admin123")
    
    # Get admin for reference
    admin = await db.users.find_one({"email": "admin@dms.com"})
    
    print("🎉 Admin account setup complete!")
