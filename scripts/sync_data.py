import asyncio
import json
import urllib.request
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import init_db, get_db, close_db
from core.config import CUSTOMER_API, PRODUCT_API


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (AI Agent)'})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def parse_float(val) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except ValueError:
        return None


async def sync_products(db, products_data: list):
    for p in products_data:
        await db.execute("""
            INSERT OR REPLACE INTO products 
            (product_id, product_code, name, description, image, cat_id, 
             base_unit_id, order_unit_id, category, base_unit, order_unit,
             min_order_qty, max_order_qty, is_active, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
        """, (
            p.get("id"),
            p.get("product_code"),
            p.get("name"),
            p.get("desc"),
            p.get("image"),
            p.get("cat_id"),
            int(p.get("base_unit_id")) if p.get("base_unit_id") else None,
            int(p.get("order_unit_id")) if p.get("order_unit_id") else None,
            p.get("category"),
            p.get("base_unit"),
            p.get("order_unit"),
            parse_float(p.get("min_order_qut")),
            parse_float(p.get("max_order_qut")),
        ))
    await db.commit()
    print(f"Synced {len(products_data)} products.")


async def sync_customers(db, customers_data: list):
    for c in customers_data:
        allowed = json.dumps(c.get("allow_products", []))
        await db.execute("""
            INSERT OR REPLACE INTO customers
            (customer_id, business_name, email, allowed_products, is_active, updated_at)
            VALUES (?, ?, ?, ?, 1, datetime('now'))
        """, (
            c.get("customer_id"),
            c.get("business_name"),
            c.get("email"),
            allowed,
        ))
    await db.commit()
    print(f"Synced {len(customers_data)} customers.")


async def main():
    if not CUSTOMER_API or not PRODUCT_API:
        print("API URLs not found in config.")
        return

    print(f"Fetching products from {PRODUCT_API}...")
    products_response = fetch_json(PRODUCT_API)
    products_data = products_response.get("data", {}).get("products", [])

    print(f"Fetching customers from {CUSTOMER_API}...")
    customers_response = fetch_json(CUSTOMER_API)
    customers_data = customers_response.get("data", {}).get("customers", [])

    print("Connecting to SQLite database...")
    await init_db()
    db = get_db()

    try:
        await sync_products(db, products_data)
        await sync_customers(db, customers_data)
        print("Data synchronization complete.")
    except Exception as e:
        print(f"Error during synchronization: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(main())
