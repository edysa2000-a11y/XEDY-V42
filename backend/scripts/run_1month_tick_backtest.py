import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import os

print("="*85)
print("PENGAMBILAN DATA 1 BULAN TICK XAUUSD DARI METATRADER 5...")
print("="*85)

if not mt5.initialize():
    print("MT5 initialization failed")
    exit(1)

utc_to = datetime.now(timezone.utc)
utc_from = utc_to - timedelta(days=31)

print(f"Range: {utc_from} s/d {utc_to}")
ticks = mt5.copy_ticks_range('XAUUSD', utc_from, utc_to, mt5.COPY_TICKS_ALL)
mt5.shutdown()

print(f"Total Ticks Diperoleh: {len(ticks):,d} ticks.")

# Classify Ticks using Lee-Ready Tick Rule
df = pd.DataFrame(ticks)
df['mid'] = (df['bid'] + df['ask']) / 2.0
df['mid_diff'] = df['mid'].diff()

tick_dir = np.where(df['mid_diff'] > 0, 1, np.where(df['mid_diff'] < 0, -1, 0))
s = pd.Series(tick_dir).replace(0, np.nan).ffill().fillna(1).astype(int)
df['is_buy'] = (s == 1).astype(int)
df['is_sell'] = (s == -1).astype(int)
df['datetime'] = pd.to_datetime(df['time'], unit='s')
df.set_index('datetime', inplace=True)

print("Resampling ke Timeframe M15, M30, H1...")

def resample_tf(df, rule):
    ohlc = df['mid'].resample(rule).ohlc()
    tot = df['mid'].resample(rule).count()
    b = df['is_buy'].resample(rule).sum()
    s = df['is_sell'].resample(rule).sum()
    res = pd.DataFrame({
        'open': ohlc['open'],
        'high': ohlc['high'],
        'low': ohlc['low'],
        'close': ohlc['close'],
        'total_ticks': tot,
        'buy_ticks': b,
        'sell_ticks': s
    }).dropna()
    res['delta_ticks'] = res['buy_ticks'] - res['sell_ticks']
    res['delta_pct'] = np.where(res['total_ticks'] > 0, (res['delta_ticks'] / res['total_ticks']) * 100.0, 0.0)
    return res

m15 = resample_tf(df, '15min')
m30 = resample_tf(df, '30min')
h1 = resample_tf(df, '1h')

m15.to_csv('data/ticks/xauusd_M15_1month.csv')
m30.to_csv('data/ticks/xauusd_M30_1month.csv')
h1.to_csv('data/ticks/xauusd_H1_1month.csv')

print(f"M15: {len(m15)} bars | M30: {len(m30)} bars | H1: {len(h1)} bars (Saved to data/ticks)")

# Align MTF context for M30 execution
m30_df = m30.copy()
m30_df['h1_delta'] = h1['delta_pct'].reindex(m30_df.index, method='ffill')
m30_df.dropna(inplace=True)

