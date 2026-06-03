from pydantic import BaseModel
from typing import List, Optional

class IdentifyRequest(BaseModel):
    business_name: str

class IdentifyResponse(BaseModel):
    customer_id: int
    business_name: str
    phone: Optional[str] = None
    allowed_products_count: int
    status: str
    confidence: float

class ResolveRequest(BaseModel):
    customer_id: int
    query: str

class ResolveOption(BaseModel):
    product_id: int
    name: str
    unit: str

class ResolveResponse(BaseModel):
    status: str # "matched", "clarification_required", "not_found"
    # For Matched
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    normalized_quantity: Optional[float] = None
    normalized_unit: Optional[str] = None
    confidence: Optional[float] = None
    
    # For Unit Validations
    valid: bool = True
    message: Optional[str] = None
    
    # For Clarification
    product_family: Optional[str] = None
    options: Optional[List[ResolveOption]] = None
    # For Not found
    alternatives: Optional[List[str]] = None

class CartAddRequest(BaseModel):
    customer_id: int
    product_id: int
    quantity: float
    unit: str

class CartRemoveRequest(BaseModel):
    customer_id: int
    product_id: int

class CartItem(BaseModel):
    product_id: int
    name: str
    qty: float
    unit: str

class CartSummaryResponse(BaseModel):
    items: List[CartItem]

class OrderPlaceRequest(BaseModel):
    customer_id: int

class OrderPlaceResponse(BaseModel):
    order_id: int
    items: int
    status: str

class ProductRecommendItem(BaseModel):
    product_id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    order_unit: Optional[str] = None

class ProductRecommendResponse(BaseModel):
    type: str # "categories" or "products"
    categories: Optional[List[str]] = None
    items: Optional[List[ProductRecommendItem]] = None

class ProductDetailsResponse(BaseModel):
    product_id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    order_unit: Optional[str] = None
    min_order_qty: Optional[float] = None
