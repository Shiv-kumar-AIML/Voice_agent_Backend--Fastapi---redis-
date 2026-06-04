from fastapi import APIRouter, HTTPException, Query
from models.schemas import (
    ResolveRequest, ResolveResponse, ResolveOption,
    ProductRecommendResponse, ProductRecommendItem, ProductDetailsResponse
)
from services.resolver_service import resolve_product
from core.database import get_db
from typing import Optional

router = APIRouter(prefix="/products", tags=["Products"])

@router.post("/resolve", response_model=ResolveResponse)
async def product_resolve(req: ResolveRequest):
    result = await resolve_product(req.customer_id, req.query)

    status = result.get("status")

    if status == "matched":
        return ResolveResponse(
            status="matched",
            product_id=result.get("product_id"),
            product_name=result.get("product_name"),
            quantity=result.get("quantity"),
            unit=result.get("unit"),
            normalized_quantity=result.get("normalized_quantity"),
            normalized_unit=result.get("normalized_unit"),
            confidence=result.get("confidence", 0.95),
            valid=result.get("valid", True),
            message=result.get("message", None),
        )
    elif status == "clarification_required":
        options = [ResolveOption(**o) for o in result.get("options", [])]
        return ResolveResponse(
            status="clarification_required",
            product_family=result.get("product_family"),
            options=options,
        )
    else:
        return ResolveResponse(
            status="not_found",
            alternatives=result.get("alternatives", []),
        )

@router.get("/recommend", response_model=ProductRecommendResponse)
async def recommend_products(query: Optional[str] = Query(None, description="Category or search term")):
    db = get_db()
    if not query or query.strip() == "":
        cursor = await db.execute("""
            SELECT DISTINCT category 
            FROM products 
            WHERE is_active = 1 AND category IS NOT NULL
            LIMIT 10
        """)
        rows = await cursor.fetchall()
        return ProductRecommendResponse(
            type="categories",
            categories=[r["category"] for r in rows if r["category"]]
        )
    else:
        q = f"%{query}%"
        cursor = await db.execute("""
            SELECT product_id, name, description, category, order_unit 
            FROM products 
            WHERE is_active = 1 
            AND (category LIKE ? OR name LIKE ? OR description LIKE ?)
            LIMIT 5
        """, (q, q, q))
        rows = await cursor.fetchall()

        items = []
        for r in rows:
            items.append(ProductRecommendItem(
                product_id=r["product_id"],
                name=r["name"],
                description=r["description"],
                category=r["category"],
                order_unit=r["order_unit"]
            ))
        return ProductRecommendResponse(type="products", items=items)

@router.get("/{product_id}", response_model=ProductDetailsResponse)
async def get_product_details(product_id: int):
    db = get_db()
    cursor = await db.execute("""
        SELECT product_id, name, description, category, order_unit, min_order_qty 
        FROM products 
        WHERE product_id = ? AND is_active = 1
    """, (product_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    return ProductDetailsResponse(
        product_id=row["product_id"],
        name=row["name"],
        description=row["description"],
        category=row["category"],
        order_unit=row["order_unit"],
        min_order_qty=float(row["min_order_qty"]) if row["min_order_qty"] is not None else None
    )
