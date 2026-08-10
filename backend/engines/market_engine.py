from .base_engine import BaseEngine
import MetaTrader5 as mt5
import asyncio
import pandas as pd
from datetime import datetime

class MarketEngine(BaseEngine):
    """
    Market Engine: Responsible for connecting to MT5 and ingesting ticks for multiple symbols.
    """
    
    @property
    def engine_name(self) -> str:
        return "MarketEngine"

    def __init__(self, config=None, feature_stores=None, data_engine=None, news_engine=None, symbols=None, v39_engines=None):
        super().__init__(config)
        self.feature_stores = feature_stores or {}
        self.data_engine = data_engine
        self.news_engine = news_engine
        self.symbols = symbols if symbols else ["XAUUSD"]
        self.v39_engines = v39_engines
        self.last_tick_time_msc = {s: 0 for s in self.symbols}
        self._running = False

    async def start(self):
        self.logger.info("Initializing MetaTrader 5...")
        if not mt5.initialize():
            self.logger.error("MT5 initialize() failed, error code: " + str(mt5.last_error()))
        else:
            for symbol in self.symbols:
                self.logger.info(f"Selecting symbol {symbol}...")
                if not mt5.symbol_select(symbol, True):
                    self.logger.error(f"Failed to select symbol {symbol}")
                else:
                    self.logger.info(f"MT5 Connected. Subscribed to {symbol}")
            
        self._running = True
        # Start background polling loop
        asyncio.create_task(self._poll_ticks())

    async def stop(self):
        self.logger.info("Stopping Market Engine...")
        self._running = False
        mt5.shutdown()

    async def _poll_ticks(self):
        """Polls MT5 for the latest tick for all symbols."""
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
                        
                    # Broadcast V39 Causal Engine Data
                    if self.v39_engines and "XAUUSD" in self.v39_engines:
                        v39 = self.v39_engines["XAUUSD"]
                        
                        # Mock triggering for UI broadcast purposes
                        event_res = await v39["v39_event"].process_news("CPI inflation data exceeds expectations")
                        macro_res = await v39["v39_macro"].calculate_yield_dxy(event_res)
                        
                        # Use actual OANDA tick volume if available
                        tick_vol = 500
                        if self.data_engine:
                            df = self.data_engine.get_historical_data("XAUUSD", "M5", 1)
                            if not df.empty and 'tick_volume' in df.columns:
                                tick_vol = int(df['tick_volume'].iloc[-1])
                                
                        flow_res = await v39["v39_flow"].aggregate_flow_channels(0.005, tick_vol)
                        
                        div_res = await v39["v39_div"].check_divergence(1.5, flow_res, macro_res)
                        gate_res = await v39["v39_consensus"].final_trade_gate(event_res, macro_res, flow_res, div_res, 81.0)
                        
                        v39_payload = {
                            "event": event_res,
                            "macro": macro_res,
                            "flow": flow_res,
                            "div": div_res,
                            "gate": gate_res
                        }
                        await ws_manager.broadcast_v39_causal(v39_payload)
                        
                loop_counter += 1

                if is_mt5_ok:
                    for symbol in self.symbols:
                        tick = mt5.symbol_info_tick(symbol)
                        if tick:
                            tick_time_msc = getattr(tick, 'time_msc', tick.time * 1000)
                            if tick_time_msc > self.last_tick_time_msc.get(symbol, 0):
                                self.last_tick_time_msc[symbol] = tick_time_msc
                                await self.on_tick_received(symbol, tick.bid, tick.ask, tick.time)
            except Exception as e:
                self.logger.error(f"Error dalam _poll_ticks: {e}", exc_info=True)
            await asyncio.sleep(0.1)  # 100ms poll interval

    async def on_tick_received(self, symbol: str, bid: float, ask: float, time_sec: int):
        try:
            from backend.api.websocket import ws_manager
            # Broadcast to frontend
            await ws_manager.broadcast_tick(symbol, bid, ask, time_sec)
            
            # Process AI pipeline
            fs = self.feature_stores.get(symbol)
            if fs:
                await fs.process_tick(symbol, bid, ask, time_sec)
        except Exception as e:
            self.logger.error(f"Error dalam on_tick_received: {e}", exc_info=True)
