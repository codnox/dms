from datetime import datetime
from app.database import get_db
from app.utils.security import get_password_hash


async def seed_initial_data():
    """Seed initial admin account"""
    async with get_db() as db:
        # Check if admin already exists
        cursor = await db.execute("SELECT id FROM users WHERE role = 'admin'")
        existing_admin = await cursor.fetchone()
        if existing_admin:
            print("📦 Admin already exists, skipping seed")
            return
        
        print("🌱 Creating admin account...")
        
        now = datetime.utcnow().isoformat()
        
        await db.execute(
            """INSERT INTO users (email, password_hash, name, role, phone, department, location,
                status, permissions, theme, compact_mode, email_notifications,
                push_notifications, is_verified, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "admin@dms.com",
                get_password_hash("Admin@123"),
                "System Administrator",
                "admin",
                "+8801700000001",
                "IT",
                "Head Office",
                "active",
                "{}",
                "light",
                0,
                1,
                1,
                1,
                now,
                now
            )
        )
        await db.commit()
        
        print("✅ Admin account created")
        print("\n📋 Admin Credentials:")
        print("=" * 45)
        print(f"{'Role':<15} {'Email':<25} {'Password'}")
        print("-" * 45)
        print(f"{'Admin':<15} {'admin@dms.com':<25} Admin@123")
        print("=" * 45)
        print("🎉 Admin account setup complete!")
        print("ℹ️  Login as admin to create managers, staff, and other users.")


async def reset_and_seed():
    """Drop all tables and re-seed admin account"""
    async with get_db() as db:
        print("🗑️  Clearing all database tables...")
        
        tables = ["notifications", "approvals", "operators", "returns", 
                   "defects", "distributions", "device_history", "devices", "users"]
        
        for table in tables:
            await db.execute(f"DELETE FROM {table}")
            print(f"   Cleared: {table}")
        
        await db.commit()
        print("✅ All tables cleared")
    
    # Re-seed admin
    await seed_initial_data()
    
    return {
        "message": "Database reset and seeded successfully",
        "users_created": 1,
        "tables_cleared": len(tables)
    }
