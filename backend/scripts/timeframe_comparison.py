import pandas as pd
import numpy as np
import warnings
import json
import itertools
warnings.filterwarnings("ignore")

try:
    from tvDatafeed import TvDatafeed, Interval
except ImportError:
    print("Please install tvdatafeed")
    exit(1)

def simulate_logic(df, params, lot, multiplier, mode):
    rsi_period = params['rsi_p']
    ema_period = params['ema_p']
    sl_atr = params['sl_atr']
    tp_atr = params['tp_atr']
    rsi_upper = params['rsi_u']
    rsi_lower = params['rsi_l']

    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['atr'] = np.max(ranges, axis=1).rolling(14).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    df['ema'] = df['close'].ewm(span=ema_period, adjust=False).mean()
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    df['macd'] = macd
    df['macd_signal'] = macd_signal

    df = df.dropna().copy()
    
    capital = 1000.0
    initial = 1000.0
    wins = 0
    trades = 0
    peak = capital
    max_dd = 0.0

    df_records = df.to_dict('records')
    for row in df_records:
        price = row['close']
        atr = row['atr']
        r = row['rsi']
        e = row['ema']
        m = row['macd']
        ms = row['macd_signal']
        pm = row.get('prev_macd', m)
        pms = row.get('prev_macd_signal', ms)
        
        position = None
        if mode == "adaptive":
            if r < rsi_lower and price > e: position = "BUY"
            elif r > rsi_upper and price < e: position = "SELL"
                
        if position:
            sl_dist = atr * sl_atr
            tp_dist = atr * tp_atr
            if position == "BUY":
                is_win = (row['high'] >= price + tp_dist)
                is_loss = (row['low'] <= price - sl_dist)
            else:
                is_win = (row['low'] <= price - tp_dist)
                is_loss = (row['high'] >= price + sl_dist)
                
            if is_win and not is_loss:
                capital += (tp_dist * multiplier) * lot
                wins += 1; trades += 1
            elif is_loss and not is_win:
                capital += -(sl_dist * multiplier) * lot
                trades += 1
            
            if capital > peak: peak = capital
            dd = ((peak - capital) / peak) * 100
            if dd > max_dd: max_dd = dd

    winrate = (wins / trades * 100) if trades > 0 else 0
    roi = ((capital - initial) / initial) * 100
    score = (winrate * 0.4) + (roi * 0.4) - (max_dd * 0.2)
    return {"score": score, "winrate": winrate, "roi": roi, "dd": max_dd, "trades": trades}

def run_test():
    tv = TvDatafeed()
    # Let's test EURUSD and XAUUSD
    pairs = [("EURUSD", "OANDA", 100000.0), ("XAUUSD", "OANDA", 100.0)]
    timeframes = [("M5", Interval.in_5_minute, 5000), ("M15", Interval.in_15_minute, 1666)]
    
    # We will test the "adaptive" logic with a fixed baseline parameter to compare RAW timeframe quality
    params = {'rsi_p': 7, 'ema_p': 50, 'sl_atr': 2.0, 'tp_atr': 1.0, 'rsi_u': 70, 'rsi_l': 30}
    
    results = []
    
    for pair, exch, mult in pairs:
        for tf_name, interval, n_bars in timeframes:
            df = tv.get_hist(symbol=pair, exchange=exch, interval=interval, n_bars=n_bars)
            if df is not None and not df.empty:
                df['prev_macd'] = df['macd'].shift(1) if 'macd' in df else 0
                df['prev_macd_signal'] = df['macd_signal'].shift(1) if 'macd_signal' in df else 0
                res = simulate_logic(df, params, 0.1, mult, "adaptive")
                results.append({
                    "Pair": pair,
                    "Timeframe": tf_name,
                    "Trades": res["trades"],
                    "WinRate": f"{res['winrate']:.1f}%",
                    "ROI": f"{res['roi']:.1f}%",
                    "Max_DD": f"{res['dd']:.1f}%"
                })
                print(f"{pair} {tf_name}: Trades={res['trades']} WR={res['winrate']:.1f}% DD={res['dd']:.1f}% ROI={res['roi']:.1f}%")
                
    with open("data/tf_compare.json", "w") as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    run_test()
