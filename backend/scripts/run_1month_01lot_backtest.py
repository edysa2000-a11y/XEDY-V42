import pandas as pd
import numpy as np

# Load 1-month M30 data
m30 = pd.read_csv('data/ticks/xauusd_M30_1month.csv').set_index('datetime')
m15 = pd.read_csv('data/ticks/xauusd_M15_1month.csv').set_index('datetime')
h1 = pd.read_csv('data/ticks/xauusd_H1_1month.csv').set_index('datetime')

print(f"Loaded 1-month M30 data: {len(m30)} bars from {m30.index[0]} to {m30.index[-1]}")

def backtest_engine(df_input, mode="v2", lot_size=0.10, initial_capital=10000.0, max_layers=2, min_dist=2.0, sl_pts=15.0):
    balance = initial_capital
    peak = initial_capital
    max_dd_dollar = 0.0
    max_dd_pct = 0.0
    
    buy_positions = []
    sell_positions = []
    trades = []
    
    # 0.10 lot on XAUUSD: 1 point move ($1.00 in Gold price) = $10.00 USD PnL
    point_value = lot_size * 100.0
    
    for i in range(len(df_input)-1):
        r = df_input.iloc[i]
        d = r['delta_pct']
        curr_p, high_p, low_p = r['close'], r['high'], r['low']
        buy_ticks = r['buy_ticks']
        sell_ticks = r['sell_ticks']
        
        # --- 1. EXIT CHECK BUY BASKET ---
        if len(buy_positions) > 0:
            total_lots = sum(p['lot'] for p in buy_positions)
            weighted_entry = sum(p['entry_p'] * p['lot'] for p in buy_positions) / total_lots
            floating_pts = curr_p - weighted_entry
            max_reach_pts = high_p - weighted_entry
            
            should_exit = False
            exit_p = curr_p
            exit_reason = ""
            
            if mode == "baseline":
                if d < 2.0:
                    should_exit = True
                    exit_reason = "EXHAUSTION (<2%)"
            elif mode == "v1_basket":
                if d < 2.0:
                    should_exit = True
                    exit_reason = "EXHAUSTION (<2%)"
            elif mode == "v2_basket":
                # A. Trailing profit lock
                if max_reach_pts >= 15.0 and floating_pts < 10.0:
                    should_exit = True
                    exit_p = weighted_entry + 10.0
                    exit_reason = "TRAIL_LOCK_10PTS"
                elif max_reach_pts >= 10.0 and floating_pts < 5.0:
                    should_exit = True
                    exit_p = weighted_entry + 5.0
                    exit_reason = "TRAIL_LOCK_5PTS"
                # B. Hard SL
                elif low_p <= weighted_entry - sl_pts:
                    should_exit = True
                    exit_p = weighted_entry - sl_pts
                    exit_reason = "HARD_SL"
                # C. Reversal: TICK BUY < TICK SELL
                elif buy_ticks < sell_ticks:
                    should_exit = True
                    exit_p = curr_p
                    exit_reason = "REVERSAL (BUY < SELL)"
                    
            if should_exit:
                total_pnl = sum((exit_p - p['entry_p']) * (p['lot'] * 100.0) for p in buy_positions)
                balance += total_pnl
                if balance > peak: peak = balance
                cur_dd_d = peak - balance
                cur_dd_p = (cur_dd_d / peak * 100.0) if peak > 0 else 0.0
                if cur_dd_d > max_dd_dollar: max_dd_dollar = cur_dd_d
                if cur_dd_p > max_dd_pct: max_dd_pct = cur_dd_p
                
                trades.append({
                    'type': 'BUY_BASKET',
                    'layers': len(buy_positions),
                    'entry_t': buy_positions[0]['entry_t'],
                    'exit_t': r.name,
                    'avg_entry': weighted_entry,
                    'exit_p': exit_p,
                    'pnl': total_pnl,
                    'won': total_pnl > 0,
                    'balance': balance,
                    'reason': exit_reason
                })
                buy_positions = []
                
        # --- 2. EXIT CHECK SELL ---
        if len(sell_positions) > 0:
            entry_p = sell_positions[0]['entry_p']
            should_exit_sell = False
            exit_p = curr_p
            exit_reason = ""
            
            if mode in ["baseline", "v1_basket"]:
                if d > -2.0:
                    should_exit_sell = True
                    exit_reason = "SELL_EXHAUSTION"
            elif mode == "v2_basket":
                max_reach = entry_p - low_p
                floating = entry_p - curr_p
                if max_reach >= 15.0 and floating < 10.0:
                    should_exit_sell = True
                    exit_p = entry_p - 10.0
                    exit_reason = "TRAIL_LOCK_10PTS"
                elif max_reach >= 10.0 and floating < 5.0:
                    should_exit_sell = True
                    exit_p = entry_p - 5.0
                    exit_reason = "TRAIL_LOCK_5PTS"
                elif high_p >= entry_p + sl_pts:
                    should_exit_sell = True
                    exit_p = entry_p + sl_pts
                    exit_reason = "HARD_SL"
                elif sell_ticks < buy_ticks:
                    should_exit_sell = True
                    exit_p = curr_p
                    exit_reason = "REVERSAL (SELL < BUY)"
                    
            if should_exit_sell:
                pnl = (entry_p - exit_p) * (sell_positions[0]['lot'] * 100.0)
                balance += pnl
                if balance > peak: peak = balance
                cur_dd_d = peak - balance
                cur_dd_p = (cur_dd_d / peak * 100.0) if peak > 0 else 0.0
                if cur_dd_d > max_dd_dollar: max_dd_dollar = cur_dd_d
                if cur_dd_p > max_dd_pct: max_dd_pct = cur_dd_p
                
                trades.append({
                    'type': 'SELL',
                    'layers': 1,
                    'entry_t': sell_positions[0]['entry_t'],
                    'exit_t': r.name,
                    'avg_entry': entry_p,
                    'exit_p': exit_p,
                    'pnl': pnl,
                    'won': pnl > 0,
                    'balance': balance,
                    'reason': exit_reason
                })
                sell_positions = []

        # --- 3. ENTRY & AVERAGING ---
        if len(buy_positions) == 0 and len(sell_positions) == 0:
            if 5.0 <= d <= 10.0:
                buy_positions.append({'entry_p': curr_p, 'lot': lot_size, 'entry_t': r.name})
            elif -10.0 <= d <= -5.0:
                sell_positions.append({'entry_p': curr_p, 'lot': lot_size, 'entry_t': r.name})
        elif len(buy_positions) > 0 and mode in ["v1_basket", "v2_basket"] and len(buy_positions) < max_layers:
            last_p = buy_positions[-1]['entry_p']
            drop_dist = last_p - curr_p
            if (curr_p < last_p) and (drop_dist >= min_dist) and (drop_dist <= 6.0) and (buy_ticks > sell_ticks):
                buy_positions.append({'entry_p': curr_p, 'lot': lot_size, 'entry_t': r.name})

    tdf = pd.DataFrame(trades)
    if len(tdf) == 0: return None
    
    wins = int((tdf['won'] == True).sum())
    total = len(tdf)
    losses = total - wins
    wr = (wins / total * 100.0) if total > 0 else 0.0
    net_pnl = balance - initial_capital
    profit_pct = (net_pnl / initial_capital * 100.0)
    g_profit = tdf[tdf['pnl'] > 0]['pnl'].sum() if wins > 0 else 0.0
    g_loss = abs(tdf[tdf['pnl'] < 0]['pnl'].sum()) if losses > 0 else 0.0
    pf = (g_profit / g_loss) if g_loss > 0 else 99.0
    
    avg_win = tdf[tdf['pnl'] > 0]['pnl'].mean() if wins > 0 else 0.0
    avg_loss = tdf[tdf['pnl'] < 0]['pnl'].mean() if losses > 0 else 0.0
    max_win = tdf['pnl'].max()
    max_loss = tdf['pnl'].min()
    
    return {
        'tdf': tdf,
        'mode': mode,
        'total_trades': total,
        'wins': wins,
        'losses': losses,
        'winrate': wr,
        'final_balance': balance,
        'net_pnl': net_pnl,
        'profit_pct': profit_pct,
        'max_dd_pct': max_dd_pct,
        'max_dd_dollar': max_dd_dollar,
        'profit_factor': pf,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_win': max_win,
        'max_loss': max_loss
    }

