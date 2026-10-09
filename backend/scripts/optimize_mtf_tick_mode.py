import pandas as pd
import numpy as np

m5 = pd.read_csv('data/ticks/xauusd_M5.csv')
m5['datetime'] = pd.to_datetime(m5['datetime'])
m5.set_index('datetime', inplace=True)

m15 = pd.read_csv('data/ticks/xauusd_M15.csv')
m15['datetime'] = pd.to_datetime(m15['datetime'])
m15.set_index('datetime', inplace=True)

m30 = pd.read_csv('data/ticks/xauusd_M30.csv')
m30['datetime'] = pd.to_datetime(m30['datetime'])
m30.set_index('datetime', inplace=True)

h1 = pd.read_csv('data/ticks/xauusd_H1.csv')
h1['datetime'] = pd.to_datetime(h1['datetime'])
h1.set_index('datetime', inplace=True)

# Merge MTF context into M5
df = m5.copy()
df['m15_delta'] = m15['delta_pct'].reindex(df.index, method='ffill')
df['m30_delta'] = m30['delta_pct'].reindex(df.index, method='ffill')
df['h1_delta'] = h1['delta_pct'].reindex(df.index, method='ffill')
df.dropna(inplace=True)

print("Testing Multi-Timeframe TICK Confluence Strategy on M5...")

# Let's test combinations:
# Confluence condition:
# BUY: M5 delta 5-10% AND (M30 delta > 0 or H1 delta > 0)
# Dynamic TP and SL

configs = [
    # (tp, sl, use_htf, max_hold_bars)
    (0, 0, False, 0), # Baseline
    (0, 0, True, 0),  # Baseline + MTF filter
    (8, 15, True, 24),
    (10, 15, True, 24),
    (12, 18, True, 24),
    (15, 20, True, 36),
    (10, 20, True, 24),
    (15, 25, True, 36)
]

for tp_pts, sl_pts, use_htf, max_bars in configs:
    trades = []
    in_pos = False
    pos_type = None
    entry_p = 0.0
    entry_idx = 0
    
    for i in range(len(df)-1):
        row = df.iloc[i]
        d_m5 = row['delta_pct']
        d_m30 = row['m30_delta']
        d_h1 = row['h1_delta']
        
        # Check exit
        if in_pos:
            bars_held = i - entry_idx
            curr_p = row['close']
            high_p = row['high']
            low_p = row['low']
            exit_trade = False
            exit_p = curr_p
            
            if pos_type == 'BUY':
                if tp_pts > 0 and high_p >= entry_p + tp_pts:
                    exit_trade = True
                    exit_p = entry_p + tp_pts
                elif sl_pts > 0 and low_p <= entry_p - sl_pts:
                    exit_trade = True
                    exit_p = entry_p - sl_pts
                elif tp_pts == 0 and d_m5 < 2.0:
                    exit_trade = True
                    exit_p = curr_p
                elif max_bars > 0 and bars_held >= max_bars:
                    exit_trade = True
                    exit_p = curr_p
                elif d_m5 < 0.0: # Reversal exit
                    exit_trade = True
                    exit_p = curr_p
            else: # SELL
                if tp_pts > 0 and low_p <= entry_p - tp_pts:
                    exit_trade = True
                    exit_p = entry_p - tp_pts
                elif sl_pts > 0 and high_p >= entry_p + sl_pts:
                    exit_trade = True
                    exit_p = entry_p + sl_pts
                elif tp_pts == 0 and d_m5 > -2.0:
                    exit_trade = True
                    exit_p = curr_p
                elif max_bars > 0 and bars_held >= max_bars:
                    exit_trade = True
                    exit_p = curr_p
                elif d_m5 > 0.0:
                    exit_trade = True
                    exit_p = curr_p
                    
            if exit_trade:
                pnl = (exit_p - entry_p)*100.0 if pos_type == 'BUY' else (entry_p - exit_p)*100.0
                trades.append({'pnl': pnl, 'won': pnl > 0})
                in_pos = False
                pos_type = None
                
        # Check entry
        if not in_pos:
            buy_trig = (5.0 <= d_m5 <= 10.0)
            sell_trig = (-10.0 <= d_m5 <= -5.0)
            
            if use_htf:
                buy_trig = buy_trig and (d_m30 > 0 or d_h1 > 0)
                sell_trig = sell_trig and (d_m30 < 0 or d_h1 < 0)
                
            if buy_trig:
                in_pos = True
                pos_type = 'BUY'
                entry_p = row['close']
                entry_idx = i
            elif sell_trig:
                in_pos = True
                pos_type = 'SELL'
                entry_p = row['close']
                entry_idx = i
                
    if trades:
        tdf = pd.DataFrame(trades)
        wins = tdf['won'].sum()
        total = len(tdf)
        wr = (wins / total) * 100.0
        pnl_tot = tdf['pnl'].sum()
        p_trades = tdf[tdf['pnl'] > 0]['pnl'].sum()
        l_trades = abs(tdf[tdf['pnl'] < 0]['pnl'].sum())
        pf = (p_trades / l_trades) if l_trades > 0 else 99.0
        print(f"TP: {tp_pts:2d} | SL: {sl_pts:2d} | HTF: {str(use_htf):5s} | Trades: {total:3d} | WR: {wr:5.1f}% | Net USD: ${pnl_tot:9.2f} | PF: {pf:4.2f}")
