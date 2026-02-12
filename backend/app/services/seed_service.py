from datetime import datetime
from app.database import get_database
from app.utils.security import get_password_hash


async def seed_initial_data():
    """Seed initial user accounts"""
    db = get_database()
    
    # Check if admin already exists
    existing_admin = await db.users.find_one({"role": "admin"})
    if existing_admin:
        print("📦 Users already exist, skipping seed")
        return
    
    print("🌱 Creating user accounts...")
    
    now = datetime.utcnow()
    
    users_to_create = [
        # Admin
        {
            "email": "admin@dms.com",
            "password_hash": get_password_hash("Admin@123"),
            "name": "System Administrator",
            "role": "admin",
            "phone": "+8801700000001",
            "department": "IT",
            "location": "Head Office - Dhaka",
            "status": "active",
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        },
        # Manager 1
        {
            "email": "manager1@dms.com",
            "password_hash": get_password_hash("Manager@123"),
            "name": "Rafiq Ahmed",
            "role": "manager",
            "phone": "+8801700000002",
            "department": "Operations",
            "location": "Dhaka - Gulshan",
            "status": "active",
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        },
        # Manager 2
        {
            "email": "manager2@dms.com",
            "password_hash": get_password_hash("Manager@123"),
            "name": "Nusrat Jahan",
            "role": "manager",
            "phone": "+8801700000003",
            "department": "Technical Support",
            "location": "Dhaka - Dhanmondi",
            "status": "active",
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        },
        # Manager 3
        {
            "email": "manager3@dms.com",
            "password_hash": get_password_hash("Manager@123"),
            "name": "Kamal Hossain",
            "role": "manager",
            "phone": "+8801700000004",
            "department": "Sales",
            "location": "Chittagong - Agrabad",
            "status": "active",
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        },
        # Distributor 1
        {
            "email": "distributor1@dms.com",
            "password_hash": get_password_hash("Dist@123"),
            "name": "Shahid Alam",
            "role": "distributor",
            "phone": "+8801700000005",
            "department": "Logistics",
            "location": "Dhaka - Mirpur",
            "status": "active",
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        },
        # Sub-Distributor 1
        {
            "email": "subdist1@dms.com",
            "password_hash": get_password_hash("SubDist@123"),
            "name": "Arif Rahman",
            "role": "sub-distributor",
            "phone": "+8801700000006",
            "department": "Field Operations",
            "location": "Dhaka - Uttara",
            "status": "active",
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        },
        # Sub-Distributor 2
        {
            "email": "subdist2@dms.com",
            "password_hash": get_password_hash("SubDist@123"),
            "name": "Fatema Begum",
            "role": "sub-distributor",
            "phone": "+8801700000007",
            "department": "Field Operations",
            "location": "Chittagong - Panchlaish",
            "status": "active",
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        },
        # Sub-Distributor 3
        {
            "email": "subdist3@dms.com",
            "password_hash": get_password_hash("SubDist@123"),
            "name": "Tanvir Hasan",
            "role": "sub-distributor",
            "phone": "+8801700000008",
            "department": "Field Operations",
            "location": "Sylhet - Zindabazar",
            "status": "active",
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        },
        # Sub-Distributor 4
        {
            "email": "subdist4@dms.com",
            "password_hash": get_password_hash("SubDist@123"),
            "name": "Razia Sultana",
            "role": "sub-distributor",
            "phone": "+8801700000009",
            "department": "Field Operations",
            "location": "Rajshahi - Shaheb Bazar",
            "status": "active",
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        },
        # Sub-Distributor 5
        {
            "email": "subdist5@dms.com",
            "password_hash": get_password_hash("SubDist@123"),
            "name": "Imran Khan",
            "role": "sub-distributor",
            "phone": "+8801700000010",
            "department": "Field Operations",
            "location": "Khulna - Sonadanga",
            "status": "active",
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        },
        # Operator 1
        {
            "email": "operator1@dms.com",
            "password_hash": get_password_hash("Oper@123"),
            "name": "Masud Rana",
            "role": "operator",
            "phone": "+8801700000011",
            "department": "Customer Service",
            "location": "Dhaka - Uttara",
            "status": "active",
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        },
        # Operator 2
        {
            "email": "operator2@dms.com",
            "password_hash": get_password_hash("Oper@123"),
            "name": "Sadia Islam",
            "role": "operator",
            "phone": "+8801700000012",
            "department": "Customer Service",
            "location": "Chittagong - Panchlaish",
            "status": "active",
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        },
        # Operator 3
        {
            "email": "operator3@dms.com",
            "password_hash": get_password_hash("Oper@123"),
            "name": "Jubayer Ali",
            "role": "operator",
            "phone": "+8801700000013",
            "department": "Customer Service",
            "location": "Sylhet - Zindabazar",
            "status": "active",
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        },
        # Operator 4
        {
            "email": "operator4@dms.com",
            "password_hash": get_password_hash("Oper@123"),
            "name": "Mithila Akter",
            "role": "operator",
            "phone": "+8801700000014",
            "department": "Customer Service",
            "location": "Rajshahi - Shaheb Bazar",
            "status": "active",
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        },
        # Operator 5
        {
            "email": "operator5@dms.com",
            "password_hash": get_password_hash("Oper@123"),
            "name": "Shakib Hasan",
            "role": "operator",
            "phone": "+8801700000015",
            "department": "Customer Service",
            "location": "Khulna - Sonadanga",
            "status": "active",
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        },
    ]
    
    result = await db.users.insert_many(users_to_create)
    print(f"✅ Created {len(result.inserted_ids)} user accounts")
    
    print("\n📋 User Credentials:")
    print("=" * 55)
    print(f"{'Role':<20} {'Email':<25} {'Password'}")
    print("-" * 55)
    print(f"{'Admin':<20} {'admin@dms.com':<25} Admin@123")
    print(f"{'Manager 1':<20} {'manager1@dms.com':<25} Manager@123")
    print(f"{'Manager 2':<20} {'manager2@dms.com':<25} Manager@123")
    print(f"{'Manager 3':<20} {'manager3@dms.com':<25} Manager@123")
    print(f"{'Distributor':<20} {'distributor1@dms.com':<25} Dist@123")
    print(f"{'Sub-Dist 1':<20} {'subdist1@dms.com':<25} SubDist@123")
    print(f"{'Sub-Dist 2':<20} {'subdist2@dms.com':<25} SubDist@123")
    print(f"{'Sub-Dist 3':<20} {'subdist3@dms.com':<25} SubDist@123")
    print(f"{'Sub-Dist 4':<20} {'subdist4@dms.com':<25} SubDist@123")
    print(f"{'Sub-Dist 5':<20} {'subdist5@dms.com':<25} SubDist@123")
    print(f"{'Operator 1':<20} {'operator1@dms.com':<25} Oper@123")
    print(f"{'Operator 2':<20} {'operator2@dms.com':<25} Oper@123")
    print(f"{'Operator 3':<20} {'operator3@dms.com':<25} Oper@123")
    print(f"{'Operator 4':<20} {'operator4@dms.com':<25} Oper@123")
    print(f"{'Operator 5':<20} {'operator5@dms.com':<25} Oper@123")
    print("=" * 55)
    
    print("🎉 User accounts setup complete!")


async def reset_and_seed():
    """Drop all collections and re-seed users"""
    db = get_database()
    
    print("🗑️  Clearing all database collections...")
    
    collections = await db.list_collection_names()
    for collection_name in collections:
        await db.drop_collection(collection_name)
        print(f"   Dropped: {collection_name}")
    
    print("✅ All collections cleared")
    
    # Re-seed users
    await seed_initial_data()
    
    return {
        "message": "Database reset and seeded successfully",
        "users_created": 15,
        "collections_cleared": len(collections)
    }
