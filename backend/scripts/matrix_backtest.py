import pandas as pd
import numpy as np
import warnings
import json
warnings.filterwarnings("ignore")

try:
    from tvDatafeed import TvDatafeed, Interval
except ImportError:
    print("Please install tvdatafeed")

def run_matrix_simulation(months: int, capital: float, pairs: list) -> dict:
    tv = TvDatafeed()
    
    # Approx 2400 bars (M15) per month
    bars_needed = months * 2400
    
    risks = {
        "CONSERVATIVE (Base Lot: 0.16)": 0.16,
        "NORMAL (Base Lot: 0.33)": 0.33,
        "MODERATE (Base Lot: 0.50)": 0.50,
        "EXTREME (Base Lot: 0.66)": 0.66
    }
    
    modes = {
        "Scalper (M1)": {"type": "scalper", "hg_key": "intra-candle-scalper"},
        "Adaptive System": {"type": "adaptive", "hg_key": "forecast-hlc-bound"},
        "Ultimate Engine": {"type": "ultimate", "hg_key": "decision-priority-engine"}
    }

    # Structure of the final payload:
    # { "CONSERVATIVE (Base Lot: 0.16)": { "Scalper (M1)": { "Net": "$...", "WR": "...", ... } }, ... }
    final_results = {}
    for r_name in risks.keys():
        final_results[r_name] = {}
        for m_name in modes.keys():
            final_results[r_name][m_name] = {
                "Net_Value": 0.0,
                "Trades": 0,
                "Wins": 0,
                "Max_DD_Value": 0.0
            }
            
    for pair in pairs:
        exchange = "OANDA" if pair != "USOIL" else "TVC" # Standardize
        df = tv.get_hist(pair, exchange, interval=Interval.in_15_minute, n_bars=bars_needed)
        
        if df is None or df.empty:
            continue
            
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # Fetch Holy Grail Params for this specific pair
        try:
            from backend.engines.risk_engine import load_holy_grail_params
            all_hg_params = load_holy_grail_params()
            hg_params = all_hg_params.get(pair, all_hg_params.get("XAUUSD", {}))
        except:
            hg_params = {}

        # Override modes with Holy Grail parameters for this pair
        modes_for_pair = {}
        for m_name, m_info in modes.items():
            hg_conf = hg_params.get(m_info["hg_key"], {})
            modes_for_pair[m_name] = {
                "type": m_info["type"],
                "rsi_p": hg_conf.get("rsi_p", 14),
                "ema_p": hg_conf.get("ema_p", 50),
                "sl": hg_conf.get("sl_atr", 2.0),
                "tp": hg_conf.get("tp_atr", 1.0),
                "rsi_u": hg_conf.get("rsi_u", 70),
                "rsi_l": hg_conf.get("rsi_l", 30)
            }
            
        # Calculate modes indicators dynamically based on Holy Grail config
        delta = df['close'].diff()
        for m_info in modes_for_pair.values():
            r_p = m_info["rsi_p"]
            e_p = m_info["ema_p"]
            
            if f'rsi_{r_p}' not in df.columns:
                gain = (delta.where(delta > 0, 0)).rolling(window=r_p).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=r_p).mean()
                rs = gain / loss
                df[f'rsi_{r_p}'] = 100 - (100 / (1 + rs))
                
            if f'ema_{e_p}' not in df.columns:
                df[f'ema_{e_p}'] = df['close'].ewm(span=e_p, adjust=False).mean()
        
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        df['macd'] = macd
        df['macd_signal'] = macd_signal
        
        df.bfill(inplace=True)
        
        multiplier = 100.0 if "XAU" in pair else 100000.0
        if pair == "USDJPY": multiplier = 1000.0
        if pair == "USOIL": multiplier = 10.0
        
        for r_name, lot in risks.items():
            for m_name, m_params in modes_for_pair.items():
                balance = capital
                peak = balance
                max_dd = 0.0
                trades = 0
                wins = 0
                
                position = None
                entry = 0.0
                sl_dist = 0.0
                tp_dist = 0.0
                
                for i in range(1, len(df)):
                    row = df.iloc[i]
                    prev = df.iloc[i-1]
                    price = row['close']
                    atr = row['atr']
                    
                    if position:
                        pnl = (price - entry) if position == "BUY" else (entry - price)
                        if pnl <= -sl_dist or pnl >= tp_dist:
                            balance += (pnl * lot * multiplier)
                            trades += 1
                            if pnl > 0: wins += 1
                            position = None
                            
                    if not position:
                        m_type = m_params["type"]
                        rsi = row[f'rsi_{m_params["rsi_p"]}']
                        ema = row[f'ema_{m_params["ema_p"]}']
                        ru = m_params["rsi_u"]
                        rl = m_params["rsi_l"]
                        sl_atr = m_params["sl"]
                        tp_atr = m_params["tp"]
                        
                        if m_type == "scalper":
                            if rsi < rl and row['macd'] > row['macd_signal']:
                                position = "BUY"; entry = price; sl_dist = atr * sl_atr; tp_dist = atr * tp_atr
                            elif rsi > ru and row['macd'] < row['macd_signal']:
                                position = "SELL"; entry = price; sl_dist = atr * sl_atr; tp_dist = atr * tp_atr
                        
                        elif m_type == "adaptive":
                            if rsi < rl and price > ema:
                                position = "BUY"; entry = price; sl_dist = atr * sl_atr; tp_dist = atr * tp_atr
                            elif rsi > ru and price < ema:
                                position = "SELL"; entry = price; sl_dist = atr * sl_atr; tp_dist = atr * tp_atr
                                
                        elif m_type == "ultimate":
                            if price > ema and prev['macd'] < prev['macd_signal'] and row['macd'] > row['macd_signal']:
                                position = "BUY"; entry = price; sl_dist = atr * sl_atr; tp_dist = atr * tp_atr
                            elif price < ema and prev['macd'] > prev['macd_signal'] and row['macd'] < row['macd_signal']:
                                position = "SELL"; entry = price; sl_dist = atr * sl_atr; tp_dist = atr * tp_atr
                                
                    peak = max(peak, balance)
                    dd = (peak - balance) / peak * 100
                    max_dd = max(max_dd, dd)

                if position:
                    pnl = (price - entry) if position == "BUY" else (entry - price)
                    balance += (pnl * lot * multiplier)
                    trades += 1
                    if pnl > 0: wins += 1
                    
                net = balance - capital
                
                # Aggregate results across multiple pairs
                final_results[r_name][m_name]["Net_Value"] += net
                final_results[r_name][m_name]["Trades"] += trades
                final_results[r_name][m_name]["Wins"] += wins
                # Max DD across pairs isn't easily additive, we just take the max or average. Let's take the max.
                final_results[r_name][m_name]["Max_DD_Value"] = max(final_results[r_name][m_name]["Max_DD_Value"], max_dd)

    # Format the payload for the frontend
    formatted_payload = {}
    for r_name in risks.keys():
        formatted_payload[r_name] = {}
        for m_name in modes.keys():
            data = final_results[r_name][m_name]
            trades = data["Trades"]
            wins = data["Wins"]
            wr = (wins / trades * 100) if trades > 0 else 0
            
            # Format net value as currency string
            net_val = data["Net_Value"]
            prefix = "" if net_val < 0 else "+"
            
            formatted_payload[r_name][m_name] = {
                "Net": f"{prefix}${net_val:,.0f}",
                "WR": f"{wr:.0f}%",
                "Trades": trades,
                "DD": f"{data['Max_DD_Value']:.1f}%"
            }
            
    return formatted_payload
