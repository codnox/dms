from datetime import datetime, timezone
import os
import secrets
import string

from app.config import settings
from app.database import get_db
from app.utils.security import get_password_hash


def generate_secure_password(length: int = 16) -> str:
    """Generate a strong random password for initial admin provisioning."""
    if length < 12:
        length = 12

    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%^&*()"
    alphabet = lowercase + uppercase + digits + symbols

    # Ensure minimum complexity, then fill remaining chars randomly.
    password_chars = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(symbols),
    ]
    password_chars.extend(secrets.choice(alphabet) for _ in range(length - 4))
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


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
        admin_password = os.getenv("ADMIN_INITIAL_PASSWORD") or generate_secure_password()
        
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        
        await db.execute(
            """INSERT INTO users (email, password_hash, name, role, phone, department, location,
                status, permissions, theme, compact_mode, email_notifications,
                push_notifications, is_verified, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "admin@dms.com",
                get_password_hash(admin_password),
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
        if settings.ENVIRONMENT == "development":
            print("\n📋 Admin Credentials:")
            print("=" * 45)
            print(f"{'Role':<15} {'Email':<25} {'Password'}")
            print("-" * 45)
            print(f"{'Admin':<15} {'admin@dms.com':<25} {admin_password}")
            print("=" * 45)
            print("⚠️  Change this password immediately after first login!")
        else:
            print("ℹ️  Initial admin account created. Set ADMIN_INITIAL_PASSWORD to control first-run credentials.")
        print("🎉 Admin account setup complete!")
        print("ℹ️  Login as admin to create managers, staff, and other users.")


async def reset_and_seed():
    """Drop all tables and re-seed admin account"""
    async with get_db() as db:
        print("🗑️  Clearing all database tables...")
        
        tables = [
            "inventory_stock_movements",
            "inventory_receipt_lines",
            "inventory_receipts",
            "inventory_po_lines",
            "inventory_purchase_orders",
            "external_inventory_items",
            "change_requests",
            "notifications",
            "approvals",
            "operators",
            "returns",
            "defects",
            "distributions",
            "device_history",
            "devices",
            "users",
        ]
        
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
