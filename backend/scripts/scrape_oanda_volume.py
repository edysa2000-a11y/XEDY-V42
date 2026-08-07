import os
import json
import logging
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import numpy as np
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_and_calculate_cvd():
    try:
        logger.info("Initializing TvDatafeed as guest...")
        tv = TvDatafeed()
        
        symbol = 'XAUUSD'
        exchange = 'OANDA'
        
        logger.info(f"Fetching {symbol} data from {exchange} (Interval M5, 60 bars)...")
        data = tv.get_hist(symbol=symbol, exchange=exchange, interval=Interval.in_5_minute, n_bars=60)
        
        if data is None or data.empty:
            logger.error("Failed to fetch data from TradingView.")
            return False
            
        # Calculate Delta: if Close >= Open, volume is positive, else negative
        data['delta'] = np.where(data['close'] >= data['open'], data['volume'], -data['volume'])
        
        # Calculate CVD for the last 20 candles
        recent_20 = data.tail(20)
        cvd = float(recent_20['delta'].sum())
        
        current_price = float(data['close'].iloc[-1])
        ema_50 = float(data['close'].ewm(span=50, adjust=False).mean().iloc[-1])
        
        trend = "BULLISH"
        if cvd > 0 and current_price < ema_50:
            trend = "BULLISH_ABSORPTION"
        elif cvd < 0 and current_price > ema_50:
            trend = "BEARISH_EXHAUSTION"
        elif cvd < 0:
            trend = "BEARISH"
            
        output = {
            "source": "TradingView (OANDA)",
            "symbol": symbol,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "timeframe": "M5",
            "cvd_20": cvd,
            "volume_trend": trend,
            "current_price": current_price,
            "ema_50": ema_50
        }
        
        os.makedirs("data", exist_ok=True)
        with open("data/oanda_cvd.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
            
        logger.info(f"Successfully saved OANDA CVD: {cvd} ({trend})")
        return True
        
    except Exception as e:
        logger.error(f"Error in fetch_and_calculate_cvd: {e}")
        return False

if __name__ == "__main__":
    fetch_and_calculate_cvd()
