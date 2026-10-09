import pandas as pd
import numpy as np

# Load 1-month resampled data for XAUUSD
m15 = pd.read_csv('data/ticks/xauusd_M15_1month.csv').set_index('datetime')
m30 = pd.read_csv('data/ticks/xauusd_M30_1month.csv').set_index('datetime')
h1 = pd.read_csv('data/ticks/xauusd_H1_1month.csv').set_index('datetime')

def simulate_5_10(df_input, lot_size=1.00, initial_capital=10000.0, exit_th=2.0, sl_pts=0.0, tp_pts=0.0):
    balance = initial_capital
    peak_balance = initial_capital
    max_dd_dollar = 0.0
    max_dd_pct = 0.0
    trades = []
    in_pos, pos_type, entry_p, entry_t = False, None, 0.0, None
    
    for i in range(len(df_input)-1):
        r = df_input.iloc[i]
        d = r['delta_pct']
        curr_p, high_p, low_p = r['close'], r['high'], r['low']
        
        # Check exit
        if in_pos:
            exited = False
            exit_p = curr_p
            exit_reason = 'EXHAUSTION (<2%)'
            
            if pos_type == 'BUY':
                if tp_pts > 0 and high_p >= entry_p + tp_pts:
                    exited = True
                    exit_p = entry_p + tp_pts
                    exit_reason = 'HIT TP'
                elif sl_pts > 0 and low_p <= entry_p - sl_pts:
                    exited = True
                    exit_p = entry_p - sl_pts
                    exit_reason = 'HIT SL'
                elif d < exit_th:
                    exited = True
                    exit_p = curr_p
            else: # SELL
                if tp_pts > 0 and low_p <= entry_p - tp_pts:
                    exited = True
                    exit_p = entry_p - tp_pts
                    exit_reason = 'HIT TP'
                elif sl_pts > 0 and high_p >= entry_p + sl_pts:
                    exited = True
                    exit_p = entry_p + sl_pts
                    exit_reason = 'HIT SL'
                elif d > -exit_th:
                    exited = True
                    exit_p = curr_p
                    
            if exited:
                points = (exit_p - entry_p) if pos_type == 'BUY' else (entry_p - exit_p)
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
                    'entry_t': str(entry_t),
                    'exit_t': str(r.name),
                    'type': pos_type,
                    'op': round(entry_p, 2),
                    'exit_p': round(exit_p, 2),
                    'points': round(points, 2),
                    'pnl': round(pnl, 2),
                    'balance': round(balance, 2),
                    'dd_pct': round(cur_dd_pct, 2),
                    'reason': exit_reason,
                    'won': pnl > 0
                })
                in_pos, pos_type = False, None
                
        # Check entry
        if not in_pos:
            if 5.0 <= d <= 10.0:
                in_pos, pos_type, entry_p, entry_t = True, 'BUY', curr_p, r.name
            elif -10.0 <= d <= -5.0:
                in_pos, pos_type, entry_p, entry_t = True, 'SELL', curr_p, r.name
                
    tdf = pd.DataFrame(trades)
    if len(tdf) == 0:
        return None
        
    wins = int((tdf['won'] == True).sum())
    total = len(tdf)
    losses = total - wins
    wr = (wins / total * 100.0) if total > 0 else 0.0
    net_pnl = balance - initial_capital
    profit_pct = (net_pnl / initial_capital * 100.0)
    
    pos_trades = tdf[tdf['pnl'] > 0]['pnl']
    neg_trades = tdf[tdf['pnl'] < 0]['pnl']
    g_profit = pos_trades.sum() if len(pos_trades) > 0 else 0.0
    g_loss = abs(neg_trades.sum()) if len(neg_trades) > 0 else 0.0
    pf = (g_profit / g_loss) if g_loss > 0 else 99.0
    
    avg_win = pos_trades.mean() if len(pos_trades) > 0 else 0.0
    avg_loss = neg_trades.mean() if len(neg_trades) > 0 else 0.0
    max_win = pos_trades.max() if len(pos_trades) > 0 else 0.0
    max_loss = neg_trades.min() if len(neg_trades) > 0 else 0.0
    
    # Calculate streaks
    streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    cur_type = None
    for w in tdf['won']:
        if w:
            if cur_type == 'win': streak += 1
            else: streak = 1; cur_type = 'win'
            max_win_streak = max(max_win_streak, streak)
        else:
            if cur_type == 'loss': streak += 1
            else: streak = 1; cur_type = 'loss'
            max_loss_streak = max(max_loss_streak, streak)
            
    return {
        'tdf': tdf,
        'lot_size': lot_size,
        'initial_capital': initial_capital,
        'final_balance': balance,
        'net_pnl': net_pnl,
        'profit_pct': profit_pct,
        'max_dd_pct': max_dd_pct,
        'max_dd_dollar': max_dd_dollar,
        'total_trades': total,
        'wins': wins,
        'losses': losses,
        'winrate': wr,
        'g_profit': g_profit,
        'g_loss': g_loss,
        'profit_factor': pf,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_win': max_win,
        'max_loss': max_loss,
        'max_win_streak': max_win_streak,
        'max_loss_streak': max_loss_streak
    }

