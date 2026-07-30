from .connection import get_db_connection
import logging

logger = logging.getLogger("xedy.database.schema")

async def init_db():
    """
    Initializes the SQLite database schema according to the Architecture Specification.
    """
    conn = await get_db_connection()
    try:
        await conn.executescript('''
            CREATE TABLE IF NOT EXISTS system_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                module TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS trade (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket TEXT UNIQUE,
                symbol TEXT NOT NULL,
                volume REAL NOT NULL,
                open_price REAL NOT NULL,
                close_price REAL,
                sl REAL,
                tp REAL,
                profit REAL,
                open_time DATETIME NOT NULL,
                close_time DATETIME,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS feature (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                rsi REAL,
                macd REAL,
                dxy_corr REAL,
                confidence REAL
            );
            
            -- Indexes for fast querying
            CREATE INDEX IF NOT EXISTS idx_trade_status ON trade(status);
            CREATE INDEX IF NOT EXISTS idx_feature_timestamp ON feature(timestamp);
            CREATE INDEX IF NOT EXISTS idx_log_module ON system_log(module);
        ''')
        await conn.commit()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        await conn.rollback()
        raise
    finally:
        await conn.close()
