import pandas as pd
import numpy as np

df = pd.read_csv('backend/scripts/xauusd_h1_week.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df['hour'] = df['datetime'].dt.hour
df['ema8'] = df['close'].ewm(span=8).mean()
df['ema21'] = df['close'].ewm(span=21).mean()
df['ema55'] = df['close'].ewm(span=55).mean()
df['atr14'] = (df['high'] - df['low']).rolling(14).mean()

def get_session(h):
    if 0 <= h <= 6:
        return 'ASIA'
    elif 7 <= h <= 12:
        return 'LONDON'
    elif 13 <= h <= 21:
        return 'NEW YORK'
    return 'OFF-SESSION'

df['session'] = df['hour'].apply(get_session)

# Let's test a systematic regime-adaptive engine:
# For each hour bar i, we forecast direction for bar i:
# Factors:
# 1. Trend: ema8 > ema21 > ema55 -> Strong Bullish; ema8 < ema21 < ema55 -> Strong Bearish
# 2. Previous bar momentum: close[i-1] - open[i-1]
# 3. Session filter: Asia range vs London expansion vs NY continuation

results = []

for tp_pts in [6, 8, 10, 12, 15]:
    for sl_pts in [15, 20, 25, 30]:
        trades = []
        for i in range(55, len(df)):
            curr = df.iloc[i]
            prev = df.iloc[i-1]
            prev2 = df.iloc[i-2]
            
            if curr['session'] == 'OFF-SESSION':
                continue
                
            # Signal logic
            bullish_score = 0
            bearish_score = 0
            
            if prev['ema8'] > prev['ema21']: bullish_score += 1
            else: bearish_score += 1
            
            if prev['ema21'] > prev['ema55']: bullish_score += 1
            else: bearish_score += 1
            
            if prev['close'] > prev['open']: bullish_score += 1
            else: bearish_score += 1
            
            if prev['close'] > prev['ema8']: bullish_score += 1
            else: bearish_score += 1
            
            # Action selection
            action = None
            if bullish_score >= 3:
                action = 'BUY'
            elif bearish_score >= 3:
                action = 'SELL'
            else:
                continue # Wait
                
            op = curr['open']
            high = curr['high']
            low = curr['low']
            close = curr['close']
            
            # Check outcome in current bar or next bars
            # Let's track trade execution until hit TP or SL
            won = False
            lost = False
            pnl = 0
            
            # Evaluate across current and subsequent bars
            for j in range(i, min(i+6, len(df))): # Max hold 6 hours
                b = df.iloc[j]
                if action == 'BUY':
                    target_tp = op + tp_pts
                    target_sl = op - sl_pts
                    if b['low'] <= target_sl:
                        lost = True
                        pnl = -sl_pts * 100
                        break
                    elif b['high'] >= target_tp:
                        won = True
                        pnl = tp_pts * 100
                        break
                elif action == 'SELL':
                    target_tp = op - tp_pts
                    target_sl = op + sl_pts
                    if b['high'] >= target_sl:
                        lost = True
                        pnl = -sl_pts * 100
                        break
                    elif b['low'] <= target_tp:
                        won = True
                        pnl = tp_pts * 100
                        break
            
            if won or lost:
                trades.append({'won': won, 'pnl': pnl})
        
        if trades:
            tdf = pd.DataFrame(trades)
            winrate = (tdf['won'].sum() / len(tdf)) * 100
            total_pnl = tdf['pnl'].sum()
            results.append({
                'tp': tp_pts,
                'sl': sl_pts,
                'total_trades': len(tdf),
                'winrate': winrate,
                'pnl': total_pnl
            })

rdf = pd.DataFrame(results).sort_values(by='winrate', ascending=False)
print(rdf.head(15).to_string(index=False))