print("="*90)
print("SIMULASI ULANG 5-10% PADA TIMEFRAME M30 (MODAL $10,000 • 1 BULAN)")
print("="*90)

for lot in [1.00, 0.50, 0.30, 0.20, 0.10]:
    r = simulate_5_10(m30, lot_size=lot, initial_capital=10000.0)
    print(f"Lot: {lot:4.2f} | Saldo: ${r['final_balance']:9.2f} | Net: ${r['net_pnl']:+9.2f} | ROI: {r['profit_pct']:+6.2f}% | Max DD: {r['max_dd_pct']:5.2f}% (${r['max_dd_dollar']:7.2f}) | PF: {r['profit_factor']:.2f}")

# Detail breakdown untuk 1.00 Lot dan 0.30 Lot
r100 = simulate_5_10(m30, lot_size=1.00, initial_capital=10000.0)
r030 = simulate_5_10(m30, lot_size=0.30, initial_capital=10000.0)

print("\n--- STATISTIK LENGKAP 1.00 LOT ---")
print(f"Total Trade        : {r100['total_trades']}")
print(f"Win / Loss         : {r100['wins']} Win / {r100['losses']} Loss")
print(f"Winrate            : {r100['winrate']:.2f}%")
print(f"Gross Profit       : ${r100['g_profit']:,.2f}")
print(f"Gross Loss         : -${r100['g_loss']:,.2f}")
print(f"Net Profit         : ${r100['net_pnl']:,.2f} ({r100['profit_pct']:+.2f}%)")
print(f"Max Drawdown       : {r100['max_dd_pct']:.2f}% (${r100['max_dd_dollar']:,.2f})")
print(f"Rata-rata Win      : +${r100['avg_win']:,.2f}")
print(f"Rata-rata Loss     : -${abs(r100['avg_loss']):,.2f}")
print(f"Win Terbesar       : +${r100['max_win']:,.2f}")
print(f"Loss Terbesar      : -${abs(r100['max_loss']):,.2f}")
print(f"Max Win Streak     : {r100['max_win_streak']} berturut-turut")
print(f"Max Loss Streak    : {r100['max_loss_streak']} berturut-turut")

print("\n--- STATISTIK LENGKAP 0.30 LOT (OPTIMAL RISK) ---")
print(f"Total Trade        : {r030['total_trades']}")
print(f"Win / Loss         : {r030['wins']} Win / {r030['losses']} Loss")
print(f"Winrate            : {r030['winrate']:.2f}%")
print(f"Gross Profit       : ${r030['g_profit']:,.2f}")
print(f"Gross Loss         : -${r030['g_loss']:,.2f}")
print(f"Net Profit         : ${r030['net_pnl']:,.2f} ({r030['profit_pct']:+.2f}%)")
print(f"Max Drawdown       : {r030['max_dd_pct']:.2f}% (${r030['max_dd_dollar']:,.2f})")
print(f"Rata-rata Win      : +${r030['avg_win']:,.2f}")
print(f"Rata-rata Loss     : -${abs(r030['avg_loss']):,.2f}")
print(f"Win Terbesar       : +${r030['max_win']:,.2f}")
print(f"Loss Terbesar      : -${abs(r030['max_loss']):,.2f}")

# Cek juga pada Timeframe H1 dan M15
print("\n" + "="*90)
print("PERBANDINGAN 5-10% DI SELURUH TIMEFRAME (1.00 LOT)")
print("="*90)
for tf_name, tf_df in [('M15', m15), ('M30', m30), ('H1', h1)]:
    res_tf = simulate_5_10(tf_df, lot_size=1.00, initial_capital=10000.0)
    print(f"TF: {tf_name:4s} | Trades: {res_tf['total_trades']:3d} | WR: {res_tf['winrate']:5.1f}% | Net: ${res_tf['net_pnl']:+9.2f} | ROI: {res_tf['profit_pct']:+6.2f}% | Max DD: {res_tf['max_dd_pct']:5.2f}% | PF: {res_tf['profit_factor']:.2f}")
