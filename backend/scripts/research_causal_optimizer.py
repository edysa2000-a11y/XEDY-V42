import MetaTrader5 as mt5
import datetime
import pandas as pd
import numpy as np
import itertools

def get_data():
    mt5.initialize()
    start_dt = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2026, 7, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
    rates_m15 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M15, start_dt, end_dt)
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
    df['lower_bb_20'] = rolling_mean - (rolling_std * 2.0)
    df['upper_bb_20'] = rolling_mean + (rolling_std * 2.0)
    df['lower_bb_22'] = rolling_mean - (rolling_std * 2.2)
    df['upper_bb_22'] = rolling_mean + (rolling_std * 2.2)
    
    # ATR
    high, low, close = df['high'], df['low'], df['close']
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)
    df['atr'] = tr.rolling(14).mean().fillna(3.0)
    
    # MACRO PROXY
    start_d1 = start_dt - datetime.timedelta(days=200)
    rates_d1 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_D1, start_d1, end_dt)
    df_d1 = pd.DataFrame(rates_d1)
    df_d1['time'] = pd.to_datetime(df_d1['time'], unit='s')
    df_d1['macro_bias'] = df_d1['close'].ewm(span=50, adjust=False).mean()
    df = pd.merge_asof(df, df_d1[['time', 'macro_bias']], on='time', direction='backward')
    
    return df.dropna()

def run_simulation(df, sl_atr, trail_step_atr, bb_std, trail_activation):
    balance = 10000.0
    positions = []
    closed_pnl = []
    monthly_results = {}
    current_month = None
    
    for i in range(50, len(df)):
        row = df.iloc[i]
        dt = row['time']
        month_key = dt.strftime('%Y-%m')
        
        if current_month != month_key:
            if current_month is not None:
                monthly_results[current_month] = closed_pnl.copy()
            closed_pnl = []
            current_month = month_key
            balance = 10000.0 # non-compounding for clean comparison
            positions = []
            
        price = row['close']
        atr = row['atr']
        macro_bias = "UP" if price > row['macro_bias'] else "DOWN"
        
        upper_bb = row['upper_bb_22'] if bb_std == 2.2 else row['upper_bb_20']
        lower_bb = row['lower_bb_22'] if bb_std == 2.2 else row['lower_bb_20']
        
        pos_to_close = []
        for p in positions:
            if p['type'] == 'BUY':
                # Activation check
                if price - p['price'] >= (atr * trail_activation):
                    p['activated'] = True
                if p['activated'] and price - p['price'] > (atr * trail_step_atr):
                    new_sl = price - (atr * sl_atr)
                    if new_sl > p['sl']:
                        p['sl'] = new_sl
                if price <= p['sl']:
                    pos_to_close.append(p)
            elif p['type'] == 'SELL':
                if p['price'] - price >= (atr * trail_activation):
                    p['activated'] = True
                if p['activated'] and p['price'] - price > (atr * trail_step_atr):
                    new_sl = price + (atr * sl_atr)
                    if new_sl < p['sl']:
                        p['sl'] = new_sl
                if price >= p['sl']:
                    pos_to_close.append(p)
                    
        for p in pos_to_close:
            pnl = (p['sl'] - p['price']) * p['volume'] if p['type'] == 'BUY' else (p['price'] - p['sl']) * p['volume']
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
        
        if can_buy and row['low'] <= lower_bb and row['rsi'] < 30:
            positions.append({'type': 'BUY', 'price': price, 'volume': lot_volume, 'sl': price - (atr * sl_atr), 'activated': trail_activation == 0})
        elif can_sell and row['high'] >= upper_bb and row['rsi'] > 70:
            positions.append({'type': 'SELL', 'price': price, 'volume': lot_volume, 'sl': price + (atr * sl_atr), 'activated': trail_activation == 0})
            
    if current_month is not None:
        monthly_results[current_month] = closed_pnl.copy()
    return monthly_results

def evaluate():
    df = get_data()
    if df is None: return
    
    sl_atrs = [2.0, 2.5, 3.0]
    trail_steps = [0.25, 0.5, 1.0]
    bb_stds = [2.0, 2.2]
    activations = [0, 1.0, 2.0]
    
    best_prof = -99999
    best_params = None
    best_res = None
    
    print("--- BRUTE FORCE 7-MONTH OPTIMIZATION ---")
    for sl, ts, bb, act in itertools.product(sl_atrs, trail_steps, bb_stds, activations):
        res = run_simulation(df, sl, ts, bb, act)
        total_prof = sum(sum(pnl) for pnl in res.values())
        all_green = all(sum(pnl) > 0 for pnl in res.values())
        
        if total_prof > best_prof and all_green:
            best_prof = total_prof
            best_params = (sl, ts, bb, act)
            best_res = res
            print(f"New Best: SL={sl}, TS={ts}, BB={bb}, Act={act} -> ${total_prof:,.2f}")
            
    if best_res is None:
        print("Tidak menemukan kombinasi all-green yang lebih baik.")
        return
        
    print("\n--- HASIL OPTIMASI TERTINGGI (ALL GREEN) ---")
    print(f"Parameters: Trailing SL = {best_params[0]} ATR, Trailing Step = {best_params[1]} ATR, BB = {best_params[2]}, Activation = {best_params[3]} ATR")
    print("="*55)
    print(f"{'Bulan':<10} | {'Profit Net':<15} | {'Winrate':<10} | {'Total OP'}")
    print("-"*55)
    
    total_wins, total_trades = 0, 0
    for m, pnl in best_res.items():
        p = sum(pnl)
        wins = len([x for x in pnl if x > 0])
        trades = len(pnl)
        wr = (wins/trades*100) if trades>0 else 0
        total_wins += wins
        total_trades += trades
        print(f"{m:<10} | ${p:>13,.2f} | {wr:>8.1f}% | {trades}")
        
    print("-"*55)
    avg_wr = (total_wins/total_trades*100) if total_trades>0 else 0
    print(f"TOTAL      | ${best_prof:>13,.2f} | {avg_wr:>8.1f}% | {total_trades}")

if __name__ == '__main__':
    evaluate()
