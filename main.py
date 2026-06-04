from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from core.database import init_db, close_db
from core.redis_client import create_redis, close_redis
from core.config import VAPI_API_KEY, ASSISTANT_ID

from api.customer import router as customer_router
from api.products import router as products_router
from api.cart import router as cart_router
from api.order import router as order_router


# ── Frontend paths ───────────────────────────────────────────────
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────
    await init_db()
    await create_redis()
    print("✅ SQLite database and Redis connected")
    yield
    # ── Shutdown ─────────────────────────────────────────────────
    await close_db()
    await close_redis()
    print("🛑 SQLite database and Redis closed")


app = FastAPI(
    title="Voice Agent Backend",
    description="FastAPI backend for Vapi B2B voice ordering agent",
    version="3.0.0",
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

# ── API Routes ───────────────────────────────────────────────────
app.include_router(customer_router)
app.include_router(products_router)
app.include_router(cart_router)
app.include_router(order_router)


# ── Health Check ─────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}


# ── Serve Frontend UI ────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def serve_ui():
    """Serve the Ordertron Voice Agent HTML frontend."""
    html_path = os.path.join(_FRONTEND_DIR, "index.html")
    if not os.path.exists(html_path):
        return HTMLResponse("<h1>Frontend not found. Ensure frontend/index.html exists.</h1>", status_code=404)

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("__VAPI_PUBLIC_KEY__", VAPI_API_KEY or "")
    html = html.replace("__VAPI_ASSISTANT_ID__", ASSISTANT_ID or "")
    return HTMLResponse(html)


app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")