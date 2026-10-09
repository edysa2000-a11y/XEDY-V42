import pandas as pd

m30 = pd.read_csv('data/ticks/xauusd_M30_1month.csv').set_index('datetime')
h1 = pd.read_csv('data/ticks/xauusd_H1_1month.csv').set_index('datetime')
df_m30 = m30.copy()
df_m30['h1_delta'] = h1['delta_pct'].reindex(df_m30.index, method='ffill')
df_m30.dropna(inplace=True)

balance = 10000.0
peak = 10000.0
trades = []
in_pos, pos_type, entry_p, entry_t = False, None, 0.0, None
max_dd_dollar = 0.0
max_dd_pct = 0.0

for i in range(len(df_m30)-1):
    r = df_m30.iloc[i]
    d = r['delta_pct']
    curr_p = r['close']
    if in_pos:
        exited = False
        if pos_type == 'BUY' and d < 2.0: exited = True
        elif pos_type == 'SELL' and d > -2.0: exited = True
        if exited:
            pts = (curr_p - entry_p) if pos_type == 'BUY' else (entry_p - curr_p)
            pnl = pts * 100.0
            balance += pnl
            if balance > peak:
                peak = balance
            cur_dd = peak - balance
            cur_dd_pct = cur_dd / peak * 100.0
            if cur_dd > max_dd_dollar: max_dd_dollar = cur_dd
            if cur_dd_pct > max_dd_pct: max_dd_pct = cur_dd_pct
            
            trades.append({
                'entry_t': str(entry_t), 'type': pos_type, 'op': entry_p,
                'exit_p': curr_p, 'pts': pts, 'pnl': pnl,
                'balance': balance, 'dd_pct': cur_dd_pct, 'won': pnl > 0
            })
            in_pos, pos_type = False, None
    if not in_pos:
        if 5.0 <= d <= 10.0: in_pos, pos_type, entry_p, entry_t = True, 'BUY', curr_p, r.name
        elif -10.0 <= d <= -5.0: in_pos, pos_type, entry_p, entry_t = True, 'SELL', curr_p, r.name

b_df = pd.DataFrame(trades)
b_df['dt'] = pd.to_datetime(b_df['entry_t'])
b_df['week'] = b_df['dt'].dt.isocalendar().week

print("="*90)
print("AUDIT BACKTEST 1 BULAN TICK MODE XAUUSD (MODAL $10,000 • FIX 1.00 LOT)")
print("="*90)

week_names = {
    37: "Minggu 1 (07 - 12 Sep 2026)",
    38: "Minggu 2 (14 - 19 Sep 2026)",
    39: "Minggu 3 (21 - 26 Sep 2026)",
    40: "Minggu 4 (28 Sep - 03 Okt 2026)",
    41: "Minggu 5 (05 - 08 Okt 2026)"
}

for w in sorted(b_df['week'].unique()):
    sub = b_df[b_df['week'] == w]
    w_cnt = int(sub['won'].sum())
    wr = (w_cnt / len(sub)) * 100.0
    pnl = sub['pnl'].sum()
    end_bal = sub['balance'].iloc[-1]
    name = week_names.get(w, f"Minggu {w}")
    print(f"• {name:32s} : {len(sub):2d} Trade | Win: {w_cnt:2d} | WR: {wr:5.1f}% | PnL: ${pnl:+9.2f} | Saldo: ${end_bal:9.2f}")

tot = len(b_df)
wins = int(b_df['won'].sum())
wr_tot = (wins / tot) * 100.0
net_tot = b_df['pnl'].sum()
roi_tot = (net_tot / 10000.0) * 100.0

print("="*90)
print(f"MODAL AWAL            : $10,000.00 USD")
print(f"SALDO AKHIR           : ${balance:,.2f} USD")
print(f"PROFIT BERSIH (NET)   : ${net_tot:,.2f} USD")
print(f"PERSENTASE PROFIT     : {roi_tot:+.2f}%")
print(f"MAX DRAWDOWN (DD)     : {max_dd_pct:.2f}% (${max_dd_dollar:,.2f} USD)")
print(f"WINRATE AKURASI       : {wr_tot:.2f}% ({wins} Win / {tot-wins} Loss)")
print(f"TOTAL TRANSAKSI       : {tot} Trade")
print("="*90)
