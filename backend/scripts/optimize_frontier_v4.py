import pandas as pd
import numpy as np

# Load 1-month M30 data
m30 = pd.read_csv('data/ticks/xauusd_M30_1month.csv').set_index('datetime')

# Compute ATR-14 on M30
high_low = m30['high'] - m30['low']
high_close = (m30['high'] - m30['close'].shift()).abs()
low_close = (m30['low'] - m30['close'].shift()).abs()
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
m30['atr'] = tr.rolling(14).mean().bfill()

# Compute Delta Acceleration (Delta change from previous bar)
m30['delta_accel'] = m30['delta_pct'] - m30['delta_pct'].shift(1).fillna(0)

def simulate_frontier_v4(df_input,
                         use_partial_tp=True, partial_tp_pts=5.0, partial_ratio=0.5,
                         use_adaptive_atr=True, atr_dist_mult=0.25, atr_trail_mult=0.50,
                         use_accel_filter=True, min_accel=0.5,
                         base_lot_l1=0.08, base_lot_l2=0.12,
                         hard_sl_pts=15.0):
    
    balance = 10000.0
    peak = 10000.0
    max_dd_dollar = 0.0
    max_dd_pct = 0.0
    
    # Each pos: {'entry_p': float, 'lot': float, 'entry_t': str, 'partial_taken': bool}
    buy_positions = []
    sell_positions = []
    trades = []
    
    for i in range(len(df_input)-1):
        r = df_input.iloc[i]
        d = r['delta_pct']
        curr_p, high_p, low_p = r['close'], r['high'], r['low']
        buy_ticks = r['buy_ticks']
        sell_ticks = r['sell_ticks']
        atr_val = r['atr']
        accel_val = r['delta_accel']
        
        # Determine dynamic parameters from ATR if enabled
        if use_adaptive_atr:
            trail_trig = max(5.0, atr_val * atr_trail_mult)
            trail_step = max(2.0, trail_trig * 0.40)
            min_dist = max(2.0, min(5.0, atr_val * atr_dist_mult))
        else:
            trail_trig = 6.0
            trail_step = 2.5
            min_dist = 2.5
            
        # 1. EXIT & PARTIAL MANAGEMENT BUY BASKET
        if len(buy_positions) > 0:
            total_lots = sum(p['lot'] for p in buy_positions)
            weighted_entry = sum(p['entry_p'] * p['lot'] for p in buy_positions) / total_lots
            max_reach_pts = high_p - weighted_entry
            floating_pts = curr_p - weighted_entry
            
            # Step A: Check Partial Take Profit (Scale-Out)
            if use_partial_tp and max_reach_pts >= partial_tp_pts:
                for pos in buy_positions:
                    if not pos.get('partial_taken', False):
                        close_lot = pos['lot'] * partial_ratio
                        realized_pnl = partial_tp_pts * (close_lot * 100.0)
                        balance += realized_pnl
                        if balance > peak: peak = balance
                        pos['lot'] -= close_lot
                        pos['partial_taken'] = True
                        trades.append({'pnl': realized_pnl, 'won': True, 'reason': 'PARTIAL_TP (+5pts)'})
                        
            # Refresh total lots after partial
            total_lots = sum(p['lot'] for p in buy_positions)
            if total_lots <= 0.001:
                buy_positions = []
            else:
                should_exit = False
                exit_p = curr_p
                exit_reason = ""
                
                # Step B: Dynamic Volatility Trailing Stop
                if max_reach_pts >= trail_trig:
                    locked_level = weighted_entry + (max_reach_pts - trail_step)
                    if curr_p <= locked_level:
                        should_exit = True
                        exit_p = max(curr_p, locked_level)
                        exit_reason = "DYNAMIC_TRAILING"
                        
                # Step C: Hard SL
                if not should_exit and (low_p <= weighted_entry - hard_sl_pts):
                    should_exit = True
                    exit_p = weighted_entry - hard_sl_pts
                    exit_reason = "HARD_SL"
                    
                # Step D: Reversal Exit (TICK BUY < TICK SELL)
                elif not should_exit and (buy_ticks < sell_ticks):
                    should_exit = True
                    exit_p = curr_p
                    exit_reason = "REVERSAL"
                    
                if should_exit:
                    total_pnl = sum((exit_p - p['entry_p']) * (p['lot'] * 100.0) for p in buy_positions)
                    balance += total_pnl
                    if balance > peak: peak = balance
                    cur_dd_d = peak - balance
                    cur_dd_p = (cur_dd_d / peak * 100.0) if peak > 0 else 0.0
                    if cur_dd_d > max_dd_dollar: max_dd_dollar = cur_dd_d
                    if cur_dd_p > max_dd_pct: max_dd_pct = cur_dd_p
                    
                    trades.append({'pnl': total_pnl, 'won': total_pnl > 0, 'reason': exit_reason})
                    buy_positions = []

        # 2. EXIT & MANAGEMENT SELL
        if len(sell_positions) > 0:
            entry_p = sell_positions[0]['entry_p']
            lot_s = sell_positions[0]['lot']
            max_reach = entry_p - low_p
            floating = entry_p - curr_p
            
            # Partial TP for Sell
            if use_partial_tp and max_reach >= partial_tp_pts and not sell_positions[0].get('partial_taken', False):
                close_lot = lot_s * partial_ratio
                pnl = partial_tp_pts * (close_lot * 100.0)
                balance += pnl
                if balance > peak: peak = balance
                sell_positions[0]['lot'] -= close_lot
                sell_positions[0]['partial_taken'] = True
                trades.append({'pnl': pnl, 'won': True, 'reason': 'PARTIAL_TP (+5pts)'})
                lot_s = sell_positions[0]['lot']
                
            if lot_s <= 0.001:
                sell_positions = []
            else:
                should_exit_sell = False
                exit_p = curr_p
                if max_reach >= trail_trig and floating <= (max_reach - trail_step):
                    should_exit_sell = True
                    exit_p = min(curr_p, entry_p - (max_reach - trail_step))
                elif high_p >= entry_p + hard_sl_pts:
                    should_exit_sell = True
                    exit_p = entry_p + hard_sl_pts
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
                    trades.append({'pnl': pnl, 'won': pnl > 0, 'reason': 'SELL_EXIT'})
                    sell_positions = []

        # 3. ENTRY & AVERAGING WITH DELTA ACCELERATION FILTER
        if len(buy_positions) == 0 and len(sell_positions) == 0:
            # Entry L1: 5.0 <= d <= 10.0
            accel_ok = (not use_accel_filter) or (accel_val >= min_accel)
            if (5.0 <= d <= 10.0) and accel_ok:
                buy_positions.append({'entry_p': curr_p, 'lot': base_lot_l1, 'entry_t': r.name, 'partial_taken': False})
            elif (-10.0 <= d <= -5.0) and ((not use_accel_filter) or (accel_val <= -min_accel)):
                sell_positions.append({'entry_p': curr_p, 'lot': base_lot_l1, 'entry_t': r.name, 'partial_taken': False})
        elif len(buy_positions) == 1:
            last_p = buy_positions[-1]['entry_p']
            drop_dist = last_p - curr_p
            if (curr_p < last_p) and (min_dist <= drop_dist <= 6.0) and (buy_ticks > sell_ticks) and (d >= 1.0):
                buy_positions.append({'entry_p': curr_p, 'lot': base_lot_l2, 'entry_t': r.name, 'partial_taken': False})

    tdf = pd.DataFrame(trades)
    if len(tdf) == 0: return None
    wins = int((tdf['won'] == True).sum())
    total = len(tdf)
    wr = (wins / total * 100.0) if total > 0 else 0.0
    net_pnl = balance - 10000.0
    roi = net_pnl / 10000.0 * 100.0
    g_p = tdf[tdf['pnl'] > 0]['pnl'].sum() if wins > 0 else 0.0
    g_l = abs(tdf[tdf['pnl'] < 0]['pnl'].sum()) if (total - wins) > 0 else 0.0
    pf = (g_p / g_l) if g_l > 0 else 99.0
    
    return {
        'trades': total, 'wr': wr, 'net_pnl': net_pnl, 'roi': roi, 'max_dd_pct': max_dd_pct, 'max_dd_dollar': max_dd_dollar, 'pf': pf
    }

