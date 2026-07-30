from .base_engine import BaseEngine
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD

class FeatureStore(BaseEngine):
    """
    Feature Store: Computes real-time technical indicators from tick data.
    """
    @property
    def engine_name(self) -> str:
        return "FeatureStore"

    def __init__(self, config=None, ml_engine=None):
        super().__init__(config)
        self.ml_engine = ml_engine
        self.history = pd.DataFrame(columns=["time", "bid", "ask", "price"])
        self.max_history = 1000

    async def start(self):
        self.logger.info("Feature Store initialized.")

    async def stop(self):
        pass

    async def process_tick(self, symbol: str, bid: float, ask: float, time_sec: int):
        price = (bid + ask) / 2.0
        
        # Add to history
        new_row = {"time": time_sec, "bid": bid, "ask": ask, "price": price}
        self.history = pd.concat([self.history, pd.DataFrame([new_row])], ignore_index=True)
        
        if len(self.history) % 10 == 0:
            self.logger.info(f"FeatureStore tick received. History size: {len(self.history)}")
        
        if len(self.history) > self.max_history:
            self.history = self.history.iloc[-self.max_history:]
            
        # Compute Indicators if we have enough data
        if len(self.history) > 30:
            rsi = RSIIndicator(close=self.history['price'], window=14).rsi().iloc[-1]
            macd = MACD(close=self.history['price']).macd().iloc[-1]
            
            # Handle NaN values gracefully (e.g., in flat market conditions)
            import numpy as np
            if pd.isna(rsi) or np.isnan(rsi):
                rsi = 50.0
            if pd.isna(macd) or np.isnan(macd):
                macd = 0.0
                
            # self.logger.debug(f"Computed RSI: {rsi:.2f} MACD: {macd:.4f}")
            
            # Pass to ML Engine
            if self.ml_engine:
                await self.ml_engine.process_features(rsi, macd, price)
