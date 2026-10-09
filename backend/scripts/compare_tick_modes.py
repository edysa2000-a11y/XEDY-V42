import pandas as pd
import numpy as np

# Load real MT5 tick aggregations for XAUUSD
m5 = pd.read_csv('data/ticks/xauusd_M5.csv').set_index('datetime')
m15 = pd.read_csv('data/ticks/xauusd_M15.csv').set_index('datetime')
m30 = pd.read_csv('data/ticks/xauusd_M30.csv').set_index('datetime')
h1 = pd.read_csv('data/ticks/xauusd_H1.csv').set_index('datetime')
h4 = pd.read_csv('data/ticks/xauusd_H4.csv').set_index('datetime')

# Combine into master execution dataset on M5
df = m5.copy()
df['m15_delta'] = m15['delta_pct'].reindex(df.index, method='ffill')
df['m30_delta'] = m30['delta_pct'].reindex(df.index, method='ffill')
df['h1_delta'] = h1['delta_pct'].reindex(df.index, method='ffill')
df['h4_delta'] = h4['delta_pct'].reindex(df.index, method='ffill')
df.dropna(inplace=True)

# 1. Backtest Baseline Rule (User Raw Rule on M5):
# Entry: 5 <= delta <= 10. Exit: delta < 2% (No SL, No TP)
base_trades = []
in_pos, pos_type, entry_p, entry_t = False, None, 0.0, None

for i in range(len(df)-1):
    r = df.iloc[i]
    d = r['delta_pct']
    curr_p = r['close']
    
    if in_pos:
        if pos_type == 'BUY' and d < 2.0:
            pnl = (curr_p - entry_p) * 100.0
            base_trades.append({'type': 'BUY', 'entry_t': entry_t, 'exit_t': r.name, 'entry_p': entry_p, 'exit_p': curr_p, 'pnl': pnl, 'won': pnl > 0})
            in_pos, pos_type = False, None
        elif pos_type == 'SELL' and d > -2.0:
            pnl = (entry_p - curr_p) * 100.0
            base_trades.append({'type': 'SELL', 'entry_t': entry_t, 'exit_t': r.name, 'entry_p': entry_p, 'exit_p': curr_p, 'pnl': pnl, 'won': pnl > 0})
            in_pos, pos_type = False, None
            
    if not in_pos:
        if 5.0 <= d <= 10.0:
            in_pos, pos_type, entry_p, entry_t = True, 'BUY', curr_p, r.name
        elif -10.0 <= d <= -5.0:
            in_pos, pos_type, entry_p, entry_t = True, 'SELL', curr_p, r.name

b_df = pd.DataFrame(base_trades)

# 2. Backtest Enhanced Institutional MTF TICK Mode Engine:
# Execution: M5 with M15/M30/H1 Confluence + TP + SL + Trailing BEP + Exhaustion Exit
tp_pts = 10.0
sl_pts = 15.0
enh_trades = []
in_pos, pos_type, entry_p, entry_t = False, None, 0.0, None
cur_sl = 0.0

