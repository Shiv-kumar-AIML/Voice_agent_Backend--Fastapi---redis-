import aiosqlite
from core.config import DATABASE_PATH

db: aiosqlite.Connection | None = None


async def init_db():
    """Open SQLite connection and enable WAL mode + row_factory."""
    global db
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")


async def close_db():
    global db
    if db:
        await db.close()
        db = None


def get_db() -> aiosqlite.Connection:
    if db is None:
        raise RuntimeError("Database not initialized")
    return db
