import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/voice_agent.db")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

CUSTOMER_API = os.getenv("CUSTOMER_API")
PRODUCT_API = os.getenv("PRODUCT_API")
VAPI_API_KEY = os.getenv("VAPI_API_KEY", "")
ASSISTANT_ID = os.getenv("ASSISTANT_ID", "")

# Cache TTLs (seconds)
CUSTOMER_CACHE_TTL = 60 * 60 * 24   # 24 hours
SESSION_CACHE_TTL = 60 * 60          # 1 hour
