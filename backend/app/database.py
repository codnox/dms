import aiosqlite
import json
from contextlib import asynccontextmanager
from app.config import settings


DB_PATH = settings.DATABASE_PATH


@asynccontextmanager
async def get_db():
    """Get an async SQLite database connection"""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    """Initialize database tables"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()
    print(f"✅ SQLite database initialized at: {DB_PATH}")


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    phone TEXT,
    department TEXT,
    location TEXT,
    status TEXT DEFAULT 'active',
    parent_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    permissions TEXT DEFAULT '{}',
    theme TEXT DEFAULT 'light',
    compact_mode INTEGER DEFAULT 0,
    email_notifications INTEGER DEFAULT 1,
    push_notifications INTEGER DEFAULT 1,
    is_verified INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_login TEXT,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT UNIQUE NOT NULL,
    device_type TEXT NOT NULL,
    model TEXT NOT NULL,
    serial_number TEXT UNIQUE NOT NULL,
    mac_address TEXT UNIQUE NOT NULL,
    manufacturer TEXT NOT NULL,
    status TEXT DEFAULT 'available',
    current_location TEXT,
    current_holder_id TEXT,
    current_holder_name TEXT,
    current_holder_type TEXT,
    purchase_date TEXT,
    warranty_expiry TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS device_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    action TEXT NOT NULL,
    from_user_id TEXT,
    from_user_name TEXT,
    to_user_id TEXT,
    to_user_name TEXT,
    status_before TEXT,
    status_after TEXT,
    location TEXT,
    notes TEXT,
    performed_by TEXT,
    performed_by_name TEXT,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS distributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    distribution_id TEXT UNIQUE NOT NULL,
    device_ids TEXT NOT NULL,
    device_count INTEGER DEFAULT 0,
    from_user_id TEXT NOT NULL,
    from_user_name TEXT,
    from_user_type TEXT,
    to_user_id TEXT NOT NULL,
    to_user_name TEXT,
    to_user_type TEXT,
    status TEXT DEFAULT 'pending',
    request_date TEXT NOT NULL,
    approval_date TEXT,
    delivery_date TEXT,
    notes TEXT,
    approved_by TEXT,
    approved_by_name TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS defects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT UNIQUE NOT NULL,
    device_id TEXT NOT NULL,
    device_serial TEXT,
    device_type TEXT,
    reported_by TEXT NOT NULL,
    reported_by_name TEXT,
    defect_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    description TEXT NOT NULL,
    symptoms TEXT,
    status TEXT DEFAULT 'reported',
    resolution TEXT,
    resolved_by TEXT,
    resolved_by_name TEXT,
    resolved_at TEXT,
    images TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_id TEXT UNIQUE NOT NULL,
    device_id TEXT NOT NULL,
    device_serial TEXT,
    device_type TEXT,
    requested_by TEXT NOT NULL,
    requested_by_name TEXT,
    return_to TEXT,
    return_to_name TEXT,
    reason TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',
    request_date TEXT NOT NULL,
    approval_date TEXT,
    received_date TEXT,
    approved_by TEXT,
    approved_by_name TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    approval_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    requested_by_name TEXT,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
    request_date TEXT NOT NULL,
    approved_by TEXT,
    approved_by_name TEXT,
    approval_date TEXT,
    rejection_reason TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS operators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operator_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    address TEXT,
    area TEXT,
    city TEXT,
    assigned_to TEXT NOT NULL,
    assigned_to_name TEXT,
    status TEXT DEFAULT 'active',
    device_count INTEGER DEFAULT 0,
    connection_type TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'info',
    category TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    link TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS change_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT UNIQUE NOT NULL,
    requested_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    requested_by_name TEXT NOT NULL,
    requested_by_role TEXT NOT NULL,
    request_type TEXT NOT NULL,
    new_email TEXT,
    new_password TEXT,
    reason TEXT,
    status TEXT DEFAULT 'pending',
    reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_by_name TEXT,
    review_note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def row_to_dict(row):
    """Convert an aiosqlite Row to a dict with string id"""
    if row is None:
        return None
    d = dict(row)
    d["_id"] = str(d["id"])
    d["id"] = str(d["id"])
    # Convert boolean fields
    for key in ["compact_mode", "email_notifications", "push_notifications", "is_verified", "is_read"]:
        if key in d:
            d[key] = bool(d[key])
    return d


def rows_to_list(rows):
    """Convert a list of aiosqlite Rows to list of dicts"""
    return [row_to_dict(r) for r in rows if r is not None]
