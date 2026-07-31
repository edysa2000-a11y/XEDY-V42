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
            
            # Simple rolling high/low for ADX/ATR
            highs = self.history['price'].rolling(window=15).max()
            lows = self.history['price'].rolling(window=15).min()
            
            import numpy as np
            from ta.trend import ADXIndicator
            try:
                adx = ADXIndicator(high=highs, low=lows, close=self.history['price']).adx().iloc[-1]
            except Exception:
                adx = 20.0
                
            try:
                tr = pd.concat([highs - lows, (highs - self.history['price'].shift(1)).abs(), (lows - self.history['price'].shift(1)).abs()], axis=1).max(axis=1)
                atr = tr.rolling(window=14).mean().iloc[-1]
            except Exception:
                atr = 1.5
            
            # Handle NaN values gracefully
            if pd.isna(rsi) or np.isnan(rsi): rsi = 50.0
            if pd.isna(macd) or np.isnan(macd): macd = 0.0
            if pd.isna(adx) or np.isnan(adx): adx = 20.0
            if pd.isna(atr) or np.isnan(atr): atr = 1.5
            
            # Macro / Correlation Defaults (real-time mapping)
            nfp_surprise = 0.0
            cpi_surprise = 0.0
            fed_rate = 5.25
            dxy_trend = 104.0
            yield_trend = 4.25
            
            # Pass all 9 features to ML Engine
            if self.ml_engine:
                await self.ml_engine.process_features(
                    rsi, macd, adx, atr,
                    nfp_surprise, cpi_surprise, fed_rate,
                    dxy_trend, yield_trend, price
                )
