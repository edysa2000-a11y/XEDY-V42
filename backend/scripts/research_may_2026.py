import MetaTrader5 as mt5
import datetime
import pandas as pd
import numpy as np
import itertools

def get_data():
    mt5.initialize()
    start_dt = datetime.datetime(2026, 5, 1, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2026, 5, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
    
    # We need older data for rolling windows
    rates_m15 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M15, start_dt - datetime.timedelta(days=10), end_dt)
    df = pd.DataFrame(rates_m15)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # BB variations
    rolling_mean = df['close'].rolling(20).mean()
    rolling_std = df['close'].rolling(20).std()
    df['upper_bb_20'] = rolling_mean + (rolling_std * 2.0)
    df['lower_bb_20'] = rolling_mean - (rolling_std * 2.0)
    df['upper_bb_25'] = rolling_mean + (rolling_std * 2.5)
    df['lower_bb_25'] = rolling_mean - (rolling_std * 2.5)
    
    # ATR
    high, low, close = df['high'], df['low'], df['close']
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)
    df['atr'] = tr.rolling(14).mean().fillna(3.0)
    
    # MACRO PROXY (D1 EMA 50)
    rates_d1 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_D1, start_dt - datetime.timedelta(days=200), end_dt)
    df_d1 = pd.DataFrame(rates_d1)
    df_d1['time'] = pd.to_datetime(df_d1['time'], unit='s')
    df_d1['macro_bias'] = df_d1['close'].ewm(span=50, adjust=False).mean()
    df = pd.merge_asof(df, df_d1[['time', 'macro_bias']], on='time', direction='backward')
    
    # Filter to only May data
    df = df[df['time'] >= pd.to_datetime('2026-05-01')].reset_index(drop=True)
    return df.dropna()

def run_simulation(df, sl_atr, trail_step_atr, bb_std, rsi_ob, rsi_os, use_trail=True, tp_atr=0):
    balance = 10000.0
    positions = []
    closed_pnl = []
    
    for i in range(50, len(df)):
        row = df.iloc[i]
        price = row['close']
        atr = row['atr']
        macro_bias = "UP" if price > row['macro_bias'] else "DOWN"
        
        upper_bb = row['upper_bb_25'] if bb_std == 2.5 else row['upper_bb_20']
        lower_bb = row['lower_bb_25'] if bb_std == 2.5 else row['lower_bb_20']
        
        pos_to_close = []
        for p in positions:
            if use_trail:
                if p['type'] == 'BUY':
                    if price - p['price'] > (atr * trail_step_atr):
                        new_sl = price - (atr * sl_atr)
                        if new_sl > p['sl']:
                            p['sl'] = new_sl
                    if price <= p['sl']:
                        pos_to_close.append(p)
                elif p['type'] == 'SELL':
                    if p['price'] - price > (atr * trail_step_atr):
                        new_sl = price + (atr * sl_atr)
                        if new_sl < p['sl']:
                            p['sl'] = new_sl
                    if price >= p['sl']:
                        pos_to_close.append(p)
            else:
                # Fixed TP/SL logic
                p_float = (price - p['price']) * p['volume'] if p['type'] == 'BUY' else (p['price'] - price) * p['volume']
                if p_float >= (atr * tp_atr * 100 * p['volume'] / 100) or p_float <= -(atr * sl_atr * 100 * p['volume'] / 100):
                    pos_to_close.append(p)
                    
        for p in pos_to_close:
            if use_trail:
                pnl = (p['sl'] - p['price']) * p['volume'] if p['type'] == 'BUY' else (p['price'] - p['sl']) * p['volume']
            else:
                pnl = (price - p['price']) * p['volume'] if p['type'] == 'BUY' else (p['price'] - price) * p['volume']
            closed_pnl.append(pnl)
            balance += pnl
            positions.remove(p)
            
        can_buy = macro_bias == "UP" and len([p for p in positions if p['type'] == 'BUY']) < 3
        can_sell = macro_bias == "DOWN" and len([p for p in positions if p['type'] == 'SELL']) < 3
        if len(positions) > 0 and abs(price - positions[-1]['price']) < atr:
            can_buy = False
            can_sell = False
            
        risk_amount = 200.0
        risk_pips = atr * sl_atr * 10
        lot_volume = max(0.01, round(risk_amount / risk_pips, 2) if risk_pips > 0 else 0.01) * 100
        
        if can_buy and row['low'] <= lower_bb and row['rsi'] < rsi_os:
            positions.append({'type': 'BUY', 'price': price, 'volume': lot_volume, 'sl': price - (atr * sl_atr)})
        elif can_sell and row['high'] >= upper_bb and row['rsi'] > rsi_ob:
            positions.append({'type': 'SELL', 'price': price, 'volume': lot_volume, 'sl': price + (atr * sl_atr)})
            
    return sum(closed_pnl)

def evaluate():
    df = get_data()
    if df is None: return
    
    sl_atrs = [1.5, 2.0, 2.5]
    trail_steps = [0.5, 1.0, 1.5]
    bb_stds = [2.0, 2.5]
    rsi_vals = [(70, 30), (75, 25)]
    
    best_prof = -99999
    best_params = None
    
    print("--- MENCARI HOLY GRAIL BULAN MEI 2026 ---")
    for sl, ts, bb, (rob, ros) in itertools.product(sl_atrs, trail_steps, bb_stds, rsi_vals):
        prof = run_simulation(df, sl, ts, bb, rob, ros, use_trail=True)
        if prof > best_prof:
            best_prof = prof
            best_params = (sl, ts, bb, rob, ros)
            
    print(f"Best Trailing Params: SL={best_params[0]} ATR, Trail_Step={best_params[1]} ATR, BB={best_params[2]}, RSI={best_params[3]}/{best_params[4]}")
    print(f"Profit: ${best_prof:,.2f}")
    
    # Test if fixed TP works better in May (Since May might be a choppy retracement month)
    best_fixed = -99999
    best_fixed_params = None
    tp_atrs = [1.5, 2.0, 3.0]
    for sl, tp, bb, (rob, ros) in itertools.product(sl_atrs, tp_atrs, bb_stds, rsi_vals):
        prof = run_simulation(df, sl, 0, bb, rob, ros, use_trail=False, tp_atr=tp)
        if prof > best_fixed:
            best_fixed = prof
            best_fixed_params = (sl, tp, bb, rob, ros)
            
    print(f"\nBest Fixed TP Params: SL={best_fixed_params[0]} ATR, TP={best_fixed_params[1]} ATR, BB={best_fixed_params[2]}, RSI={best_fixed_params[3]}/{best_fixed_params[4]}")
    print(f"Profit: ${best_fixed:,.2f}")

if __name__ == '__main__':
    evaluate()
