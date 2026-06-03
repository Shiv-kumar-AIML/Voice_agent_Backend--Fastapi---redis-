import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import create_pool, get_pool, close_pool

async def recreate_db():
    print("Connecting to DB...")
    await create_pool()
    pool = get_pool()
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            print("Dropping old tables...")
            await conn.execute("DROP TABLE IF EXISTS customer_allowed_products CASCADE;")
            await conn.execute("DROP TABLE IF EXISTS products CASCADE;")
            await conn.execute("DROP TABLE IF EXISTS customers CASCADE;")
            
            print("Creating customers table...")
            await conn.execute("""
                CREATE TABLE customers (
                    id SERIAL PRIMARY KEY,
                    customer_id INTEGER UNIQUE NOT NULL,
                    business_name VARCHAR(255) NOT NULL,
                    email VARCHAR(255),
                    phone_number VARCHAR(20),
                    allowed_products INTEGER[],
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX idx_customer_phone ON customers (phone_number);
            """)

            print("Creating products table...")
            await conn.execute("""
                CREATE TABLE products (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER UNIQUE NOT NULL,
                    product_code VARCHAR(100),
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    image TEXT,
                    cat_id VARCHAR(50),
                    base_unit_id INTEGER,
                    order_unit_id INTEGER,
                    category VARCHAR(100),
                    base_unit VARCHAR(20),
                    order_unit VARCHAR(20),
                    min_order_qty NUMERIC(10,2),
                    max_order_qty NUMERIC(10,2),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX idx_product_name ON products (name);
            """)

            print("Schema recreated successfully!")

    await close_pool()

if __name__ == "__main__":
    asyncio.run(recreate_db())
