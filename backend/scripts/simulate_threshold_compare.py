import pandas as pd
import numpy as np

# Load 1-month resampled data for XAUUSD
m30 = pd.read_csv('data/ticks/xauusd_M30_1month.csv').set_index('datetime')
h1 = pd.read_csv('data/ticks/xauusd_H1_1month.csv').set_index('datetime')
m15 = pd.read_csv('data/ticks/xauusd_M15_1month.csv').set_index('datetime')

# Let's run simulation on M30 with the user's exit rule (Close when delta < 2%)
def simulate_threshold(df_input, threshold_min, threshold_max=None, exit_threshold=2.0, initial_capital=10000.0, lot_size=1.00):
    balance = initial_capital
    peak_balance = initial_capital
    max_dd_dollar = 0.0
    max_dd_pct = 0.0
    trades = []
    in_pos, pos_type, entry_p, entry_t = False, None, 0.0, None
    
    for i in range(len(df_input)-1):
        r = df_input.iloc[i]
        d = r['delta_pct']
        curr_p = r['close']
        
        # Check exit
        if in_pos:
            exited = False
            if pos_type == 'BUY' and d < exit_threshold:
                exited = True
            elif pos_type == 'SELL' and d > -exit_threshold:
                exited = True
                
            if exited:
                points = (curr_p - entry_p) if pos_type == 'BUY' else (entry_p - curr_p)
                pnl = points * lot_size * 100.0 # $100 per 1.00 lot
                balance += pnl
                if balance > peak_balance:
                    peak_balance = balance
                cur_dd_dollar = peak_balance - balance
                cur_dd_pct = (cur_dd_dollar / peak_balance) * 100.0 if peak_balance > 0 else 0.0
                if cur_dd_dollar > max_dd_dollar:
                    max_dd_dollar = cur_dd_dollar
                if cur_dd_pct > max_dd_pct:
                    max_dd_pct = cur_dd_pct
                    
                trades.append({
                    'pnl': pnl,
                    'won': pnl > 0,
                    'balance': balance,
                    'points': points
                })
                in_pos, pos_type = False, None
                
        # Check entry
        if not in_pos:
            if threshold_max is not None:
                buy_cond = (threshold_min <= d <= threshold_max)
                sell_cond = (-threshold_max <= d <= -threshold_min)
            else:
                buy_cond = (d >= threshold_min)
                sell_cond = (d <= -threshold_min)
                
            if buy_cond:
                in_pos, pos_type, entry_p, entry_t = True, 'BUY', curr_p, r.name
            elif sell_cond:
                in_pos, pos_type, entry_p, entry_t = True, 'SELL', curr_p, r.name
                
    tdf = pd.DataFrame(trades)
    if len(tdf) == 0:
        return None
        
    wins = int(tdf['won'].sum())
    total = len(tdf)
    wr = (wins / total) * 100.0
    net_pnl = balance - initial_capital
    profit_pct = (net_pnl / initial_capital) * 100.0
    g_profit = tdf[tdf['pnl'] > 0]['pnl'].sum()
    g_loss = abs(tdf[tdf['pnl'] < 0]['pnl'].sum())
    pf = (g_profit / g_loss) if g_loss > 0 else 99.0
    avg_gain = tdf['pnl'].mean()
    
    return {
        'threshold': threshold_min,
        'trades': total,
        'wins': wins,
        'losses': total - wins,
        'winrate': wr,
        'final_balance': balance,
        'net_pnl': net_pnl,
        'profit_pct': profit_pct,
        'max_dd_pct': max_dd_pct,
        'max_dd_dollar': max_dd_dollar,
        'profit_factor': pf,
        'avg_gain': avg_gain
    }

print("="*90)
print("SIMULASI 1: AMBANG BATAS MINIMUM (DELTA >= X%, CLOSE < 2%)")
print("="*90)

thresholds = [5.0, 10.0, 15.0, 20.0, 25.0]
results_min = []
for th in thresholds:
    res = simulate_threshold(m30, threshold_min=th, threshold_max=None)
    if res:
        results_min.append(res)

df_res_min = pd.DataFrame(results_min)
cols = ['threshold', 'trades', 'winrate', 'profit_pct', 'max_dd_pct', 'max_dd_dollar', 'final_balance', 'profit_factor', 'avg_gain']
print(df_res_min[cols].to_string(index=False))

print("\n" + "="*90)
print("SIMULASI 2: RANGE BAND (5-10%, 10-15%, 15-20%, 20-25%, 25-30%)")
print("="*90)

ranges = [
    (5.0, 10.0, "5% - 10% (Baseline)"),
    (10.0, 15.0, "10% - 15%"),
    (15.0, 20.0, "15% - 20%"),
    (20.0, 25.0, "20% - 25%"),
    (25.0, 30.0, "25% - 30%")
]

results_band = []
for low, high, label in ranges:
    res = simulate_threshold(m30, threshold_min=low, threshold_max=high)
    if res:
        res['label'] = label
        results_band.append(res)

df_res_band = pd.DataFrame(results_band)
cols_band = ['label', 'trades', 'winrate', 'profit_pct', 'max_dd_pct', 'max_dd_dollar', 'final_balance', 'profit_factor', 'avg_gain']
print(df_res_band[cols_band].to_string(index=False))
