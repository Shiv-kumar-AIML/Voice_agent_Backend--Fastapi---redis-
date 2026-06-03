import asyncio
import json
import urllib.request
import sys
import os

# Add the parent directory to sys.path so we can import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import create_pool, get_pool, close_pool
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

async def sync_products(pool, products_data: list):
    async with pool.acquire() as conn:
        records = []
        for p in products_data:
            records.append((
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
                True, # is_active
            ))
            
        await conn.executemany('''
            INSERT INTO products (product_id, product_code, name, description, image, cat_id, base_unit_id, order_unit_id, category, base_unit, order_unit, min_order_qty, max_order_qty, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (product_id) DO UPDATE SET
                product_code = EXCLUDED.product_code,
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                image = EXCLUDED.image,
                cat_id = EXCLUDED.cat_id,
                base_unit_id = EXCLUDED.base_unit_id,
                order_unit_id = EXCLUDED.order_unit_id,
                category = EXCLUDED.category,
                base_unit = EXCLUDED.base_unit,
                order_unit = EXCLUDED.order_unit,
                min_order_qty = EXCLUDED.min_order_qty,
                max_order_qty = EXCLUDED.max_order_qty,
                is_active = EXCLUDED.is_active,
                updated_at = CURRENT_TIMESTAMP
        ''', records)
        print(f"Synced {len(records)} products.")

async def sync_customers(pool, customers_data: list):
    async with pool.acquire() as conn:
        async with conn.transaction():
            customer_records = []
            for c in customers_data:
                customer_id = c.get("customer_id")
                customer_records.append((
                    customer_id,
                    c.get("business_name"),
                    c.get("email"),
                    c.get("allow_products", []),
                    True # is_active
                ))
                
            # Upsert customers
            await conn.executemany('''
                INSERT INTO customers (customer_id, business_name, email, allowed_products, is_active)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (customer_id) DO UPDATE SET
                    business_name = EXCLUDED.business_name,
                    email = EXCLUDED.email,
                    allowed_products = EXCLUDED.allowed_products,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
            ''', customer_records)
            print(f"Synced {len(customer_records)} customers.")

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

    print("Connecting to database...")
    await create_pool()
    pool = get_pool()
    
    try:
        await sync_products(pool, products_data)
        await sync_customers(pool, customers_data)
        print("Data synchronization complete.")
    except Exception as e:
        print(f"Error during synchronization: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
