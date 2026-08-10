import pandas as pd
import numpy as np
import warnings
import json
warnings.filterwarnings("ignore")

try:
    from tvDatafeed import TvDatafeed, Interval
except ImportError:
    print("Please install tvdatafeed")
    exit(1)

def run_confidence_comparison():
    print("Downloading 1 month historical data for XAUUSD (M15)...")
    tv = TvDatafeed()
    df = tv.get_hist("XAUUSD", "OANDA", interval=Interval.in_15_minute, n_bars=2500)
    
    if df is None or df.empty:
        print("Failed to download data.")
        return
        
    # Holy Grail parameters for XAUUSD Adaptive
    rsi_period = 7
    ema_period = 50
    sl_atr = 1.0
    tp_atr = 2.0
    rsi_upper = 75
    rsi_lower = 25
    
    # Calculate indicators
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['atr'] = true_range.rolling(14).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    df['ema'] = df['close'].ewm(span=ema_period, adjust=False).mean()
    
    df.bfill(inplace=True)
    
    # Calculate simulated AI Confidence based on Confluence
    # Base 50%, add up to 25% for MACD momentum, up to 25% for Trend extension
    macd_conf = np.abs(df['macd_hist']) / df['atr'] * 1.5 
    trend_conf = np.abs(df['close'] - df['ema']) / df['atr'] * 0.5
    raw_conf = 0.50 + macd_conf + trend_conf
    df['confidence'] = np.clip(raw_conf, 0.50, 0.99)
    
    results = {}
    lot_size = 0.5
    point_value = 10 * lot_size # WTI/OANDA XAU multiplier is 10. Wait, XAUUSD in tvDatafeed Oanda is actual price (e.g. 2350.50).
    # 1 lot = 100 ounces. 0.5 lot = 50 ounces. $1 move = $50.
    multiplier = 100.0
    
    scenarios = [
        {"name": "No Filter (Semua Trade)", "min_conf": 0.0},
        {"name": "Confidence 71% - 100%", "min_conf": 0.71},
        {"name": "Confidence 81% - 100%", "min_conf": 0.81}
    ]
    
    for scen in scenarios:
        balance = 10000.0
        peak = balance
        max_dd = 0.0
        trades = 0
        wins = 0
        
        position = None
        entry_price = 0.0
        sl_dist = 0.0
        tp_dist = 0.0
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            price = row['close']
            
            if position:
                pnl = (price - entry_price) if position == "BUY" else (entry_price - price)
                if pnl <= -sl_dist or pnl >= tp_dist:
                    balance += (pnl * lot_size * multiplier)
                    trades += 1
                    if pnl > 0: wins += 1
                    position = None
                    
            if not position:
                # ADAPTIVE SYSTEM LOGIC
                if row['rsi'] < rsi_lower and price > row['ema']:
                    if row['confidence'] >= scen["min_conf"]:
                        position = "BUY"
                        entry_price = price
                        sl_dist = row['atr'] * sl_atr
                        tp_dist = row['atr'] * tp_atr
                elif row['rsi'] > rsi_upper and price < row['ema']:
                    if row['confidence'] >= scen["min_conf"]:
                        position = "SELL"
                        entry_price = price
                        sl_dist = row['atr'] * sl_atr
                        tp_dist = row['atr'] * tp_atr
                        
            peak = max(peak, balance)
            dd = (peak - balance) / peak * 100
            max_dd = max(max_dd, dd)

        if position:
            pnl = (price - entry_price) if position == "BUY" else (entry_price - price)
            balance += (pnl * lot_size * multiplier)
            trades += 1
            if pnl > 0: wins += 1
            
        win_rate = (wins / trades * 100) if trades > 0 else 0
        roi = ((balance - 10000.0) / 10000.0) * 100
        
        results[scen["name"]] = {
            "Total Trades": trades,
            "Win Rate": f"{win_rate:.1f}%",
            "Net Profit": f"${balance - 10000.0:.2f}",
            "ROI": f"{roi:.1f}%",
            "Max Drawdown": f"{max_dd:.1f}%"
        }

    artifact_path = r"C:\Users\ACER\.gemini\antigravity\brain\8c71afb5-ee69-4964-b445-618827fa6a10\confidence_comparison.json"
    with open(artifact_path, "w") as f:
        json.dump(results, f, indent=4)
    print("Done")

if __name__ == "__main__":
    run_confidence_comparison()