print("Running Frontier v4.0 Quantitative Experiments...")
results = []

# 1. Benchmark v3.0 (from previous step)
r_v3 = simulate_frontier_v4(m30, use_partial_tp=False, use_adaptive_atr=False, use_accel_filter=False, base_lot_l1=0.08, base_lot_l2=0.12)
r_v3['model'] = "v3.0 Benchmark (0.08+0.12)"
results.append(r_v3)

# 2. Experiment 1: Scale-Out Partial TP (Tutup 50% di +5 pts, sisa 50% runner)
r_exp1 = simulate_frontier_v4(m30, use_partial_tp=True, partial_tp_pts=5.0, partial_ratio=0.5, use_adaptive_atr=False, use_accel_filter=False, base_lot_l1=0.08, base_lot_l2=0.12)
r_exp1['model'] = "v4.1 Scale-Out Partial TP (50% @ +5pts)"
results.append(r_exp1)

# 3. Experiment 2: Adaptive ATR Volatility Scaling
r_exp2 = simulate_frontier_v4(m30, use_partial_tp=False, use_adaptive_atr=True, atr_dist_mult=0.25, atr_trail_mult=0.50, use_accel_filter=False, base_lot_l1=0.08, base_lot_l2=0.12)
r_exp2['model'] = "v4.2 Adaptive ATR Volatility Scaling"
results.append(r_exp2)

