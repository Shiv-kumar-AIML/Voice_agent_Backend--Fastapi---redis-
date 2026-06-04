import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import init_db, get_db, close_db

async def recreate_db():
    print("Connecting to SQLite DB...")
    await init_db()
    db = get_db()

    print("Dropping old tables...")
    await db.execute("DROP TABLE IF EXISTS products")
    await db.execute("DROP TABLE IF EXISTS customers")

    print("Creating customers table...")
    await db.execute("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER UNIQUE NOT NULL,
            business_name TEXT NOT NULL,
            email TEXT,
            phone_number TEXT,
            allowed_products TEXT DEFAULT '[]',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    await db.execute("CREATE INDEX IF NOT EXISTS idx_customer_business ON customers (business_name COLLATE NOCASE)")

    print("Creating products table...")
    await db.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER UNIQUE NOT NULL,
            product_code TEXT,
            name TEXT NOT NULL,
            description TEXT,
            image TEXT,
            cat_id TEXT,
            base_unit_id INTEGER,
            order_unit_id INTEGER,
            category TEXT,
            base_unit TEXT,
            order_unit TEXT,
            min_order_qty REAL,
            max_order_qty REAL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    await db.execute("CREATE INDEX IF NOT EXISTS idx_product_name ON products (name COLLATE NOCASE)")

    await db.commit()
    print("Schema recreated successfully!")

    await close_db()

if __name__ == "__main__":
    asyncio.run(recreate_db())
