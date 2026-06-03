from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import create_pool, close_pool
from core.redis_client import create_redis, close_redis

from api.customer import router as customer_router
from api.products import router as products_router
from api.cart import router as cart_router
from api.order import router as order_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────
    await create_pool()
    await create_redis()
    print("✅ Database pool and Redis connected")
    yield
    # ── Shutdown ─────────────────────────────────────────────────
    await close_pool()
    await close_redis()
    print("🛑 Database pool and Redis closed")


app = FastAPI(
    title="Voice Agent Backend",
    description="FastAPI backend for Vapi B2B voice ordering agent",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────
app.include_router(customer_router)
app.include_router(products_router)
app.include_router(cart_router)
app.include_router(order_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}