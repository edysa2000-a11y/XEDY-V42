from .base_engine import BaseEngine
import MetaTrader5 as mt5
import asyncio
import pandas as pd
from datetime import datetime

class MarketEngine(BaseEngine):
    """
    Market Engine: Responsible for connecting to MT5 and ingesting ticks.
    """
    
    @property
    def engine_name(self) -> str:
        return "MarketEngine"

    def __init__(self, config=None, feature_store=None, data_engine=None, news_engine=None):
        super().__init__(config)
        self.feature_store = feature_store
        self.data_engine = data_engine
        self.news_engine = news_engine
        self.symbol = self.config.get("symbol", "XAUUSD")
        self._running = False

    async def start(self):
        self.logger.info("Initializing MetaTrader 5...")
        if not mt5.initialize():
            self.logger.error("MT5 initialize() failed, error code: " + str(mt5.last_error()))
        else:
            self.logger.info("Selecting symbol XAUUSD...")
            if not mt5.symbol_select(self.symbol, True):
                self.logger.error(f"Failed to select symbol {self.symbol}")
            else:
                self.logger.info(f"MT5 Connected. Subscribed to {self.symbol}")
            
        self._running = True
        # Start background polling loop
        asyncio.create_task(self._poll_ticks())

    async def stop(self):
        self.logger.info("Stopping Market Engine...")
        self._running = False
        mt5.shutdown()

    async def _poll_ticks(self):
        """Polls MT5 for the latest tick (since MT5 python API lacks async push)."""
        from backend.api.websocket import ws_manager
        
        loop_counter = 0
        while self._running:
            try:
                # Determine MT5 statuses
                is_mt5_ok = mt5.terminal_info() is not None
                
                # Broadcast status occasionally (every ~2 seconds)
                if loop_counter % 20 == 0:
                    await ws_manager.broadcast_status(
                        broker_status="CONNECTED" if is_mt5_ok else "DISCONNECTED",
                        mt5_status="CONNECTED" if is_mt5_ok else "DISCONNECTED",
                        ai_status="ACTIVE"
                    )
                    
                    # Fetch detailed dashboard data if engines exist
                    if self.data_engine and self.news_engine:
                        dashboard_payload = {
                            "type": "dashboard_data",
                            "data_engine": self.data_engine.get_dashboard_data(),
                            "news_engine": self.news_engine.get_dashboard_data()
                        }
                        await ws_manager._broadcast_json(dashboard_payload)
                        
                loop_counter += 1

                if is_mt5_ok:
                    tick = mt5.symbol_info_tick(self.symbol)
                    if tick:
                        tick_time_msc = getattr(tick, 'time_msc', tick.time * 1000)
                        if tick_time_msc > getattr(self, 'last_tick_time_msc', 0):
                            self.last_tick_time_msc = tick_time_msc
                            await self.on_tick_received(self.symbol, tick.bid, tick.ask, tick.time)
            except Exception as e:
                self.logger.error(f"Error dalam _poll_ticks: {e}", exc_info=True)
            await asyncio.sleep(0.1)  # 100ms poll interval

    async def on_tick_received(self, symbol: str, bid: float, ask: float, time_sec: int):
        try:
            from backend.api.websocket import ws_manager
            # Broadcast to frontend
            await ws_manager.broadcast_tick(symbol, bid, ask, time_sec)
            
            # Process AI pipeline
            if self.feature_store:
                await self.feature_store.process_tick(symbol, bid, ask, time_sec)
        except Exception as e:
            self.logger.error(f"Error dalam on_tick_received: {e}", exc_info=True)