print("="*95)
print("HASIL BACKTEST 1 BULAN KEBELAKANG — XAUUSD (GOLD)")
print("Modal: $10,000.00 USD • Lot: Fix 0.10 Lot ($10/Poin) • Data Real Tick M30 MT5")
print("Periode: 1 Bulan Penuh (~10.8 Juta Ticks • 1,007 Bar M30)")
print("="*95)

r_base = backtest_engine(m30, mode="baseline", lot_size=0.10)
r_v1 = backtest_engine(m30, mode="v1_basket", lot_size=0.10, max_layers=2)
r_v2 = backtest_engine(m30, mode="v2_basket", lot_size=0.10, max_layers=2)

print("\n1. STRATEGI BASELINE (SINGLE ENTRY • TANPA AVERAGING • EXIT DELTA < 2%):")
print(f"Total Trade    : {r_base['total_trades']}")
print(f"Win / Loss     : {r_base['wins']} Win / {r_base['losses']} Loss")
print(f"Winrate        : {r_base['winrate']:.2f}%")
print(f"Net Profit     : ${r_base['net_pnl']:+,.2f} ({r_base['profit_pct']:+.2f}%)")
print(f"Saldo Akhir    : ${r_base['final_balance']:,.2f}")
print(f"Max Drawdown   : {r_base['max_dd_pct']:.2f}% (${r_base['max_dd_dollar']:,.2f})")
print(f"Profit Factor  : {r_base['profit_factor']:.2f}")

