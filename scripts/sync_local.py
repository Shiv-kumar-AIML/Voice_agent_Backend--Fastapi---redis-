import asyncio
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import create_pool, get_pool, close_pool
from scripts.sync_data import sync_products, sync_customers

async def main():
    print("Reading product.json...")
    with open('product.json', 'r') as f:
        products_response = json.load(f)
    products_data = products_response.get("data", {}).get("products", [])

    print("Reading customer.json...")
    with open('customer.json', 'r') as f:
        customers_response = json.load(f)
    customers_data = customers_response.get("data", {}).get("customers", [])

    print("Connecting to database...")
    await create_pool()
    pool = get_pool()
    
    try:
        await sync_products(pool, products_data)
        await sync_customers(pool, customers_data)
        print("Local data synchronization complete.")
    except Exception as e:
        print(f"Error during synchronization: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
