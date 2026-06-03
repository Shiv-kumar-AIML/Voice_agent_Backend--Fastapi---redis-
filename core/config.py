import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment. Add it to your .env file.")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

CUSTOMER_API = os.getenv("CUSTOMER_API")
PRODUCT_API = os.getenv("PRODUCT_API")

# Cache TTLs (seconds)
CUSTOMER_CACHE_TTL = 60 * 60 * 24   # 24 hours
SESSION_CACHE_TTL = 60 * 60          # 1 hour
