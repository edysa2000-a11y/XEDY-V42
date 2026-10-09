import pandas as pd
import numpy as np

m30 = pd.read_csv('data/ticks/xauusd_M30_1month.csv').set_index('datetime')
h1 = pd.read_csv('data/ticks/xauusd_H1_1month.csv').set_index('datetime')
m15 = pd.read_csv('data/ticks/xauusd_M15_1month.csv').set_index('datetime')

# Prepare M30
df_m30 = m30.copy()
df_m30['h1_delta'] = h1['delta_pct'].reindex(df_m30.index, method='ffill')
df_m30.dropna(inplace=True)

# Prepare M15
df_m15 = m15.copy()
df_m15['h1_delta'] = h1['delta_pct'].reindex(df_m15.index, method='ffill')
df_m15.dropna(inplace=True)

def evaluate_strategy(df_input, use_htf, tp_pts, sl_pts, delta_min=5.0, delta_max=10.0, exit_threshold=2.0, initial_capital=10000.0, lot_size=1.00):
    balance = initial_capital
    peak_balance = initial_capital
    max_dd_dollar = 0.0
    max_dd_pct = 0.0
    trades = []
    in_pos, pos_type, entry_p, entry_t = False, None, 0.0, None
    
    for i in range(len(df_input)-1):
        r = df_input.iloc[i]
        d = r['delta_pct']
        dh1 = r.get('h1_delta', 0.0)
        curr_p, high_p, low_p = r['close'], r['high'], r['low']
        
        if in_pos:
            exited, exit_p, reason = False, curr_p, ''
            if pos_type == 'BUY':
                if tp_pts > 0 and high_p >= entry_p + tp_pts:
                    exited, exit_p, reason = True, entry_p + tp_pts, 'HIT_TP'
                elif sl_pts > 0 and low_p <= entry_p - sl_pts:
                    exited, exit_p, reason = True, entry_p - sl_pts, 'HIT_SL'
                elif d < exit_threshold:
                    exited, exit_p, reason = True, curr_p, 'EXHAUSTION'
            else: # SELL
                if tp_pts > 0 and low_p <= entry_p - tp_pts:
                    exited, exit_p, reason = True, entry_p - tp_pts, 'HIT_TP'
                elif sl_pts > 0 and high_p >= entry_p + sl_pts:
                    exited, exit_p, reason = True, entry_p + sl_pts, 'HIT_SL'
                elif d > -exit_threshold:
                    exited, exit_p, reason = True, curr_p, 'EXHAUSTION'
                    
            if exited:
                points = (exit_p - entry_p) if pos_type == 'BUY' else (entry_p - exit_p)
                pnl = points * lot_size * 100.0
                balance += pnl
                if balance > peak_balance:
                    peak_balance = balance
                cur_dd_dollar = peak_balance - balance
                cur_dd_pct = (cur_dd_dollar / peak_balance) * 100.0
                if cur_dd_dollar > max_dd_dollar: max_dd_dollar = cur_dd_dollar
                if cur_dd_pct > max_dd_pct: max_dd_pct = cur_dd_pct
                
                trades.append({'pnl': pnl, 'won': pnl > 0})
                in_pos, pos_type = False, None
                
        if not in_pos:
            buy_cond = (delta_min <= d <= delta_max)
            sell_cond = (-delta_max <= d <= -delta_min)
            if use_htf:
                buy_cond = buy_cond and (dh1 > 0)
                sell_cond = sell_cond and (dh1 < 0)
                
            if buy_cond: in_pos, pos_type, entry_p, entry_t = True, 'BUY', curr_p, r.name
            elif sell_cond: in_pos, pos_type, entry_p, entry_t = True, 'SELL', curr_p, r.name
            
    if trades:
        tdf = pd.DataFrame(trades)
        wins = tdf['won'].sum()
        total = len(tdf)
        wr = (wins / total) * 100.0
        net_pnl = balance - initial_capital
        profit_pct = (net_pnl / initial_capital) * 100.0
        g_prof = tdf[tdf['pnl'] > 0]['pnl'].sum()
        g_loss = abs(tdf[tdf['pnl'] < 0]['pnl'].sum())
        pf = (g_prof / g_loss) if g_loss > 0 else 99.0
        return {
            'trades': total, 'wins': wins, 'losses': total - wins,
            'winrate': wr, 'final_balance': balance, 'net_pnl': net_pnl,
            'profit_pct': profit_pct, 'max_dd_pct': max_dd_pct,
            'max_dd_dollar': max_dd_dollar, 'profit_factor': pf
        }
    return None

print("="*85)
print("PARAMETER SCAN: TIMEFRAME M30 (1 BULAN • $10,000 • 1 LOT)")
print("="*85)

results = []
for use_htf in [False, True]:
    for tp in [0, 8, 10, 12, 15]:
        for sl in [0, 8, 10, 12, 15, 20]:
            r = evaluate_strategy(df_m30, use_htf=use_htf, tp_pts=tp, sl_pts=sl)
            if r:
                r['use_htf'] = use_htf
                r['tp'] = tp
                r['sl'] = sl
                results.append(r)

rdf = pd.DataFrame(results).sort_values(by='profit_pct', ascending=False)
print("TOP 10 PERFORMA TERBAIK M30:")
cols = ['use_htf', 'tp', 'sl', 'trades', 'winrate', 'profit_pct', 'max_dd_pct', 'final_balance', 'profit_factor']
print(rdf[cols].head(10).to_string(index=False))

print("\n" + "="*85)
print("PARAMETER SCAN: TIMEFRAME M15 (1 BULAN • $10,000 • 1 LOT)")
print("="*85)
results_m15 = []
for use_htf in [False, True]:
    for tp in [0, 8, 10, 12, 15]:
        for sl in [0, 8, 10, 12, 15, 20]:
            r = evaluate_strategy(df_m15, use_htf=use_htf, tp_pts=tp, sl_pts=sl)
            if r:
                r['use_htf'] = use_htf
                r['tp'] = tp
                r['sl'] = sl
                results_m15.append(r)

rdf_m15 = pd.DataFrame(results_m15).sort_values(by='profit_pct', ascending=False)
print("TOP 10 PERFORMA TERBAIK M15:")
print(rdf_m15[cols].head(10).to_string(index=False))
