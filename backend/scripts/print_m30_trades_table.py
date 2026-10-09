import pandas as pd

df = pd.read_csv('backend/scripts/m30_tick_mode_all_trades.csv')
print("="*120)
print("LOG LENGKAP HASIL TRADE 1 MINGGU — TICK MODE XAUUSD (1.00 LOT)")
print("="*120)

for idx, r in df.iterrows():
    wib_entry = pd.to_datetime(r['entry_time']) + pd.Timedelta(hours=7)
    wib_exit = pd.to_datetime(r['exit_time']) + pd.Timedelta(hours=7)
    res_badge = "WIN " if r['result'] == "WIN" else "LOSS"
    pts = r['points']
    pnl = r['pnl_usd']
    cum = r['cum_pnl']
    print(f"{idx+1:2d}. {wib_entry.strftime('%d/%m %H:%M')} -> {wib_exit.strftime('%H:%M')} WIB | {r['type']:4s} @ {r['op']:7.2f} -> {r['exit_p']:7.2f} | Poin: {pts:+5.2f} | {r['reason']:22s} | {res_badge} | PnL: ${pnl:+8.2f} | Cum: ${cum:+9.2f}")

print("="*120)
wins = (df['result'] == 'WIN').sum()
losses = (df['result'] == 'LOSS').sum()
tot = len(df)
wr = (wins / tot) * 100
net = df['pnl_usd'].sum()
print(f"RINGKASAN: Total {tot} Trade | Wins: {wins} | Losses: {losses} | Winrate: {wr:.1f}% | Total Net PnL (1.00 Lot): ${net:,.2f}")
print("="*120)
