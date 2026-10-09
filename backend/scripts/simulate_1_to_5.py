import pandas as pd
import numpy as np

# Load 1-month M30 and M15 data for XAUUSD
m30 = pd.read_csv('data/ticks/xauusd_M30_1month.csv').set_index('datetime')
m15 = pd.read_csv('data/ticks/xauusd_M15_1month.csv').set_index('datetime')

def run_threshold_sim(df_input, th_entry, exit_ratio=0.4, initial_capital=10000.0, lot_size=1.00):
    th_exit = th_entry * exit_ratio # misal untuk 5%, exit = 5 * 0.4 = 2.0% (persis ide user)
    balance = initial_capital
    peak = initial_capital
    max_dd_dollar = 0.0
    max_dd_pct = 0.0
    trades = []
    in_pos, pos_type, entry_p, entry_t = False, None, 0.0, None
    
    for i in range(len(df_input)-1):
        r = df_input.iloc[i]
        d = r['delta_pct']
        curr_p = r['close']
        
        if in_pos:
            exited = False
            if pos_type == 'BUY' and d < th_exit:
                exited = True
            elif pos_type == 'SELL' and d > -th_exit:
                exited = True
                
            if exited:
                points = (curr_p - entry_p) if pos_type == 'BUY' else (entry_p - curr_p)
                pnl = points * lot_size * 100.0 # $100 per 1.00 lot
                balance += pnl
                if balance > peak:
                    peak = balance
                dd_d = peak - balance
                dd_p = (dd_d / peak * 100.0) if peak > 0 else 0.0
                if dd_d > max_dd_dollar: max_dd_dollar = dd_d
                if dd_p > max_dd_pct: max_dd_pct = dd_p
                
                trades.append({'pnl': pnl, 'won': pnl > 0, 'balance': balance})
                in_pos, pos_type = False, None
                
        if not in_pos:
            if d >= th_entry:
                in_pos, pos_type, entry_p, entry_t = True, 'BUY', curr_p, r.name
            elif d <= -th_entry:
                in_pos, pos_type, entry_p, entry_t = True, 'SELL', curr_p, r.name
                
    tdf = pd.DataFrame(trades)
    if len(tdf) == 0:
        return None
        
    wins = int(tdf['won'].sum())
    total = len(tdf)
    wr = (wins / total * 100.0)
    net_pnl = balance - initial_capital
    profit_pct = (net_pnl / initial_capital * 100.0)
    g_p = tdf[tdf['pnl'] > 0]['pnl'].sum()
    g_l = abs(tdf[tdf['pnl'] < 0]['pnl'].sum())
    pf = (g_p / g_l) if g_l > 0 else 99.0
    avg_gain = tdf['pnl'].mean()
    
    return {
        'threshold': th_entry,
        'exit_th': round(th_exit, 2),
        'trades': total,
        'wins': wins,
        'losses': total - wins,
        'winrate': wr,
        'profit_pct': profit_pct,
        'max_dd_pct': max_dd_pct,
        'max_dd_dollar': max_dd_dollar,
        'final_balance': balance,
        'profit_factor': pf,
        'avg_gain': avg_gain
    }

print("="*95)
print("HASIL SIMULASI AMBANG BATAS SELISIH TICK: 1%, 2%, 3%, 4%, 5%")
print("Modal: $10,000.00 USD • Fix 1.00 Lot ($100/poin) • Data 1 Bulan MT5 XAUUSD")
print("="*95)

thresholds = [1.0, 2.0, 3.0, 4.0, 5.0]

print("\n--- A. TIMEFRAME M30 (1 BULAN PENUH) ---")
res_m30 = [run_threshold_sim(m30, th, exit_ratio=0.4) for th in thresholds]
df_m30 = pd.DataFrame(res_m30)
cols = ['threshold', 'exit_th', 'trades', 'winrate', 'profit_pct', 'max_dd_pct', 'max_dd_dollar', 'final_balance', 'profit_factor', 'avg_gain']
print(df_m30[cols].to_string(index=False))

print("\n--- B. TIMEFRAME M15 (1 BULAN PENUH) ---")
res_m15 = [run_threshold_sim(m15, th, exit_ratio=0.4) for th in thresholds]
df_m15 = pd.DataFrame(res_m15)
print(df_m15[cols].to_string(index=False))

# Also test Pendekatan B: Fixed Exit saat berbalik arah (Delta < 0%)
print("\n" + "="*95)
print("VARIASI B: EXIT SAAT REVERSAL BERBALIK ARAH (DELTA < 0%)")
print("="*95)

def run_zero_exit_sim(df_input, th_entry, initial_capital=10000.0, lot_size=1.00):
    balance = initial_capital
    peak = initial_capital
    max_dd_dollar = 0.0
    max_dd_pct = 0.0
    trades = []
    in_pos, pos_type, entry_p = False, None, 0.0
    
    for i in range(len(df_input)-1):
        r = df_input.iloc[i]
        d = r['delta_pct']
        curr_p = r['close']
        
        if in_pos:
            exited = False
            if pos_type == 'BUY' and d < 0.0: exited = True
            elif pos_type == 'SELL' and d > 0.0: exited = True
            if exited:
                points = (curr_p - entry_p) if pos_type == 'BUY' else (entry_p - curr_p)
                pnl = points * lot_size * 100.0
                balance += pnl
                if balance > peak: peak = balance
                dd_d = peak - balance
                dd_p = (dd_d / peak * 100.0) if peak > 0 else 0.0
                if dd_d > max_dd_dollar: max_dd_dollar = dd_d
                if dd_p > max_dd_pct: max_dd_pct = dd_p
                trades.append({'pnl': pnl, 'won': pnl > 0})
                in_pos, pos_type = False, None
        if not in_pos:
            if d >= th_entry: in_pos, pos_type, entry_p = True, 'BUY', curr_p
            elif d <= -th_entry: in_pos, pos_type, entry_p = True, 'SELL', curr_p
            
    tdf = pd.DataFrame(trades)
    wins = int(tdf['won'].sum())
    total = len(tdf)
    wr = (wins / total * 100.0) if total > 0 else 0.0
    net_pnl = balance - initial_capital
    profit_pct = (net_pnl / initial_capital * 100.0)
    g_p = tdf[tdf['pnl'] > 0]['pnl'].sum()
    g_l = abs(tdf[tdf['pnl'] < 0]['pnl'].sum())
    pf = (g_p / g_l) if g_l > 0 else 99.0
    return {
        'threshold': th_entry, 'trades': total, 'winrate': wr,
        'profit_pct': profit_pct, 'max_dd_pct': max_dd_pct,
        'max_dd_dollar': max_dd_dollar, 'final_balance': balance, 'profit_factor': pf
    }

res_m30_zero = [run_zero_exit_sim(m30, th) for th in thresholds]
df_m30_zero = pd.DataFrame(res_m30_zero)
print(df_m30_zero[['threshold', 'trades', 'winrate', 'profit_pct', 'max_dd_pct', 'final_balance', 'profit_factor']].to_string(index=False))
