import MetaTrader5 as mt5
import datetime
import pandas as pd
import numpy as np

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
    
    # BB 2.0
    rolling_mean = df['close'].rolling(20).mean()
    rolling_std = df['close'].rolling(20).std()
    df['upper_bb'] = rolling_mean + (rolling_std * 2.0)
    df['lower_bb'] = rolling_mean - (rolling_std * 2.0)
    
    # ATR & ADX
    high, low, close = df['high'], df['low'], df['close']
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)
    atr = tr.rolling(14).mean().fillna(3.0)
    df['atr'] = atr
    
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = abs(minus_dm)
    plus_di = 100 * (plus_dm.ewm(alpha=1/14).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/14).mean() / atr)
    dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
    df['adx'] = dx.ewm(alpha=1/14).mean()
    
    # MACRO PROXY
    start_d1 = start_dt - datetime.timedelta(days=200)
    rates_d1 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_D1, start_d1, end_dt)
    df_d1 = pd.DataFrame(rates_d1)
    df_d1['time'] = pd.to_datetime(df_d1['time'], unit='s')
    df_d1['macro_bias'] = df_d1['close'].ewm(span=50, adjust=False).mean()
    df = pd.merge_asof(df, df_d1[['time', 'macro_bias']], on='time', direction='backward')
    
    return df.dropna()

def run_simulation(df):
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
        adx = row['adx']
        macro_bias = "UP" if price > row['macro_bias'] else "DOWN"
        
        # ADAPTIVE SELF-LEARNING LOGIC based on ADX (Trend Recognition)
        if adx < 25:
            # Sideways / Choppy: Whipsaw is high. Use fixed TP to lock profits early, wide SL to survive whipsaw.
            curr_sl_atr = 2.5
            curr_tp_atr = 1.5
            use_trailing = False
            curr_trail_step = 0.0
        elif adx < 40:
            # Normal Trend: Use Trailing Stop to ride it. Tight SL because we expect immediate follow-through.
            curr_sl_atr = 2.0
            curr_tp_atr = 0.0
            use_trailing = True
            curr_trail_step = 0.5
        else:
            # Aggressive Trend: Wild swings. Wider Trailing SL to survive deep pullbacks.
            curr_sl_atr = 3.0
            curr_tp_atr = 0.0
            use_trailing = True
            curr_trail_step = 1.0
            
        pos_to_close = []
        for p in positions:
            if p['use_trailing']:
                if p['type'] == 'BUY':
                    if price - p['price'] > (atr * p['trail_step']):
                        new_sl = price - (atr * p['sl_atr'])
                        if new_sl > p['sl']:
                            p['sl'] = new_sl
                    if price <= p['sl']:
                        pos_to_close.append(p)
                elif p['type'] == 'SELL':
                    if p['price'] - price > (atr * p['trail_step']):
                        new_sl = price + (atr * p['sl_atr'])
                        if new_sl < p['sl']:
                            p['sl'] = new_sl
                    if price >= p['sl']:
                        pos_to_close.append(p)
            else:
                # Fixed TP
                p_float = (price - p['price']) * p['volume'] if p['type'] == 'BUY' else (p['price'] - price) * p['volume']
                if p_float >= (atr * p['tp_atr'] * 100 * p['volume'] / 100) or p_float <= -(atr * p['sl_atr'] * 100 * p['volume'] / 100):
                    pos_to_close.append(p)
                    
        for p in pos_to_close:
            if p['use_trailing']:
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
        risk_pips = atr * curr_sl_atr * 10
        lot_volume = max(0.01, round(risk_amount / risk_pips, 2) if risk_pips > 0 else 0.01) * 100
        
        if can_buy and row['low'] <= row['lower_bb'] and row['rsi'] < 30:
            positions.append({
                'type': 'BUY', 'price': price, 'volume': lot_volume, 
                'sl': price - (atr * curr_sl_atr), 
                'use_trailing': use_trailing, 'sl_atr': curr_sl_atr, 'tp_atr': curr_tp_atr, 'trail_step': curr_trail_step
            })
        elif can_sell and row['high'] >= row['upper_bb'] and row['rsi'] > 70:
            positions.append({
                'type': 'SELL', 'price': price, 'volume': lot_volume, 
                'sl': price + (atr * curr_sl_atr), 
                'use_trailing': use_trailing, 'sl_atr': curr_sl_atr, 'tp_atr': curr_tp_atr, 'trail_step': curr_trail_step
            })
            
    if current_month is not None:
        monthly_results[current_month] = closed_pnl.copy()
    return monthly_results

def evaluate():
    print("Memulai Backtest Adaptive Self-Learning (ADX Trend Recognition)...")
    df = get_data()
    if df is None: return
    res = run_simulation(df)
    
    print("\n--- ADAPTIVE SELF-LEARNING RESULTS (JAN-JUL 2026) ---")
    print(f"{'Bulan':<10} | {'Profit Net':<15} | {'Winrate':<10} | {'Total OP'}")
    print("-" * 55)
    
    total_prof = 0
    total_wins = 0
    total_trades = 0
    for m, pnl in res.items():
        p = sum(pnl)
        total_prof += p
        wins = len([x for x in pnl if x > 0])
        trades = len(pnl)
        wr = (wins/trades*100) if trades>0 else 0
        total_wins += wins
        total_trades += trades
        print(f"{m:<10} | ${p:>13,.2f} | {wr:>8.1f}% | {trades}")
        
    print("-" * 55)
    avg_wr = (total_wins/total_trades*100) if total_trades>0 else 0
    print(f"TOTAL      | ${total_prof:>13,.2f} | {avg_wr:>8.1f}% | {total_trades}")

if __name__ == '__main__':
    evaluate()
