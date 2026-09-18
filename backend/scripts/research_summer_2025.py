import MetaTrader5 as mt5
import datetime
import pandas as pd
import numpy as np
import itertools

def get_data():
    mt5.initialize()
    # Grab data for the whole year 2025 to test robustness, but we will focus scoring on May-Aug
    start_dt = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2025, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
    rates_m15 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M15, start_dt - datetime.timedelta(days=20), end_dt)
    df = pd.DataFrame(rates_m15)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # BB 2.0
    rolling_mean = df['close'].rolling(20).mean()
    rolling_std = df['close'].rolling(20).std()
    df['upper_bb_20'] = rolling_mean + (rolling_std * 2.0)
    df['lower_bb_20'] = rolling_mean - (rolling_std * 2.0)
    
    # ATR
    high, low, close = df['high'], df['low'], df['close']
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)
    df['atr'] = tr.rolling(14).mean().fillna(3.0)
    
    # MACRO PROXY
    rates_d1 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_D1, start_dt - datetime.timedelta(days=200), end_dt)
    df_d1 = pd.DataFrame(rates_d1)
    df_d1['time'] = pd.to_datetime(df_d1['time'], unit='s')
    df_d1['macro_bias'] = df_d1['close'].ewm(span=50, adjust=False).mean()
    df = pd.merge_asof(df, df_d1[['time', 'macro_bias']], on='time', direction='backward')
    
    df = df[df['time'] >= pd.to_datetime('2025-01-01')].reset_index(drop=True)
    return df.dropna()

def run_simulation(df, sl_atr, trail_step_atr, activation_atr):
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
            balance = 10000.0 
            positions = []
            
        price = row['close']
        atr = row['atr']
        macro_bias = "UP" if price > row['macro_bias'] else "DOWN"
        
        pos_to_close = []
        for p in positions:
            if p['type'] == 'BUY':
                # Activation check for Break Even / Trailing
                if not p['activated'] and price - p['price'] >= (atr * activation_atr):
                    p['activated'] = True
                    p['sl'] = p['price'] + (atr * 0.2) # Move to BE + small profit
                    
                if p['activated'] and price - p['price'] > (atr * trail_step_atr):
                    new_sl = price - (atr * sl_atr)
                    if new_sl > p['sl']:
                        p['sl'] = new_sl
                if price <= p['sl']:
                    pos_to_close.append(p)
            elif p['type'] == 'SELL':
                if not p['activated'] and p['price'] - price >= (atr * activation_atr):
                    p['activated'] = True
                    p['sl'] = p['price'] - (atr * 0.2)
                    
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
        
        if can_buy and row['low'] <= row['lower_bb_20'] and row['rsi'] < 30:
            positions.append({'type': 'BUY', 'price': price, 'volume': lot_volume, 'sl': price - (atr * sl_atr), 'activated': activation_atr == 0})
        elif can_sell and row['high'] >= row['upper_bb_20'] and row['rsi'] > 70:
            positions.append({'type': 'SELL', 'price': price, 'volume': lot_volume, 'sl': price + (atr * sl_atr), 'activated': activation_atr == 0})
            
    if current_month is not None:
        monthly_results[current_month] = closed_pnl.copy()
    return monthly_results

def evaluate():
    df = get_data()
    if df is None: return
    
    sl_atrs = [1.5, 2.0, 2.5]
    trail_steps = [0.5]
    activations = [0, 1.0, 1.5, 2.0]
    
    best_summer_prof = -999999
    best_total_prof = -999999
    best_params = None
    best_res = None
    
    print("--- OPTIMASI BULAN MINUS (MAY-AUG 2025) ---")
    for sl, ts, act in itertools.product(sl_atrs, trail_steps, activations):
        res = run_simulation(df, sl, ts, act)
        
        # Focus on May, June, July, August
        summer_months = ['2025-05', '2025-06', '2025-07', '2025-08']
        summer_prof = sum(sum(res.get(m, [0])) for m in summer_months)
        total_prof = sum(sum(pnl) for pnl in res.values())
        
        # We want to maximize summer profit without breaking the total profit
        if summer_prof > best_summer_prof and total_prof > 200000:
            best_summer_prof = summer_prof
            best_total_prof = total_prof
            best_params = (sl, ts, act)
            best_res = res
            print(f"New Best Summer: SL={sl}, Act={act} -> Summer: ${summer_prof:,.2f} | Total: ${total_prof:,.2f}")
            
    print("\n--- HASIL OPTIMASI FINAL ---")
    print(f"Parameters: Trailing SL = {best_params[0]} ATR, Activation = {best_params[2]} ATR")
    print("="*55)
    print(f"{'Bulan':<10} | {'Profit Net':<15} | {'Winrate':<10} | {'Total OP'}")
    print("-"*55)
    
    for m, pnl in best_res.items():
        p = sum(pnl)
        wins = len([x for x in pnl if x > 0])
        trades = len(pnl)
        wr = (wins/trades*100) if trades>0 else 0
        print(f"{m:<10} | ${p:>13,.2f} | {wr:>8.1f}% | {trades}")
        
if __name__ == '__main__':
    evaluate()