print("\n2. STRATEGI BUY BASKET PROTOCOL v1.0 (AVERAGING 2 LAYER • EXIT DELTA < 2%):")
print(f"Total Trade    : {r_v1['total_trades']}")
print(f"Win / Loss     : {r_v1['wins']} Win / {r_v1['losses']} Loss")
print(f"Winrate        : {r_v1['winrate']:.2f}%")
print(f"Net Profit     : ${r_v1['net_pnl']:+,.2f} ({r_v1['profit_pct']:+.2f}%)")
print(f"Saldo Akhir    : ${r_v1['final_balance']:,.2f}")
print(f"Max Drawdown   : {r_v1['max_dd_pct']:.2f}% (${r_v1['max_dd_dollar']:,.2f})")
print(f"Profit Factor  : {r_v1['profit_factor']:.2f}")

print("\n3. STRATEGI BUY BASKET PROTOCOL v2.0 (TERBARU • EXIT TICK BUY < TICK SELL • TRAILING LOCK):")
print(f"Total Trade    : {r_v2['total_trades']}")
print(f"Win / Loss     : {r_v2['wins']} Win / {r_v2['losses']} Loss")
print(f"Winrate        : {r_v2['winrate']:.2f}%")
print(f"Net Profit     : ${r_v2['net_pnl']:+,.2f} ({r_v2['profit_pct']:+.2f}%)")
print(f"Saldo Akhir    : ${r_v2['final_balance']:,.2f}")
print(f"Max Drawdown   : {r_v2['max_dd_pct']:.2f}% (${r_v2['max_dd_dollar']:,.2f})")
print(f"Profit Factor  : {r_v2['profit_factor']:.2f}")
print(f"Rata-rata Win  : +${r_v2['avg_win']:.2f}")
print(f"Rata-rata Loss : -${abs(r_v2['avg_loss']):.2f}")
print(f"Win Terbesar   : +${r_v2['max_win']:.2f}")
print(f"Loss Terbesar  : -${abs(r_v2['max_loss']):.2f}")

# Simpan CSV hasil trade
r_v2['tdf'].to_csv('backend/scripts/1month_01lot_v2_trades.csv', index=False)
print("\nDetail seluruh transaksi tersimpan di: backend/scripts/1month_01lot_v2_trades.csv")
