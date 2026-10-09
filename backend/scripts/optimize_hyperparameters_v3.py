import pandas as pd
import numpy as np

# Load 1-month M30 data
m30 = pd.read_csv('data/ticks/xauusd_M30_1month.csv').set_index('datetime')
h1 = pd.read_csv('data/ticks/xauusd_H1_1month.csv').set_index('datetime')
m30['h1_delta'] = h1['delta_pct'].reindex(m30.index, method='ffill')
m30['hour'] = pd.to_datetime(m30.index).hour # UTC hour

def run_grid_sim(df_input, 
                 entry_min=5.0, entry_max=10.0,
                 avg_dist_min=2.5, avg_dist_max=6.0,
                 avg_min_delta=1.0,
                 lot_l1=0.08, lot_l2=0.12,
                 trail_trigger=8.0, trail_step=4.0,
                 sl_pts=15.0,
                 h1_filter=False,
                 session_filter=False):
    
    balance = 10000.0
    peak = 10000.0
    max_dd_dollar = 0.0
    max_dd_pct = 0.0
    
    buy_positions = []
    sell_positions = []
    trades = []
    
    for i in range(len(df_input)-1):
        r = df_input.iloc[i]
        d = r['delta_pct']
        curr_p, high_p, low_p = r['close'], r['high'], r['low']
        buy_ticks = r['buy_ticks']
        sell_ticks = r['sell_ticks']
        h1_d = r.get('h1_delta', 0.0)
        u_hour = r.get('hour', 12) # UTC hour (WIB = UTC + 7)
        
        # Session filter: skip Asian early drift (22 to 02 UTC / 05 to 09 WIB)
        if session_filter and (u_hour in [21, 22, 23, 0, 1]):
            pass # still check exits, but don't open new positions
        
        # 1. EXIT CHECK BUY BASKET
        if len(buy_positions) > 0:
            total_lots = sum(p['lot'] for p in buy_positions)
            weighted_entry = sum(p['entry_p'] * p['lot'] for p in buy_positions) / total_lots
            floating_pts = curr_p - weighted_entry
            max_reach_pts = high_p - weighted_entry
            
            should_exit = False
            exit_p = curr_p
            exit_reason = ""
            
            # A. Dynamic Trailing Lock
            if max_reach_pts >= trail_trigger:
                locked_level = weighted_entry + (max_reach_pts - trail_step)
                if curr_p <= locked_level:
                    should_exit = True
                    exit_p = max(curr_p, locked_level)
                    exit_reason = "TRAIL_LOCK"
                    
            # B. Hard SL
            if not should_exit and (low_p <= weighted_entry - sl_pts):
                should_exit = True
                exit_p = weighted_entry - sl_pts
                exit_reason = "HARD_SL"
                
            # C. True Reversal Exit: TICK BUY < TICK SELL
            elif not should_exit and (buy_ticks < sell_ticks):
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
                    'pnl': total_pnl,
                    'won': total_pnl > 0,
                    'balance': balance,
                    'reason': exit_reason
                })
                buy_positions = []

        # 2. EXIT CHECK SELL
        if len(sell_positions) > 0:
            entry_p = sell_positions[0]['entry_p']
            lot_s = sell_positions[0]['lot']
            max_reach = entry_p - low_p
            floating = entry_p - curr_p
            should_exit_sell = False
            exit_p = curr_p
            
            if max_reach >= trail_trigger and floating <= (max_reach - trail_step):
                should_exit_sell = True
                exit_p = min(curr_p, entry_p - (max_reach - trail_step))
            elif high_p >= entry_p + sl_pts:
                should_exit_sell = True
                exit_p = entry_p + sl_pts
            elif sell_ticks < buy_ticks:
                should_exit_sell = True
                exit_p = curr_p
                
            if should_exit_sell:
                pnl = (entry_p - exit_p) * (lot_s * 100.0)
                balance += pnl
                if balance > peak: peak = balance
                cur_dd_d = peak - balance
                cur_dd_p = (cur_dd_d / peak * 100.0) if peak > 0 else 0.0
                if cur_dd_d > max_dd_dollar: max_dd_dollar = cur_dd_d
                if cur_dd_p > max_dd_pct: max_dd_pct = cur_dd_p
                
                trades.append({'type': 'SELL', 'layers': 1, 'pnl': pnl, 'won': pnl > 0, 'balance': balance})
                sell_positions = []

        # 3. ENTRY & AVERAGING
        can_open = True
        if session_filter and (u_hour in [21, 22, 23, 0, 1]):
            can_open = False
            
        if can_open:
            if len(buy_positions) == 0 and len(sell_positions) == 0:
                # Optional H1 confluence filter: don't buy if H1 is deeply bearish (< -5%)
                if (not h1_filter or h1_d >= -5.0) and (entry_min <= d <= entry_max):
                    buy_positions.append({'entry_p': curr_p, 'lot': lot_l1, 'entry_t': r.name})
                elif (not h1_filter or h1_d <= 5.0) and (-entry_max <= d <= -entry_min):
                    sell_positions.append({'entry_p': curr_p, 'lot': lot_l1, 'entry_t': r.name})
            elif len(buy_positions) == 1:
                last_p = buy_positions[-1]['entry_p']
                drop_dist = last_p - curr_p
                # Averaging L2 with smart weighting (lot_l2)
                if (curr_p < last_p) and (avg_dist_min <= drop_dist <= avg_dist_max) and (buy_ticks > sell_ticks) and (d >= avg_min_delta):
                    buy_positions.append({'entry_p': curr_p, 'lot': lot_l2, 'entry_t': r.name})

    tdf = pd.DataFrame(trades)
    if len(tdf) == 0: return None
    
    wins = int((tdf['won'] == True).sum())
    total = len(tdf)
    losses = total - wins
    wr = (wins / total * 100.0) if total > 0 else 0.0
    net_pnl = balance - 10000.0
    profit_pct = (net_pnl / 10000.0 * 100.0)
    g_profit = tdf[tdf['pnl'] > 0]['pnl'].sum() if wins > 0 else 0.0
    g_loss = abs(tdf[tdf['pnl'] < 0]['pnl'].sum()) if losses > 0 else 0.0
    pf = (g_profit / g_loss) if g_loss > 0 else 99.0
    
    return {
        'total_trades': total,
        'wins': wins,
        'losses': losses,
        'winrate': wr,
        'net_pnl': net_pnl,
        'profit_pct': profit_pct,
        'max_dd_pct': max_dd_pct,
        'max_dd_dollar': max_dd_dollar,
        'profit_factor': pf,
        'balance': balance
    }

