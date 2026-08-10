import pandas as pd
import numpy as np
import warnings
import json
import itertools
from concurrent.futures import ProcessPoolExecutor, as_completed
warnings.filterwarnings("ignore")

try:
    from tvDatafeed import TvDatafeed, Interval
except ImportError:
    print("Please install tvdatafeed")
    exit(1)

def simulate_logic(df, params, lot, multiplier, mode, capital=1000.0):
    rsi_period = params['rsi_p']
    ema_period = params['ema_p']
    sl_atr = params['sl_atr']
    tp_atr = params['tp_atr']
    rsi_upper = params['rsi_u']
    rsi_lower = params['rsi_l']

    # ATR calculation
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['atr'] = true_range.rolling(14).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    
    # EMA
    df['ema'] = df['close'].ewm(span=ema_period, adjust=False).mean()
    
    df.bfill(inplace=True)
    
    # Simulation
    balance = capital
    peak = balance
    max_dd = 0.0
    trades = 0
    wins = 0
    
    position = None
    entry_price = 0.0
    sl_dist = 0.0
    tp_dist = 0.0
    
    point_val = 10 * lot # 1 standard lot = $10 per pip
    
    close_prices = df['close'].values
    atr_vals = df['atr'].values
    rsi_vals = df['rsi'].values
    macd_vals = df['macd'].values
    macdsig_vals = df['macd_signal'].values
    ema_vals = df['ema'].values
    
    for i in range(1, len(close_prices)):
        price = close_prices[i]
        
        # Check close
        if position:
            pnl = (price - entry_price) if position == "BUY" else (entry_price - price)
            if pnl <= -sl_dist or pnl >= tp_dist:
                balance += (pnl * point_val * multiplier)
                trades += 1
                if pnl > 0: wins += 1
                position = None
                
        # Check open
        if not position:
            if mode == "scalper":
                if rsi_vals[i] < rsi_lower and macd_vals[i] > macdsig_vals[i]:
                    position = "BUY"
                    entry_price = price
                    sl_dist = atr_vals[i] * sl_atr
                    tp_dist = atr_vals[i] * tp_atr
                elif rsi_vals[i] > rsi_upper and macd_vals[i] < macdsig_vals[i]:
                    position = "SELL"
                    entry_price = price
                    sl_dist = atr_vals[i] * sl_atr
                    tp_dist = atr_vals[i] * tp_atr
                    
            elif mode == "adaptive":
                if rsi_vals[i] < rsi_lower and price > ema_vals[i]:
                    position = "BUY"
                    entry_price = price
                    sl_dist = atr_vals[i] * sl_atr
                    tp_dist = atr_vals[i] * tp_atr
                elif rsi_vals[i] > rsi_upper and price < ema_vals[i]:
                    position = "SELL"
                    entry_price = price
                    sl_dist = atr_vals[i] * sl_atr
                    tp_dist = atr_vals[i] * tp_atr

        peak = max(peak, balance)
        dd = (peak - balance) / peak * 100
        max_dd = max(max_dd, dd)

    net = balance - capital
    winrate = (wins / trades * 100) if trades > 0 else 0
    # Penalty for too few trades or too high drawdown
    fitness = (net * (winrate/100)) / ((max_dd/100) + 1.0) if (net > 0 and trades > 50 and max_dd < 40) else -1.0

    return {
        "params": params,
        "trades": trades,
        "winrate": winrate,
        "net": net,
        "max_dd": max_dd,
        "fitness": fitness
    }

def main():
    tv = TvDatafeed()
    pair = "XAUUSD"
    print(f"[{pair}] Downloading M15 data for 3 months...")
    df = tv.get_hist(pair, "OANDA", interval=Interval.in_15_minute, n_bars=7000)
    
    if df is None or df.empty:
        print("Failed to download data.")
        return
        
    lot = 0.01  # $1000 capital means we should use very low lot size like 0.01 or 0.05
    multiplier = 10.0
    capital = 1000.0
    mode = "adaptive"

    param_grid = {
        'rsi_p': [9, 14, 21],
        'ema_p': [50, 100, 200],
        'sl_atr': [1.0, 1.5, 2.0],
        'tp_atr': [1.0, 1.5, 2.0, 3.0],
        'rsi_u': [65, 70, 75],
        'rsi_l': [25, 30, 35]
    }
    
    keys = param_grid.keys()
    combinations = list(itertools.product(*param_grid.values()))
    
    best_result = None
    best_fitness = -9999
    
    print(f"Testing {len(combinations)} parameter combinations for XAUUSD (Capital: ${capital}, Lot: {lot})...")
    
    with ProcessPoolExecutor(max_workers=6) as executor:
        futures = []
        for combo in combinations:
            params = dict(zip(keys, combo))
            futures.append(executor.submit(simulate_logic, df.copy(), params, lot, multiplier, mode, capital))
            
        for i, future in enumerate(as_completed(futures)):
            res = future.result()
            if res['fitness'] > best_fitness:
                best_fitness = res['fitness']
                best_result = res
                print(f"New Best! Net: ${res['net']:.2f}, WR: {res['winrate']:.1f}%, DD: {res['max_dd']:.1f}% -> Params: {res['params']}")
                
    print("\n--- OPTIMIZATION COMPLETE ---")
    if best_result:
        print(json.dumps(best_result, indent=4))
        
        # Save to file
        with open("xauusd_1k_optimized.json", "w") as f:
            json.dump(best_result, f, indent=4)
    else:
        print("No profitable combination found within the constraints.")

if __name__ == "__main__":
    main()
