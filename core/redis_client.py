import json
import redis.asyncio as aioredis
from core.config import REDIS_HOST, REDIS_PORT, CUSTOMER_CACHE_TTL, SESSION_CACHE_TTL

redis: aioredis.Redis | None = None


async def create_redis():
    global redis
    redis = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


async def close_redis():
    global redis
    if redis:
        await redis.close()
        redis = None


def get_redis() -> aioredis.Redis:
    if redis is None:
        raise RuntimeError("Redis not initialized")
    return redis

# ── Customer Cache ───────────────────────────────────────────────

def _customer_key(business_name: str) -> str:
    return f"customer:{business_name.strip().lower().replace(' ', '_')}"


async def get_customer_cache(business_name: str) -> dict | None:
    data = await get_redis().get(_customer_key(business_name))
    return json.loads(data) if data else None


async def set_customer_cache(business_name: str, data: dict):
    await get_redis().set(
        _customer_key(business_name),
        json.dumps(data),
        ex=CUSTOMER_CACHE_TTL,
    )


# ── Session Cache ────────────────────────────────────────────────

def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


async def get_session(session_id: str) -> dict | None:
    data = await get_redis().get(_session_key(session_id))
    return json.loads(data) if data else None


async def set_session(session_id: str, data: dict):
    await get_redis().set(
        _session_key(session_id),
        json.dumps(data),
        ex=SESSION_CACHE_TTL,
    )


async def delete_session(session_id: str):
    await get_redis().delete(_session_key(session_id))

# ── Allowed Products Cache ───────────────────────────────────────────────

async def cache_customer_allowed_products(customer_id: int, product_ids: list):
    key = f"customer:{customer_id}:products"
    await get_redis().delete(key)
    if product_ids:
        # sadd needs strings or ints, we compress slightly
        await get_redis().sadd(key, *product_ids)
        await get_redis().expire(key, 3600)

async def get_customer_allowed_products(customer_id: int) -> set:
    key = f"customer:{customer_id}:products"
    members = await get_redis().smembers(key)
    return {int(m) for m in members}

# ── Cart Cache ───────────────────────────────────────────────

async def update_cart(customer_id: int, product_id: int, quantity: float, name: str, unit: str):
    key = f"cart:customer:{customer_id}"
    current = await get_redis().hget(key, str(product_id))
    if current:
        data = json.loads(current)
        data["qty"] += quantity
    else:
        data = {"product_id": product_id, "qty": quantity, "name": name, "unit": unit}
    
    await get_redis().hset(key, str(product_id), json.dumps(data))
    await get_redis().expire(key, 86400) # 1 day

async def remove_cart_item(customer_id: int, product_id: int):
    key = f"cart:customer:{customer_id}"
    await get_redis().hdel(key, str(product_id))

async def get_cart(customer_id: int) -> list:
    key = f"cart:customer:{customer_id}"
    items = await get_redis().hgetall(key)
    return [json.loads(val) for val in items.values()]

async def clear_cart(customer_id: int):
    key = f"cart:customer:{customer_id}"
    await get_redis().delete(key)