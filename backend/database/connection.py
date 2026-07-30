import aiosqlite
import os
import logging

logger = logging.getLogger("xedy.database")

DB_PATH = os.environ.get("XEDY_DB_PATH", "xedy_ultimate.db")

async def get_db_connection() -> aiosqlite.Connection:
    """
    Returns an async SQLite connection with WAL mode enabled.
    WAL mode is critical for high-concurrency tick writing without locking.
    """
    try:
        conn = await aiosqlite.connect(DB_PATH)
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA synchronous=NORMAL;")
        await conn.execute("PRAGMA foreign_keys=ON;")
        conn.row_factory = aiosqlite.Row
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise
