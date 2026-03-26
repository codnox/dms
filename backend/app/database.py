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
        # Migrations: add new columns if they don't exist yet
        for stmt in [
            "ALTER TABLE change_requests ADD COLUMN device_id TEXT",
            "ALTER TABLE change_requests ADD COLUMN requested_status TEXT",
            "ALTER TABLE devices ADD COLUMN registered_by_name TEXT",
            "ALTER TABLE returns ADD COLUMN defect_id TEXT",
            "ALTER TABLE defects ADD COLUMN auto_return_id TEXT",
            "ALTER TABLE defects ADD COLUMN replacement_device_id TEXT",
            "ALTER TABLE defects ADD COLUMN replacement_requested_at TEXT",
            "ALTER TABLE defects ADD COLUMN replacement_confirmed_at TEXT",
            "ALTER TABLE defects ADD COLUMN replacement_confirmed_by TEXT",
            "ALTER TABLE defects ADD COLUMN replacement_confirmed_by_name TEXT",
            "ALTER TABLE returns ADD COLUMN mac_address TEXT",
            "ALTER TABLE devices ADD COLUMN band_type TEXT",
            "ALTER TABLE devices ADD COLUMN nuid TEXT",
            "ALTER TABLE external_inventory_items ADD COLUMN item_id TEXT",
            "ALTER TABLE external_inventory_items ADD COLUMN serial_number TEXT",
            "ALTER TABLE external_inventory_items ADD COLUMN mac_id TEXT",
            "ALTER TABLE external_inventory_items ADD COLUMN device_type TEXT",
            "ALTER TABLE external_inventory_items ADD COLUMN price REAL DEFAULT 0",
            "ALTER TABLE external_inventory_items ADD COLUMN image_url TEXT",
            "ALTER TABLE approval_role_routing ADD COLUMN staff_enabled INTEGER DEFAULT 1",
            "CREATE INDEX IF NOT EXISTS idx_external_inventory_items_item_id ON external_inventory_items(item_id)",
            "CREATE INDEX IF NOT EXISTS idx_external_inventory_items_serial_number ON external_inventory_items(serial_number)",
            "CREATE INDEX IF NOT EXISTS idx_external_inventory_items_mac_id ON external_inventory_items(mac_id)",
            "CREATE INDEX IF NOT EXISTS idx_external_inventory_items_device_type ON external_inventory_items(device_type)",
            "CREATE TABLE IF NOT EXISTS approval_role_routing (id INTEGER PRIMARY KEY AUTOINCREMENT, approval_type TEXT UNIQUE NOT NULL, admin_enabled INTEGER DEFAULT 1, manager_enabled INTEGER DEFAULT 1, staff_enabled INTEGER DEFAULT 1, updated_by TEXT, updated_at TEXT NOT NULL)",
        ]:
            try:
                await db.execute(stmt)
            except Exception:
                pass  # Column already exists
        for stmt in [
            "UPDATE external_inventory_items SET item_id = inventory_id WHERE item_id IS NULL OR item_id = ''",
            "UPDATE external_inventory_items SET serial_number = '' WHERE serial_number IS NULL",
            "UPDATE external_inventory_items SET mac_id = '' WHERE mac_id IS NULL",
            "UPDATE external_inventory_items SET device_type = COALESCE(category, 'device') WHERE device_type IS NULL OR device_type = ''",
            "UPDATE external_inventory_items SET price = COALESCE(price, unit_cost, 0)",
            "UPDATE external_inventory_items SET sku = COALESCE(NULLIF(item_id, ''), sku)",
            "UPDATE external_inventory_items SET category = COALESCE(NULLIF(device_type, ''), category)",
            "UPDATE external_inventory_items SET unit_cost = COALESCE(price, unit_cost, 0)",
        ]:
            await db.execute(stmt)

        await db.execute(
            """INSERT OR IGNORE INTO approval_role_routing
             (approval_type, admin_enabled, manager_enabled, staff_enabled, updated_by, updated_at)
             VALUES ('distribution', 1, 1, 1, 'system', datetime('now'))"""
        )
        await db.execute(
            """INSERT OR IGNORE INTO approval_role_routing
             (approval_type, admin_enabled, manager_enabled, staff_enabled, updated_by, updated_at)
             VALUES ('return', 1, 1, 1, 'system', datetime('now'))"""
        )
        await db.execute(
            """INSERT OR IGNORE INTO approval_role_routing
             (approval_type, admin_enabled, manager_enabled, staff_enabled, updated_by, updated_at)
             VALUES ('defect', 1, 1, 1, 'system', datetime('now'))"""
        )
        await db.execute("UPDATE approval_role_routing SET staff_enabled = COALESCE(staff_enabled, 1)")
        # Data migration: fix existing devices that still have old NOC values
        await db.execute(
            "UPDATE devices SET current_location = 'PDIC' WHERE current_location = 'NOC' OR current_location IS NULL"
        )
        await db.execute(
            "UPDATE devices SET current_holder_name = 'PDIC (Distribution)' WHERE current_holder_type = 'noc' AND (current_holder_name IS NULL OR current_holder_name = 'NOC')"
        )
        # Backfill registered_by_name from device_history where possible
        await db.execute(
            """UPDATE devices SET registered_by_name = (
                SELECT performed_by_name FROM device_history
                WHERE device_history.device_id = CAST(devices.id AS TEXT)
                  AND device_history.action = 'registered'
                ORDER BY device_history.timestamp ASC LIMIT 1
            ) WHERE registered_by_name IS NULL"""
        )
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
    band_type TEXT,
    nuid TEXT,
    status TEXT DEFAULT 'available',
    current_location TEXT,
    current_holder_id TEXT,
    current_holder_name TEXT,
    registered_by_name TEXT,
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
    manifest_file TEXT,
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
    replacement_requested_at TEXT,
    replacement_confirmed_at TEXT,
    replacement_confirmed_by TEXT,
    replacement_confirmed_by_name TEXT,
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
    device_id TEXT,
    requested_status TEXT,
    reason TEXT,
    status TEXT DEFAULT 'pending',
    reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_by_name TEXT,
    review_note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS external_inventory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inventory_id TEXT UNIQUE NOT NULL,
    item_id TEXT NOT NULL,
    name TEXT NOT NULL,
    serial_number TEXT,
    mac_id TEXT,
    device_type TEXT NOT NULL,
    price REAL DEFAULT 0,
    sku TEXT,
    category TEXT,
    unit TEXT DEFAULT 'pcs',
    quantity_on_hand INTEGER DEFAULT 0,
    reorder_level INTEGER DEFAULT 0,
    unit_cost REAL DEFAULT 0,
    supplier_name TEXT,
    location TEXT,
    status TEXT DEFAULT 'active',
    notes TEXT,
    image_url TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory_purchase_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id TEXT UNIQUE NOT NULL,
    supplier_name TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    expected_date TEXT,
    ordered_by TEXT NOT NULL,
    ordered_by_name TEXT,
    total_amount REAL DEFAULT 0,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory_po_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id TEXT NOT NULL,
    item_inventory_id TEXT NOT NULL,
    item_sku TEXT,
    item_name TEXT,
    quantity_ordered INTEGER NOT NULL,
    unit_cost REAL DEFAULT 0,
    line_total REAL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory_receipts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id TEXT UNIQUE NOT NULL,
    po_id TEXT NOT NULL,
    supplier_name TEXT,
    received_by TEXT NOT NULL,
    received_by_name TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory_receipt_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id TEXT NOT NULL,
    item_inventory_id TEXT NOT NULL,
    item_sku TEXT,
    item_name TEXT,
    quantity_received INTEGER NOT NULL,
    unit_cost REAL DEFAULT 0,
    line_total REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS inventory_stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movement_id TEXT UNIQUE NOT NULL,
    item_inventory_id TEXT NOT NULL,
    item_sku TEXT,
    item_name TEXT,
    movement_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    reference_type TEXT,
    reference_id TEXT,
    notes TEXT,
    performed_by TEXT,
    performed_by_name TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approval_role_routing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    approval_type TEXT UNIQUE NOT NULL,
    admin_enabled INTEGER DEFAULT 1,
    manager_enabled INTEGER DEFAULT 1,
    staff_enabled INTEGER DEFAULT 1,
    updated_by TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_external_inventory_items_status ON external_inventory_items(status);
CREATE INDEX IF NOT EXISTS idx_external_inventory_items_sku ON external_inventory_items(sku);
CREATE INDEX IF NOT EXISTS idx_inventory_purchase_orders_status ON inventory_purchase_orders(status);
CREATE INDEX IF NOT EXISTS idx_inventory_po_lines_po_id ON inventory_po_lines(po_id);
CREATE INDEX IF NOT EXISTS idx_inventory_receipts_po_id ON inventory_receipts(po_id);
CREATE INDEX IF NOT EXISTS idx_inventory_receipt_lines_receipt_id ON inventory_receipt_lines(receipt_id);
CREATE INDEX IF NOT EXISTS idx_inventory_stock_movements_item_id ON inventory_stock_movements(item_inventory_id);
CREATE INDEX IF NOT EXISTS idx_inventory_stock_movements_created_at ON inventory_stock_movements(created_at);
CREATE INDEX IF NOT EXISTS idx_approval_role_routing_type ON approval_role_routing(approval_type);
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
