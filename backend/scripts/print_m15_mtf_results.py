import pandas as pd
import numpy as np

m15 = pd.read_csv('data/ticks/xauusd_M15.csv').set_index('datetime')
m30 = pd.read_csv('data/ticks/xauusd_M30.csv').set_index('datetime')
h1 = pd.read_csv('data/ticks/xauusd_H1.csv').set_index('datetime')
h4 = pd.read_csv('data/ticks/xauusd_H4.csv').set_index('datetime')

df = m15.copy()
df['m30_delta'] = m30['delta_pct'].reindex(df.index, method='ffill')
df['h1_delta'] = h1['delta_pct'].reindex(df.index, method='ffill')
df['h4_delta'] = h4['delta_pct'].reindex(df.index, method='ffill')
df.dropna(inplace=True)

print("="*80)
print("M15 MULTI-TIMEFRAME TICK MODE OPTIMIZATION (1.00 LOT)")
print("="*80)

results = []
for tp in [0, 8, 10, 12, 15]:
    for sl in [0, 15, 20]:
        trades = []
        in_pos, pos_type, entry_p = False, None, 0.0
        for i in range(len(df)-1):
            r = df.iloc[i]
            d = r['delta_pct']
            d30 = r['m30_delta']
            dh1 = r['h1_delta']
            
            if in_pos:
                curr_p, high_p, low_p = r['close'], r['high'], r['low']
                exited, exit_p = False, curr_p
                if pos_type == 'BUY':
                    if tp > 0 and high_p >= entry_p + tp: exited, exit_p = True, entry_p + tp
                    elif sl > 0 and low_p <= entry_p - sl: exited, exit_p = True, entry_p - sl
                    elif tp == 0 and d < 2.0: exited, exit_p = True, curr_p
                    elif d < -2.0: exited, exit_p = True, curr_p
                else:
                    if tp > 0 and low_p <= entry_p - tp: exited, exit_p = True, entry_p - tp
                    elif sl > 0 and high_p >= entry_p + sl: exited, exit_p = True, entry_p + sl
                    elif tp == 0 and d > -2.0: exited, exit_p = True, curr_p
                    elif d > 2.0: exited, exit_p = True, curr_p
                if exited:
                    pnl = (exit_p - entry_p)*100.0 if pos_type == 'BUY' else (entry_p - exit_p)*100.0
                    trades.append({'pnl': pnl, 'won': pnl > 0})
                    in_pos, pos_type = False, None
            if not in_pos:
                b_trig = (5.0 <= d <= 10.0) and (dh1 > 0 or d30 > 0)
                s_trig = (-10.0 <= d <= -5.0) and (dh1 < 0 or d30 < 0)
                if b_trig: in_pos, pos_type, entry_p = True, 'BUY', r['close']
                elif s_trig: in_pos, pos_type, entry_p = True, 'SELL', r['close']
        if trades:
            tdf = pd.DataFrame(trades)
            wr = (tdf['won'].sum() / len(tdf)) * 100.0
            tot_pnl = tdf['pnl'].sum()
            p_sum = tdf[tdf['pnl'] > 0]['pnl'].sum()
            l_sum = abs(tdf[tdf['pnl'] < 0]['pnl'].sum())
            pf = (p_sum / l_sum) if l_sum > 0 else 99.0
            results.append({
                'tp': tp,
                'sl': sl,
                'trades': len(tdf),
                'winrate': wr,
                'net_pnl': tot_pnl,
                'profit_factor': pf
            })

rdf = pd.DataFrame(results).sort_values(by='net_pnl', ascending=False)
print(rdf.to_string(index=False))
