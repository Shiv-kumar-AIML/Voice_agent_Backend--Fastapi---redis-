import json
from fastapi import APIRouter, HTTPException
from models.schemas import IdentifyRequest, IdentifyResponse
from core.database import get_db
from core.redis_client import cache_customer_allowed_products

router = APIRouter(prefix="/customer", tags=["Customer"])

@router.post("/identify", response_model=IdentifyResponse)
async def identify_customer(req: IdentifyRequest):
    db = get_db()
    query = req.business_name.strip()

    cursor = await db.execute("""
        SELECT customer_id, business_name, phone_number, allowed_products, is_active
        FROM customers
        WHERE business_name LIKE ?
        LIMIT 1
    """, (f"%{query}%",))
    row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")

    if not row["is_active"]:
        raise HTTPException(status_code=400, detail="Customer is inactive")

    c_id = row["customer_id"]
    # allowed_products is stored as JSON text in SQLite
    allowed_raw = row["allowed_products"] or "[]"
    allowed_products = json.loads(allowed_raw) if isinstance(allowed_raw, str) else allowed_raw
    count = len(allowed_products)

    # Cache allowed_products in Redis for fast resolution later
    await cache_customer_allowed_products(c_id, allowed_products)

    return IdentifyResponse(
        customer_id=c_id,
        business_name=row["business_name"],
        phone=row["phone_number"],
        allowed_products_count=count,
        status="identified",
        confidence=0.95
    )
