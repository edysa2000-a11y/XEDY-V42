import asyncio
from backend.core.logger import setup_logger
from backend.engines.execution_engine import ExecutionEngine
from backend.engines.risk_engine import RiskEngine
from backend.engines.decision_engine import DecisionEngine
from backend.engines.ml_engine import MLEngine
from backend.engines.feature_store import FeatureStore
from backend.engines.market_engine import MarketEngine
from backend.telegram.bot import TelegramEcosystem
import MetaTrader5 as mt5

async def main():
    logger = setup_logger("xedy.main")
    logger.info("Initializing XEDY Core Pipeline...")
    
    # Initialize Telegram Bot (runs safely in background)
    telegram_bot = TelegramEcosystem()

    # Initialize from bottom to top (Dependency Injection)
    execution_engine = ExecutionEngine()
    risk_engine = RiskEngine(execution_engine=execution_engine)
    decision_engine = DecisionEngine(risk_engine=risk_engine)
    ml_engine = MLEngine(decision_engine=decision_engine)
    feature_store = FeatureStore(ml_engine=ml_engine)
    
    market_engine = MarketEngine(feature_store=feature_store)

    # Start all engines
    await telegram_bot.start()
    await execution_engine.start()
    await risk_engine.start()
    await decision_engine.start()
    await ml_engine.start()
    await feature_store.start()
    await market_engine.start()

    logger.info("All engines running. Waiting for ticks...")
    
    try:
        # Keep main thread alive
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await market_engine.stop()
        await feature_store.stop()
        await ml_engine.stop()
        await decision_engine.stop()
        await risk_engine.stop()
        await execution_engine.stop()
        await telegram_bot.stop()
        mt5.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