# 4. Experiment 3: Delta Acceleration / Velocity Filter
r_exp3 = simulate_frontier_v4(m30, use_partial_tp=False, use_adaptive_atr=False, use_accel_filter=True, min_accel=1.0, base_lot_l1=0.08, base_lot_l2=0.12)
r_exp3['model'] = "v4.3 Delta Velocity Acceleration (+1% jump)"
results.append(r_exp3)

# 5. Experiment 4: Hybrid Institutional (Scale-Out + Adaptive ATR)
r_exp4 = simulate_frontier_v4(m30, use_partial_tp=True, partial_tp_pts=5.0, partial_ratio=0.5, use_adaptive_atr=True, atr_dist_mult=0.25, atr_trail_mult=0.50, use_accel_filter=False, base_lot_l1=0.08, base_lot_l2=0.12)
r_exp4['model'] = "v4.4 Hybrid (Scale-Out + Adaptive ATR)"
results.append(r_exp4)

# 6. Experiment 5: Ultra-Sharpe Ratio Master Engine (Scale-Out + Conservative Sizing 0.06+0.14)
r_exp5 = simulate_frontier_v4(m30, use_partial_tp=True, partial_tp_pts=5.0, partial_ratio=0.5, use_adaptive_atr=False, use_accel_filter=False, base_lot_l1=0.06, base_lot_l2=0.14)
r_exp5['model'] = "v4.5 Master Ultra-Sharpe (Scale-Out + 0.06/0.14)"
results.append(r_exp5)

df_all = pd.DataFrame(results)
cols = ['model', 'trades', 'wr', 'roi', 'net_pnl', 'max_dd_pct', 'max_dd_dollar', 'pf']
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
print("\n" + "="*115)
print("HASIL EXPERIMEN FRONTIER v4.0 (1 BULAN REAL TICK MT5 XAUUSD • MODAL $10,000)")
print("="*115)
print(df_all[cols].to_string(index=False))
