import pandas as pd

df = pd.read_csv('backend/scripts/xauusd_h1_week.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df['hour'] = df['datetime'].dt.hour
df['ema8'] = df['close'].ewm(span=8).mean()
df['ema21'] = df['close'].ewm(span=21).mean()
df['ema55'] = df['close'].ewm(span=55).mean()
df['atr'] = (df['high'] - df['low']).rolling(14).mean()

# High-confluence institutional hours identified by Qwen
# Asia Expansion: 06 UTC (13:00 WIB)
# London Session: 07, 10, 12 UTC (14:00, 17:00, 19:00 WIB)
# New York Session: 13, 14, 15, 18, 21 UTC (20:00, 21:00, 22:00, 01:00, 04:00 WIB)
qwen_high_prob_hours = [6, 7, 10, 12, 13, 14, 15, 18, 21]

tp_pts = 10
sl_pts = 20

trades = []
for i in range(55, len(df)):
    curr = df.iloc[i]
    prev = df.iloc[i-1]
    
    if curr['hour'] not in qwen_high_prob_hours:
        continue
        
    bull_score = int(prev['ema8'] > prev['ema21']) + int(prev['ema21'] > prev['ema55']) + int(prev['close'] > prev['open']) + int(prev['close'] > prev['ema8'])
    bear_score = 4 - bull_score
    
    action = 'BUY' if bull_score >= 3 else ('SELL' if bear_score >= 3 else None)
    if not action:
        continue
        
    op = curr['open']
    won, lost = False, False
    exit_p = op
    
    for j in range(i, min(i+6, len(df))):
        b = df.iloc[j]
        if action == 'BUY':
            if b['low'] <= op - sl_pts:
                lost = True
                exit_p = op - sl_pts
                break
            elif b['high'] >= op + tp_pts:
                won = True
                exit_p = op + tp_pts
                break
        else:
            if b['high'] >= op + sl_pts:
                lost = True
                exit_p = op + sl_pts
                break
            elif b['low'] <= op - tp_pts:
                won = True
                exit_p = op - tp_pts
                break
                
    pnl = (tp_pts if won else -sl_pts) * 100.0
    trades.append({
        'datetime': str(curr['datetime']),
        'hour_utc': curr['hour'],
        'hour_wib': (curr['hour'] + 7) % 24,
        'action': action,
        'op': op,
        'tp': op + tp_pts if action == 'BUY' else op - tp_pts,
        'sl': op - sl_pts if action == 'BUY' else op + sl_pts,
        'exit_price': exit_p,
        'result': 'WIN' if won else 'LOSS',
        'pnl_usd': pnl
    })

tdf = pd.DataFrame(trades)
total = len(tdf)
wins = int(tdf['result'].eq('WIN').sum())
losses = int(tdf['result'].eq('LOSS').sum())
wr = (wins / total) * 100
net_pnl = tdf['pnl_usd'].sum()

print("="*80)
print(f"QWEN INSTITUTIONAL SESSION ENGINE — RESULTS")
print(f"Total Trades: {total} | Wins: {wins} | Losses: {losses} | Winrate: {wr:.1f}%")
print(f"Net Profit (1.00 Lot = $100/point): ${net_pnl:,.2f}")
print("="*80)
print(tdf.to_string(index=False))
tdf.to_csv('backend/scripts/qwen_final_1week_report.csv', index=False)
