from fastapi import APIRouter, HTTPException
from models.schemas import CartAddRequest, CartRemoveRequest, CartSummaryResponse, CartItem
from core.redis_client import update_cart, remove_cart_item, get_cart
from core.database import get_db

router = APIRouter(prefix="/cart", tags=["Cart"])

@router.post("/add")
async def add_to_cart(req: CartAddRequest):
    db = get_db()
    cursor = await db.execute(
        "SELECT name, min_order_qty, order_unit FROM products WHERE product_id = ?",
        (req.product_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Product with ID {req.product_id} not found.")

    name = row["name"]
    min_qty = row["min_order_qty"]
    order_unit = row["order_unit"]

    try:
        min_qty = float(min_qty) if min_qty is not None else 1.0
    except (ValueError, TypeError):
        min_qty = 1.0

    if min_qty > 0:
        remainder = round((req.quantity % min_qty), 4)
        if remainder != 0 and remainder != min_qty:
            raise HTTPException(
                status_code=422,
                detail=f"This product must be ordered in multiples of {min_qty} {order_unit}. You cannot order {req.quantity}."
            )

    await update_cart(req.customer_id, req.product_id, req.quantity, name, req.unit)

    cart_items = await get_cart(req.customer_id)
    return {
        "cart_items": len(cart_items),
        "message": "Added"
    }

@router.post("/remove")
async def remove_from_cart(req: CartRemoveRequest):
    await remove_cart_item(req.customer_id, req.product_id)
    return {"message": "Removed"}

@router.get("/summary", response_model=CartSummaryResponse)
async def cart_summary(customer_id: int):
    items = await get_cart(customer_id)
    return {"items": items}
