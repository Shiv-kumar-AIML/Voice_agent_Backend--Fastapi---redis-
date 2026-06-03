from fastapi import APIRouter, HTTPException, Query
from models.schemas import (
    ResolveRequest, ResolveResponse, ResolveOption,
    ProductRecommendResponse, ProductRecommendItem, ProductDetailsResponse
)
from services.resolver_service import resolve_product
from core.database import get_pool
from typing import Optional

router = APIRouter(prefix="/products", tags=["Products"])

@router.post("/resolve", response_model=ResolveResponse)
async def product_resolve(req: ResolveRequest):
    result = await resolve_product(req.customer_id, req.query)
    
    # Map result to schema
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
async def recommend_products(query: Optional[str] = Query(None, description="Category or search term for recommendation")):
    pool = get_pool()
    async with pool.acquire() as conn:
        if not query or query.strip() == "":
            rows = await conn.fetch('''
                SELECT DISTINCT category 
                FROM products 
                WHERE is_active = true AND category IS NOT NULL
                LIMIT 10
            ''')
            return ProductRecommendResponse(
                type="categories",
                categories=[r["category"] for r in rows if r["category"]]
            )
        else:
            q = f"%{query}%"
            rows = await conn.fetch('''
                SELECT product_id, name, description, category, order_unit 
                FROM products 
                WHERE is_active = true 
                AND (category ILIKE $1 OR name ILIKE $1 OR description ILIKE $1)
                LIMIT 5
            ''')
            
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
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT product_id, name, description, category, order_unit, min_order_qty 
            FROM products 
            WHERE product_id = $1 AND is_active = true
        ''', product_id)
        if not row:
            raise HTTPException(status_code=404, detail="Product not found")
            
        return ProductDetailsResponse(
            product_id=row["product_id"],
            name=row["name"],
            description=row["description"],
            category=row["category"],
            order_unit=row["order_unit"],
            # Convert decimal to float if necessary, though Decimal is supported by Pydantic mostly.
            min_order_qty=float(row["min_order_qty"]) if row["min_order_qty"] is not None else None
        )