# RUN GRID SEARCH
print("Menjalankan Grid Search Optimasi Tingkat Lanjut...")
grid_results = []

# Baseline v2.0 params for reference:
base_v2 = run_grid_sim(m30, entry_min=5.0, entry_max=10.0, avg_dist_min=2.0, avg_dist_max=6.0, avg_min_delta=0.0, lot_l1=0.10, lot_l2=0.10, trail_trigger=10.0, trail_step=5.0)
base_v2['label'] = "v2.0 Baseline (0.10+0.10)"
grid_results.append(base_v2)

# Test 1: Smart Sizing Asymmetric (L1=0.08, L2=0.12)
t1 = run_grid_sim(m30, entry_min=5.0, entry_max=10.0, avg_dist_min=2.5, avg_dist_max=6.0, avg_min_delta=1.0, lot_l1=0.08, lot_l2=0.12, trail_trigger=8.0, trail_step=3.5)
t1['label'] = "v3.0 Smart Sizing (0.08+0.12) + Trail 8/3.5"
grid_results.append(t1)

# Test 2: Smart Sizing (0.07 + 0.13) + Delta Min 1.0% + Dist 2.5
t2 = run_grid_sim(m30, entry_min=5.0, entry_max=10.0, avg_dist_min=2.5, avg_dist_max=6.0, avg_min_delta=1.0, lot_l1=0.07, lot_l2=0.13, trail_trigger=7.0, trail_step=3.0)
t2['label'] = "v3.1 Asymmetric (0.07+0.13) + Trail 7/3.0"
grid_results.append(t2)

# Test 3: Confluence H1 Filter + Smart Sizing
t3 = run_grid_sim(m30, entry_min=5.0, entry_max=10.0, avg_dist_min=2.5, avg_dist_max=6.0, avg_min_delta=1.0, lot_l1=0.08, lot_l2=0.12, trail_trigger=8.0, trail_step=3.5, h1_filter=True)
t3['label'] = "v3.2 H1 Confluence Filter + (0.08+0.12)"
grid_results.append(t3)

# Test 4: Session Filter (Skip Asian Rollover 04-08 WIB) + Smart Sizing
t4 = run_grid_sim(m30, entry_min=5.0, entry_max=10.0, avg_dist_min=2.5, avg_dist_max=6.0, avg_min_delta=1.0, lot_l1=0.08, lot_l2=0.12, trail_trigger=8.0, trail_step=3.5, session_filter=True)
t4['label'] = "v3.3 Session Filter + (0.08+0.12)"
grid_results.append(t4)

# Test 5: Full Institutional Quad-Filter (H1 Confluence + Session + Smart Sizing + Dynamic Trail)
t5 = run_grid_sim(m30, entry_min=5.0, entry_max=10.0, avg_dist_min=2.5, avg_dist_max=6.0, avg_min_delta=1.0, lot_l1=0.08, lot_l2=0.12, trail_trigger=8.0, trail_step=3.5, h1_filter=True, session_filter=True)
t5['label'] = "v3.4 Master Quad-Engine (All Optimized)"
grid_results.append(t5)

# Test 6: Sizing 0.10 + 0.15 (Slightly more aggressive)
t6 = run_grid_sim(m30, entry_min=5.0, entry_max=10.0, avg_dist_min=2.5, avg_dist_max=6.0, avg_min_delta=1.0, lot_l1=0.10, lot_l2=0.15, trail_trigger=8.0, trail_step=3.5, h1_filter=True, session_filter=True)
t6['label'] = "v3.5 High-Yield (0.10+0.15) Quad-Engine"
grid_results.append(t6)

df_res = pd.DataFrame(grid_results)
cols = ['label', 'total_trades', 'winrate', 'profit_pct', 'net_pnl', 'max_dd_pct', 'max_dd_dollar', 'profit_factor']
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
print("\n" + "="*105)
print("HASIL KOMPARASI OPTIMASI TINGKAT LANJUT (1 BULAN MT5 XAUUSD • MODAL $10,000)")
print("="*105)
print(df_res[cols].to_string(index=False))
