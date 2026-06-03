from fastapi import APIRouter, HTTPException, Depends
from models.schemas import IdentifyRequest, IdentifyResponse
from core.database import get_pool
from core.redis_client import cache_customer_allowed_products

router = APIRouter(prefix="/customer", tags=["Customer"])

@router.post("/identify", response_model=IdentifyResponse)
async def identify_customer(req: IdentifyRequest):
    pool = get_pool()
    query = req.business_name.strip()
    
    async with pool.acquire() as conn:
        # 1. Exact/ILIKE Match
        row = await conn.fetchrow("""
            SELECT customer_id, business_name, phone_number, allowed_products, is_active
            FROM customers
            WHERE business_name ILIKE $1
            LIMIT 1
        """, f"%{query}%")
        
        if not row:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        if not row["is_active"]:
            raise HTTPException(status_code=400, detail="Customer is inactive")
        
        c_id = row["customer_id"]
        allowed_products = row["allowed_products"] or []
        count = len(allowed_products)
        
        # 2. Cache allowed_products in Redis for fast resolution later
        await cache_customer_allowed_products(c_id, allowed_products)
        
        return IdentifyResponse(
            customer_id=c_id,
            business_name=row["business_name"],
            phone=row["phone_number"],
            allowed_products_count=count,
            status="identified",
            confidence=0.95
        )