for i in range(len(df)-1):
    r = df.iloc[i]
    d = r['delta_pct']
    d15 = r['m15_delta']
    d30 = r['m30_delta']
    dh1 = r['h1_delta']
    curr_p = r['close']
    high_p = r['high']
    low_p = r['low']
    
    if in_pos:
        exited, exit_p, exit_reason = False, curr_p, ''
        if pos_type == 'BUY':
            # Check Trailing BEP: if floating +5 pts, move SL to entry + 0.5
            if high_p >= entry_p + 5.0:
                cur_sl = max(cur_sl, entry_p + 0.5)
                
            if high_p >= entry_p + tp_pts:
                exited, exit_p, exit_reason = True, entry_p + tp_pts, 'HIT_TP'
            elif low_p <= cur_sl:
                exited, exit_p = True, cur_sl
                exit_reason = 'HIT_BEP' if cur_sl >= entry_p else 'HIT_SL'
            elif d < 2.0: # Exhaustion
                exited, exit_p, exit_reason = True, curr_p, 'EXHAUSTION'
            elif d < -3.0: # Reversal
                exited, exit_p, exit_reason = True, curr_p, 'REVERSAL'
        else: # SELL
            if low_p <= entry_p - 5.0:
                cur_sl = min(cur_sl, entry_p - 0.5)
                
            if low_p <= entry_p - tp_pts:
                exited, exit_p, exit_reason = True, entry_p - tp_pts, 'HIT_TP'
            elif high_p >= cur_sl:
                exited, exit_p = True, cur_sl
                exit_reason = 'HIT_BEP' if cur_sl <= entry_p else 'HIT_SL'
            elif d > -2.0:
                exited, exit_p, exit_reason = True, curr_p, 'EXHAUSTION'
            elif d > 3.0:
                exited, exit_p, exit_reason = True, curr_p, 'REVERSAL'
                
        if exited:
            pnl = (exit_p - entry_p)*100.0 if pos_type == 'BUY' else (entry_p - exit_p)*100.0
            enh_trades.append({
                'type': pos_type,
                'entry_t': entry_t,
                'exit_t': r.name,
                'entry_p': entry_p,
                'exit_p': exit_p,
                'reason': exit_reason,
                'pnl': pnl,
                'won': pnl > 0
            })
            in_pos, pos_type = False, None
            
    if not in_pos:
        # Multi-timeframe confluence rule:
        buy_conf = (5.0 <= d <= 12.0) and (dh1 > 0 or d30 > 0) and (d15 >= 0)
        sell_conf = (-12.0 <= d <= -5.0) and (dh1 < 0 or d30 < 0) and (d15 <= 0)
        
        if buy_conf:
            in_pos, pos_type, entry_p, entry_t = True, 'BUY', curr_p, r.name
            cur_sl = entry_p - sl_pts
        elif sell_conf:
            in_pos, pos_type, entry_p, entry_t = True, 'SELL', curr_p, r.name
            cur_sl = entry_p + sl_pts

e_df = pd.DataFrame(enh_trades)

print("="*85)
print("HASIL KOMPARASI BACKTEST 1 MINGGU (XAUUSD • 1.00 LOT)")
print("="*85)

print("\n1. BASELINE TICK MODE (RULE ASLI USER):")
b_wins = b_df['won'].sum()
b_wr = (b_wins / len(b_df)) * 100
b_pnl = b_df['pnl'].sum()
b_profit = b_df[b_df['pnl'] > 0]['pnl'].sum()
b_loss = abs(b_df[b_df['pnl'] < 0]['pnl'].sum())
b_pf = (b_profit / b_loss) if b_loss > 0 else 99.0
print(f"Total Trade : {len(b_df)}")
print(f"Win / Loss  : {b_wins} Win / {len(b_df)-b_wins} Loss")
print(f"Winrate     : {b_wr:.2f}%")
print(f"Net PnL     : ${b_pnl:,.2f}")
print(f"Profit Fact : {b_pf:.2f}")

print("\n2. ENHANCED INSTITUTIONAL MTF TICK MODE ENGINE (METODE BARU):")
e_wins = e_df['won'].sum()
e_wr = (e_wins / len(e_df)) * 100
e_pnl = e_df['pnl'].sum()
e_profit = e_df[e_df['pnl'] > 0]['pnl'].sum()
e_loss = abs(e_df[e_df['pnl'] < 0]['pnl'].sum())
e_pf = (e_profit / e_loss) if e_loss > 0 else 99.0
print(f"Total Trade : {len(e_df)}")
print(f"Win / Loss  : {e_wins} Win / {len(e_df)-e_wins} Loss")
print(f"Winrate     : {e_wr:.2f}%")
print(f"Net PnL     : ${e_pnl:,.2f}")
print(f"Profit Fact : {e_pf:.2f}")
print("\nExit Breakdown:")
print(e_df['reason'].value_counts())

e_df.to_csv('backend/scripts/tick_mode_enhanced_trades.csv', index=False)
