import pandas as pd
import numpy as np

# Load real MT5 H1 data
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

print("="*80)
print("XEDY AI + QWEN QUANT ENGINE — HOURLY SESSION BACKTEST (1 WEEK)")
print("="*80)

# We want to evaluate the hourly forecasts across Asia, London, New York
# Let's test a Qwen Smart Session Filter:
# When Qwen identifies high-quality regime alignment:
# 1. Asia Session: Range Contraction & Clean Trend Extension
# 2. London Session: London Open Expansion (07:00 - 11:00 UTC)
# 3. New York Session: Wall Street Liquidity Injection (13:00 - 18:00 UTC)

def run_simulation(tp_pts, sl_pts, use_be=True, be_trigger=0.5):
    trades = []
    
    for i in range(25, len(df)-1):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        if curr['session'] == 'OFF-SESSION':
            continue
            
        # Directional scoring
        bull_score = 0
        bear_score = 0
        
        # Trend filter
        if prev['ema8'] > prev['ema21']: bull_score += 1
        else: bear_score += 1
        
        if prev['ema21'] > prev['ema55']: bull_score += 1
        else: bear_score += 1
        
        # Candle close confirmation
        if prev['close'] > prev['open']: bull_score += 1
        else: bear_score += 1
        
        if prev['close'] > prev['ema8']: bull_score += 1
        else: bear_score += 1
        
        # Session volume & momentum
        if prev['high'] - prev['low'] > 0.8 * prev['atr14']:
            if prev['close'] > prev['open']: bull_score += 1
            else: bear_score += 1
            
        action = None
        confidence = 0
        if bull_score >= 4:
            action = 'BUY'
            confidence = int((bull_score / 5) * 100)
        elif bear_score >= 4:
            action = 'SELL'
            confidence = int((bear_score / 5) * 100)
        else:
            continue # Qwen Filter: WAIT / NO ENTRY
            
        op = curr['open']
        time_str = str(curr['datetime'])
        session_str = curr['session']
        
        won = False
        lost = False
        be = False
        pnl = 0
        exit_price = op
        exit_time = time_str
        
        # Monitor trade over subsequent hours (max hold 6 hours)
        cur_sl = op - sl_pts if action == 'BUY' else op + sl_pts
        cur_tp = op + tp_pts if action == 'BUY' else op - tp_pts
        
        for j in range(i, min(i+6, len(df))):
            bar = df.iloc[j]
            exit_time = str(bar['datetime'])
            
            if action == 'BUY':
                # Check BE trigger
                if use_be and bar['high'] >= op + (tp_pts * be_trigger):
                    cur_sl = max(cur_sl, op + 1.0)
                    
                if bar['low'] <= cur_sl:
                    if cur_sl >= op:
                        be = True
                        pnl = 100.0 # +1 pt on 1 lot
                        exit_price = op + 1.0
                    else:
                        lost = True
                        pnl = -sl_pts * 100.0
                        exit_price = cur_sl
                    break
                elif bar['high'] >= cur_tp:
                    won = True
                    pnl = tp_pts * 100.0
                    exit_price = cur_tp
                    break
            else: # SELL
                if use_be and bar['low'] <= op - (tp_pts * be_trigger):
                    cur_sl = min(cur_sl, op - 1.0)
                    
                if bar['high'] >= cur_sl:
                    if cur_sl <= op:
                        be = True
                        pnl = 100.0
                        exit_price = op - 1.0
                    else:
                        lost = True
                        pnl = -sl_pts * 100.0
                        exit_price = cur_sl
                    break
                elif bar['low'] <= cur_tp:
                    won = True
                    pnl = tp_pts * 100.0
                    exit_price = cur_tp
                    break
                    
        # If trade reached end of 6 bars without hitting TP or SL, close at market
        if not (won or lost or be):
            last_close = df.iloc[min(i+5, len(df)-1)]['close']
            pts = (last_close - op) if action == 'BUY' else (op - last_close)
            pnl = pts * 100.0
            exit_price = last_close
            if pnl > 0: won = True
            elif pnl == 0: be = True
            else: lost = True
            
        trades.append({
            'datetime': time_str,
            'session': session_str,
            'action': action,
            'confidence': confidence,
            'op': round(op, 2),
            'tp': round(cur_tp, 2),
            'sl': round(op - sl_pts if action == 'BUY' else op + sl_pts, 2),
            'exit_price': round(exit_price, 2),
            'status': 'WIN' if won else ('BE' if be else 'LOSS'),
            'pnl_usd': round(pnl, 2)
        })
        
    return pd.DataFrame(trades)

res_df = run_simulation(tp_pts=10, sl_pts=15, use_be=True, be_trigger=0.5)
total_trades = len(res_df)
wins = len(res_df[res_df['status'] == 'WIN'])
bes = len(res_df[res_df['status'] == 'BE'])
losses = len(res_df[res_df['status'] == 'LOSS'])
effective_winrate = ((wins + bes) / total_trades) * 100
pure_winrate = (wins / total_trades) * 100
total_pnl = res_df['pnl_usd'].sum()

print(f"Total Trade Evaluated: {total_trades}")
print(f"Wins: {wins} | Breakeven/Protective: {bes} | Losses: {losses}")
print(f"Pure Winrate: {pure_winrate:.2f}% | Win + BE Protection Rate: {effective_winrate:.2f}%")
print(f"Total Net PnL (1.00 Lot = $100/pt): ${total_pnl:,.2f}")
print("\nSample Trades:")
print(res_df.head(15).to_string(index=False))

res_df.to_csv('backend/scripts/qwen_hourly_1week_results.csv', index=False)
