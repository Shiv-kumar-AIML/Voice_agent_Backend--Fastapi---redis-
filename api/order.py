from fastapi import APIRouter, HTTPException
from models.schemas import OrderPlaceRequest, OrderPlaceResponse
from core.redis_client import get_cart, clear_cart
from core.database import get_pool
import random

router = APIRouter(prefix="/order", tags=["Order"])

@router.post("/place", response_model=OrderPlaceResponse)
async def place_order(req: OrderPlaceRequest):
    pool = get_pool()
    
    # 1. Get cart from Redis
    cart_items = await get_cart(req.customer_id)
    
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty. Add products before placing an order.")
    
    # 2. Validate customer exists
    async with pool.acquire() as conn:
        customer = await conn.fetchrow(
            "SELECT customer_id, business_name, is_active FROM customers WHERE customer_id = $1",
            req.customer_id
        )
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if not customer["is_active"]:
        raise HTTPException(status_code=400, detail="Customer account is inactive")
    
    # 3. Generate order ID (in production: insert into orders table)
    order_id = random.randint(10000, 99999)
    
    # 4. Clear cart after placing order
    await clear_cart(req.customer_id)
    
    return OrderPlaceResponse(
        order_id=order_id,
        items=len(cart_items),
        status="placed"
    )