# -------------------------------------------------------------------------
# BACKTEST FUNCTION WITH BALANCE, % PROFIT & DRAWDOWN
# -------------------------------------------------------------------------
def run_backtest(df_input, use_htf=True, tp_pts=8.0, sl_pts=20.0, use_exhaustion=True, initial_capital=10000.0, lot_size=1.00):
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
                    exited, exit_p, reason = True, entry_p + tp_pts, 'HIT TP'
                elif sl_pts > 0 and low_p <= entry_p - sl_pts:
                    exited, exit_p, reason = True, entry_p - sl_pts, 'HIT SL'
                elif use_exhaustion and d < 2.0:
                    exited, exit_p, reason = True, curr_p, 'TICK EXHAUSTION (<2%)'
            else: # SELL
                if tp_pts > 0 and low_p <= entry_p - tp_pts:
                    exited, exit_p, reason = True, entry_p - tp_pts, 'HIT TP'
                elif sl_pts > 0 and high_p >= entry_p + sl_pts:
                    exited, exit_p, reason = True, entry_p + sl_pts, 'HIT SL'
                elif use_exhaustion and d > -2.0:
                    exited, exit_p, reason = True, curr_p, 'TICK EXHAUSTION (<2%)'
                    
            if exited:
                points = (exit_p - entry_p) if pos_type == 'BUY' else (entry_p - exit_p)
                pnl = points * lot_size * 100.0 # $100 per 1.00 lot
                balance += pnl
                if balance > peak_balance:
                    peak_balance = balance
                
                cur_dd_dollar = peak_balance - balance
                cur_dd_pct = (cur_dd_dollar / peak_balance) * 100.0
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
                    'reason': reason,
                    'points': round(points, 2),
                    'pnl_usd': round(pnl, 2),
                    'balance': round(balance, 2),
                    'dd_pct': round(cur_dd_pct, 2),
                    'won': pnl > 0
                })
                in_pos, pos_type = False, None
                
        if not in_pos:
            buy_cond = (5.0 <= d <= 10.0)
            sell_cond = (-10.0 <= d <= -5.0)
            
            if use_htf:
                buy_cond = buy_cond and (dh1 > 0)
                sell_cond = sell_cond and (dh1 < 0)
                
            if buy_cond:
                in_pos, pos_type, entry_p, entry_t = True, 'BUY', curr_p, r.name
            elif sell_cond:
                in_pos, pos_type, entry_p, entry_t = True, 'SELL', curr_p, r.name
                
    tdf = pd.DataFrame(trades)
    wins = (tdf['won'] == True).sum()
    total_trades = len(tdf)
    winrate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    net_pnl = balance - initial_capital
    profit_pct = (net_pnl / initial_capital) * 100.0
    gross_profit = tdf[tdf['pnl_usd'] > 0]['pnl_usd'].sum()
    gross_loss = abs(tdf[tdf['pnl_usd'] < 0]['pnl_usd'].sum())
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 99.0
    
    return {
        'trades_df': tdf,
        'initial_capital': initial_capital,
        'final_balance': balance,
        'net_pnl': net_pnl,
        'profit_pct': profit_pct,
        'max_dd_dollar': max_dd_dollar,
        'max_dd_pct': max_dd_pct,
        'total_trades': total_trades,
        'wins': wins,
        'losses': total_trades - wins,
        'winrate': winrate,
        'profit_factor': profit_factor
    }

print("\nMenjalankan Simulasi 1 Bulan...")
res_m30 = run_backtest(m30_df, use_htf=True, tp_pts=8.0, sl_pts=20.0, use_exhaustion=True, initial_capital=10000.0, lot_size=1.00)
res_m30_base = run_backtest(m30_df, use_htf=False, tp_pts=0.0, sl_pts=0.0, use_exhaustion=True, initial_capital=10000.0, lot_size=1.00)

print("="*85)
print("HASIL BACKTEST 1 BULAN — MODAL $10,000 • FIX 1.00 LOT")
print("="*85)

print("\n1. ENHANCED MTF TICK MODE ENGINE (M30 + H1 CONFLUENCE + TP 8 + SL 20):")
print(f"• Modal Awal     : ${res_m30['initial_capital']:,.2f}")
print(f"• Saldo Akhir    : ${res_m30['final_balance']:,.2f}")
print(f"• Profit Bersih  : ${res_m30['net_pnl']:,.2f}")
print(f"• % PROFIT (ROI) : {res_m30['profit_pct']:+.2f}%")
print(f"• MAX DRAWDOWN   : {res_m30['max_dd_pct']:.2f}% (${res_m30['max_dd_dollar']:,.2f})")
print(f"• WINRATE        : {res_m30['winrate']:.2f}% ({res_m30['wins']} Menang / {res_m30['losses']} Kalah)")
print(f"• Total Trade    : {res_m30['total_trades']} Transaksi")
print(f"• Profit Factor  : {res_m30['profit_factor']:.2f}")

print("\n2. BASELINE TICK MODE (RULE MURNI USER: 5-10%, CLOSE < 2%, TANPA SL/TP):")
print(f"• Modal Awal     : ${res_m30_base['initial_capital']:,.2f}")
print(f"• Saldo Akhir    : ${res_m30_base['final_balance']:,.2f}")
print(f"• Profit Bersih  : ${res_m30_base['net_pnl']:,.2f}")
print(f"• % PROFIT (ROI) : {res_m30_base['profit_pct']:+.2f}%")
print(f"• MAX DRAWDOWN   : {res_m30_base['max_dd_pct']:.2f}% (${res_m30_base['max_dd_dollar']:,.2f})")
print(f"• WINRATE        : {res_m30_base['winrate']:.2f}% ({res_m30_base['wins']} Menang / {res_m30_base['losses']} Kalah)")
print(f"• Total Trade    : {res_m30_base['total_trades']} Transaksi")
print(f"• Profit Factor  : {res_m30_base['profit_factor']:.2f}")

# Save detailed trades
res_m30['trades_df'].to_csv('backend/scripts/tick_mode_1month_m30_trades.csv', index=False)
