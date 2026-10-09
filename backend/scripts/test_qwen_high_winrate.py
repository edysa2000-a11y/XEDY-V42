import pandas as pd
import numpy as np

df = pd.read_csv('backend/scripts/xauusd_h1_week.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df['hour'] = df['datetime'].dt.hour
df['ema8'] = df['close'].ewm(span=8).mean()
df['ema21'] = df['close'].ewm(span=21).mean()
df['ema55'] = df['close'].ewm(span=55).mean()
df['atr14'] = (df['high'] - df['low']).rolling(14).mean()

delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / (loss + 1e-9)
df['rsi'] = 100 - (100 / (1 + rs))

def get_session(h):
    if 0 <= h <= 6: return 'ASIA (Tokyo/Sydney)'
    elif 7 <= h <= 12: return 'LONDON (Frankfurt/London)'
    elif 13 <= h <= 21: return 'NEW YORK (Wall Street)'
    return 'OFF-SESSION'

df['session'] = df['hour'].apply(get_session)

for tp in [5, 6, 8, 10, 12]:
    for sl in [15, 20, 25, 30]:
        trades = []
        for i in range(55, len(df)-1):
            curr = df.iloc[i]
            prev = df.iloc[i-1]
            if curr['session'] == 'OFF-SESSION': continue
            
            # Smart filter
            buy_conf = (prev['ema8'] > prev['ema21']) and (prev['ema21'] > prev['ema55']) and (prev['rsi'] > 50) and (prev['rsi'] < 68) and (prev['close'] > prev['open'])
            sell_conf = (prev['ema8'] < prev['ema21']) and (prev['ema21'] < prev['ema55']) and (prev['rsi'] < 50) and (prev['rsi'] > 32) and (prev['close'] < prev['open'])
            
            if not (buy_conf or sell_conf): continue
            
            action = 'BUY' if buy_conf else 'SELL'
            op = curr['open']
            
            won = False
            lost = False
            for j in range(i, min(i+6, len(df))):
                b = df.iloc[j]
                if action == 'BUY':
                    if b['low'] <= op - sl: lost = True; break
                    elif b['high'] >= op + tp: won = True; break
                else:
                    if b['high'] >= op + sl: lost = True; break
                    elif b['low'] <= op - tp: won = True; break
            if won or lost:
                pnl = (tp if won else -sl) * 100
                trades.append({'time': curr['datetime'], 'session': curr['session'], 'action': action, 'won': won, 'pnl': pnl})
        if trades:
            tdf = pd.DataFrame(trades)
            w_cnt = int(tdf['won'].sum())
            wr = (w_cnt / len(tdf)) * 100
            pnl_tot = tdf['pnl'].sum()
            print(f"TP: {tp:2d} | SL: {sl:2d} | Trades: {len(tdf):2d} | Wins: {w_cnt:2d} | Losses: {len(tdf)-w_cnt:2d} | Winrate: {wr:5.1f}% | Net USD: ${pnl_tot:8.2f}")
