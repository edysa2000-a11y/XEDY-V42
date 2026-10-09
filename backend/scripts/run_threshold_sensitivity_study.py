import pandas as pd
import numpy as np

# Load data
m30 = pd.read_csv('data/ticks/xauusd_M30_1month.csv').set_index('datetime')
m15 = pd.read_csv('data/ticks/xauusd_M15_1month.csv').set_index('datetime')
m5 = pd.read_csv('data/ticks/xauusd_M5.csv').set_index('datetime') # 1 week
m1 = pd.read_csv('data/ticks/xauusd_M1.csv').set_index('datetime') # 1 week

def backtest_sim(df_input, threshold, exit_th=2.0, sl_pts=15.0, initial_capital=10000.0, lot_size=1.00):
    balance = initial_capital
    peak = initial_capital
    max_dd_dollar = 0.0
    max_dd_pct = 0.0
    trades = []
    in_pos, pos_type, entry_p, entry_t = False, None, 0.0, None
    
    for i in range(len(df_input)-1):
        r = df_input.iloc[i]
        d = r['delta_pct']
        curr_p, high_p, low_p = r['close'], r['high'], r['low']
        
        if in_pos:
            exited = False
            exit_p = curr_p
            if pos_type == 'BUY':
                if sl_pts > 0 and low_p <= entry_p - sl_pts:
                    exited = True
                    exit_p = entry_p - sl_pts
                elif d < exit_th:
                    exited = True
                    exit_p = curr_p
            else: # SELL
                if sl_pts > 0 and high_p >= entry_p + sl_pts:
                    exited = True
                    exit_p = entry_p + sl_pts
                elif d > -exit_th:
                    exited = True
                    exit_p = curr_p
                    
            if exited:
                pts = (exit_p - entry_p) if pos_type == 'BUY' else (entry_p - exit_p)
                pnl = pts * lot_size * 100.0
                balance += pnl
                if balance > peak:
                    peak = balance
                dd_d = peak - balance
                dd_p = (dd_d / peak * 100.0) if peak > 0 else 0.0
                if dd_d > max_dd_dollar: max_dd_dollar = dd_d
                if dd_p > max_dd_pct: max_dd_pct = dd_p
                
                trades.append({'pnl': pnl, 'won': pnl > 0})
                in_pos, pos_type = False, None
                
        if not in_pos:
            if d >= threshold:
                in_pos, pos_type, entry_p, entry_t = True, 'BUY', curr_p, r.name
            elif d <= -threshold:
                in_pos, pos_type, entry_p, entry_t = True, 'SELL', curr_p, r.name
                
    tdf = pd.DataFrame(trades)
    if len(tdf) == 0:
        return {
            'threshold': threshold, 'trades': 0, 'wins': 0, 'losses': 0,
            'winrate': 0.0, 'profit_pct': 0.0, 'max_dd_pct': 0.0,
            'max_dd_dollar': 0.0, 'final_balance': initial_capital, 'profit_factor': 0.0, 'net_pnl': 0.0
        }
    wins = int(tdf['won'].sum())
    total = len(tdf)
    wr = (wins / total * 100.0)
    net_pnl = balance - initial_capital
    profit_pct = (net_pnl / initial_capital * 100.0)
    g_p = tdf[tdf['pnl'] > 0]['pnl'].sum()
    g_l = abs(tdf[tdf['pnl'] < 0]['pnl'].sum())
    pf = (g_p / g_l) if g_l > 0 else 99.0
    return {
        'threshold': threshold, 'trades': total, 'wins': wins, 'losses': total - wins,
        'winrate': wr, 'profit_pct': profit_pct, 'max_dd_pct': max_dd_pct,
        'max_dd_dollar': max_dd_dollar, 'final_balance': balance, 'profit_factor': pf, 'net_pnl': net_pnl
    }

print("="*95)
print("HASIL SENSITIVITAS SELISIH TICK: 5%, 10%, 15%, 20%, 25% (MODAL $10,000 • 1 LOT)")
print("="*95)

thresholds = [5.0, 10.0, 15.0, 20.0, 25.0]

print("\n--- 1. TIMEFRAME M30 (1 BULAN PENUH) ---")
res_m30 = [backtest_sim(m30, th, exit_th=2.0, sl_pts=15.0) for th in thresholds]
df_m30 = pd.DataFrame(res_m30)
cols = ['threshold', 'trades', 'winrate', 'profit_pct', 'max_dd_pct', 'max_dd_dollar', 'final_balance', 'profit_factor']
print(df_m30[cols].to_string(index=False))

print("\n--- 2. TIMEFRAME M15 (1 BULAN PENUH) ---")
res_m15 = [backtest_sim(m15, th, exit_th=2.0, sl_pts=15.0) for th in thresholds]
df_m15 = pd.DataFrame(res_m15)
print(df_m15[cols].to_string(index=False))

print("\n--- 3. TIMEFRAME M5 (SENSITIVITAS HIGH-FREQUENCY) ---")
res_m5 = [backtest_sim(m5, th, exit_th=2.0, sl_pts=15.0) for th in thresholds]
df_m5 = pd.DataFrame(res_m5)
print(df_m5[cols].to_string(index=False))
