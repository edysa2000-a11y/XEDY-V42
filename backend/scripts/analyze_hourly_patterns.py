import pandas as pd

df = pd.read_csv('backend/scripts/xauusd_h1_week.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df['hour'] = df['datetime'].dt.hour
df['ema8'] = df['close'].ewm(span=8).mean()
df['ema21'] = df['close'].ewm(span=21).mean()
df['ema55'] = df['close'].ewm(span=55).mean()
df['atr'] = (df['high'] - df['low']).rolling(14).mean()

tp_pts = 10
sl_pts = 20

trades = []
for i in range(55, len(df)):
    curr = df.iloc[i]
    prev = df.iloc[i-1]
    
    bull_score = int(prev['ema8'] > prev['ema21']) + int(prev['ema21'] > prev['ema55']) + int(prev['close'] > prev['open']) + int(prev['close'] > prev['ema8'])
    bear_score = 4 - bull_score
    
    action = 'BUY' if bull_score >= 3 else ('SELL' if bear_score >= 3 else None)
    if not action: continue
    
    op = curr['open']
    won, lost = False, False
    for j in range(i, min(i+6, len(df))):
        b = df.iloc[j]
        if action == 'BUY':
            if b['low'] <= op - sl_pts: lost = True; break
            elif b['high'] >= op + tp_pts: won = True; break
        else:
            if b['high'] >= op + sl_pts: lost = True; break
            elif b['low'] <= op - tp_pts: won = True; break
    trades.append({'time': curr['datetime'], 'hour': curr['hour'], 'action': action, 'won': won, 'lost': lost})

tdf = pd.DataFrame(trades)
print("WINRATE BY HOUR (UTC):")
for h in sorted(tdf['hour'].unique()):
    sub = tdf[tdf['hour'] == h]
    w_sum = sub['won'].sum()
    wr = (w_sum / len(sub)) * 100
    print(f"Hour {h:02d} (WIB {(h+7)%24:02d}): total={len(sub)}, wins={w_sum}, winrate={wr:.1f}%")
