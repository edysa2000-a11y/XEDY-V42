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
            
        # Also Fetch DXY and US10Y for the Ticker Bar
        def fetch_asset(sym, exc):
            try:
                # Get daily data to calculate 1D change
                df = tv.get_hist(symbol=sym, exchange=exc, interval=Interval.in_daily, n_bars=2)
                if df is not None and len(df) >= 2:
                    current = float(df['close'].iloc[-1])
                    prev = float(df['close'].iloc[-2])
                    change = current - prev
                    change_pct = (change / prev) * 100
                    return current, change, change_pct
            except:
                pass
            return 0.0, 0.0, 0.0
            
        xau_current, xau_change, xau_pct = fetch_asset('XAUUSD', 'OANDA')
        dxy_current, dxy_change, dxy_pct = fetch_asset('DXY', 'TVC') # TVC usually has DXY
        us10y_current, us10y_change, us10y_pct = fetch_asset('US10Y', 'TVC')
        
        # Calculate Real Yield mockup (US10Y - 2.5% expected inflation roughly)
        real_yield_current = us10y_current - 2.5
        real_yield_change = us10y_change
        real_yield_pct = us10y_pct # Mockup percentage
        
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
        
        ticker_output = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "XAUUSD": {"price": xau_current if xau_current > 0 else current_price, "change": xau_change, "change_pct": xau_pct},
            "DXY": {"price": dxy_current, "change": dxy_change, "change_pct": dxy_pct},
            "US10Y": {"price": us10y_current, "change": us10y_change, "change_pct": us10y_pct},
            "REAL_YIELD": {"price": real_yield_current, "change": real_yield_change, "change_pct": real_yield_pct},
            "GLD_NET_FLOW": {"price": 2.85, "change": 1.1, "change_pct": 0, "status": "1D Bullish"}, # Mockup for now
            "COMEX_NET_LONG": {"price": 186742, "change": 7892, "change_pct": 4.41, "status": "Bullish"}, # Mockup for now
            "RISK_SENTIMENT": {"status": "RISK OFF", "desc": "Safe Haven Demand" if dxy_current > 104 else "Risk On"}
        }
        
        os.makedirs("data", exist_ok=True)
        with open("data/oanda_cvd.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
            
        with open("data/market_ticker.json", "w", encoding="utf-8") as f:
            json.dump(ticker_output, f, indent=2)
            
        logger.info(f"Successfully saved OANDA CVD: {cvd} ({trend}) and Market Ticker")
        return True
        
    except Exception as e:
        logger.error(f"Error in fetch_and_calculate_cvd: {e}")
        return False

if __name__ == "__main__":
    fetch_and_calculate_cvd()
