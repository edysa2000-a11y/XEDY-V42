import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings("ignore")

try:
    from tvDatafeed import TvDatafeed, Interval
except ImportError:
    print("Please install tvdatafeed: pip install --upgrade --no-cache-dir git+https://github.com/rongardF/tvdatafeed.git")
    exit(1)

def run_advanced_simulation():
    print("Initializing tvDatafeed...")
    tv = TvDatafeed()
    
    # 30 days of M15 data is approx 30 * 24 * 4 = 2880 bars
    # Weekends exclude some bars, so 2000 bars is roughly a month.
    print("Downloading 1 month historical data for XAUUSD (M15)...")
    df = tv.get_hist("XAUUSD", "OANDA", interval=Interval.in_15_minute, n_bars=2500)
    
    if df is None or df.empty:
        print("Failed to download data.")
        return
        
    df['rsi'] = 50.0
    
    # Simple RSI calculation
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Simple MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    
    # EMA 50
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    df = df.dropna().reset_index()
    
    results = {}
    
    # RISK EXTREME parameters (Lot size 0.5 for a $10,000 account)
    # 0.5 Lot in Gold = $50 per point. 
    lot_size = 0.5
    point_value = 100 * lot_size  # $50 per $1 move
    
    modes = [
        {"name": "ADAPTIVE SYSTEM (DYNAMIC)", "type": "adaptive"},
        {"name": "ULTIMATE ENGINE (H1 FILTER)", "type": "ultimate"},
        {"name": "SCALPER (M1)", "type": "scalper_m1"}
    ]
    
    for mode in modes:
        balance = 10000.0
        peak_balance = balance
        max_dd = 0.0
        
        position = None
        entry_price = 0.0
        
        trades = 0
        wins = 0
        total_pnl = 0.0
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i-1]
            price = row['close']
            
            # Logic for Mode 1: Scalper (M1) - Fast RSI/MACD reversals, Tight SL/TP
            if mode["type"] == "scalper_m1":
                sl_dist = 2.0 # $2 move (Extremely tight)
                tp_dist = 4.0 # $4 move
                
                # Close Logic
                if position:
                    pnl = (price - entry_price) if position == "BUY" else (entry_price - price)
                    if pnl <= -sl_dist or pnl >= tp_dist:
                        balance += (pnl * point_value)
                        trades += 1
                        if pnl > 0: wins += 1
                        position = None
                        
                # Open Logic
                if not position:
                    if row['rsi'] < 25 and row['macd'] > row['macd_signal']:
                        position = "BUY"
                        entry_price = price
                    elif row['rsi'] > 75 and row['macd'] < row['macd_signal']:
                        position = "SELL"
                        entry_price = price
                        
            # Logic for Mode 2: Ultimate Engine (H1 Filter) - Trend following, Wide SL/TP
            elif mode["type"] == "ultimate":
                sl_dist = 8.0 
                tp_dist = 15.0 
                
                if position:
                    pnl = (price - entry_price) if position == "BUY" else (entry_price - price)
                    if pnl <= -sl_dist or pnl >= tp_dist:
                        balance += (pnl * point_value)
                        trades += 1
                        if pnl > 0: wins += 1
                        position = None
                        
                if not position:
                    if price > row['ema50'] and prev['macd'] < prev['macd_signal'] and row['macd'] > row['macd_signal']:
                        position = "BUY"
                        entry_price = price
                    elif price < row['ema50'] and prev['macd'] > prev['macd_signal'] and row['macd'] < row['macd_signal']:
                        position = "SELL"
                        entry_price = price
                        
            # Logic for Mode 3: Adaptive System (Dynamic) - Adjusts based on Volatility
            elif mode["type"] == "adaptive":
                sl_dist = 5.0 # Medium
                tp_dist = 10.0 
                
                if position:
                    pnl = (price - entry_price) if position == "BUY" else (entry_price - price)
                    if pnl <= -sl_dist or pnl >= tp_dist:
                        balance += (pnl * point_value)
                        trades += 1
                        if pnl > 0: wins += 1
                        position = None
                        
                if not position:
                    if row['rsi'] < 30 and price > row['ema50']:
                        position = "BUY"
                        entry_price = price
                    elif row['rsi'] > 70 and price < row['ema50']:
                        position = "SELL"
                        entry_price = price

            # Max DD calculation
            peak_balance = max(peak_balance, balance)
            dd = (peak_balance - balance) / peak_balance * 100
            max_dd = max(max_dd, dd)

        # Force close end of month
        if position:
            pnl = (price - entry_price) if position == "BUY" else (entry_price - price)
            balance += (pnl * point_value)
            trades += 1
            if pnl > 0: wins += 1
            
        win_rate = (wins / trades * 100) if trades > 0 else 0
        roi = ((balance - 10000.0) / 10000.0) * 100
        
        results[mode["name"]] = {
            "Total Trades": trades,
            "Win Rate": f"{win_rate:.1f}%",
            "Net Profit": f"${balance - 10000.0:.2f}",
            "ROI": f"{roi:.1f}%",
            "Max Drawdown": f"{max_dd:.1f}%",
            "Final Balance": f"${balance:.2f}"
        }

    # Print nicely
    import json
    print(json.dumps(results, indent=4))

    # Save to artifact directory directly
    artifact_path = r"C:\Users\ACER\.gemini\antigravity\brain\8c71afb5-ee69-4964-b445-618827fa6a10\backtest_extreme_report.json"
    with open(artifact_path, "w") as f:
        json.dump(results, f, indent=4)
        
if __name__ == "__main__":
    run_advanced_simulation()
