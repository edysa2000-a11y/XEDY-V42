import MetaTrader5 as mt5
import datetime
import pandas as pd
import numpy as np

def get_data():
    mt5.initialize()
    start_dt = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2026, 7, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
    rates_m15 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M15, start_dt, end_dt)
    df = pd.DataFrame(rates_m15)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # ATR
    high, low, close = df['high'], df['low'], df['close']
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)
    df['atr'] = tr.rolling(14).mean().fillna(3.0)
    
    # Supertrend (Classic All-Weather Trend Follower)
    atr_multiplier = 3.0
    hl2 = (df['high'] + df['low']) / 2
    df['basic_ub'] = hl2 + (atr_multiplier * df['atr'])
    df['basic_lb'] = hl2 - (atr_multiplier * df['atr'])
    
    df['final_ub'] = 0.0
    df['final_lb'] = 0.0
    df['trend'] = 1 # 1 for up, -1 for down
    
    for i in range(1, len(df)):
        if df['basic_ub'].iloc[i] < df['final_ub'].iloc[i-1] or df['close'].iloc[i-1] > df['final_ub'].iloc[i-1]:
            df.loc[df.index[i], 'final_ub'] = df['basic_ub'].iloc[i]
        else:
            df.loc[df.index[i], 'final_ub'] = df['final_ub'].iloc[i-1]
            
        if df['basic_lb'].iloc[i] > df['final_lb'].iloc[i-1] or df['close'].iloc[i-1] < df['final_lb'].iloc[i-1]:
            df.loc[df.index[i], 'final_lb'] = df['basic_lb'].iloc[i]
        else:
            df.loc[df.index[i], 'final_lb'] = df['final_lb'].iloc[i-1]
            
        if df['trend'].iloc[i-1] == 1 and df['close'].iloc[i] < df['final_lb'].iloc[i]:
            df.loc[df.index[i], 'trend'] = -1
        elif df['trend'].iloc[i-1] == -1 and df['close'].iloc[i] > df['final_ub'].iloc[i]:
            df.loc[df.index[i], 'trend'] = 1
        else:
            df.loc[df.index[i], 'trend'] = df['trend'].iloc[i-1]
            
    return df.dropna()

def run_simulation(df):
    balance = 10000.0
    positions = []
    closed_pnl = []
    monthly_results = {}
    current_month = None
    
    for i in range(50, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        dt = row['time']
        month_key = dt.strftime('%Y-%m')
        
        if current_month != month_key:
            if current_month is not None:
                monthly_results[current_month] = closed_pnl.copy()
            closed_pnl = []
            current_month = month_key
            balance = 10000.0
            positions = []
            
        price = row['close']
        atr = row['atr']
        trend = row['trend']
        prev_trend = prev['trend']
        
        # Process trailing stops based on Supertrend line
        float_profit = 0
        pos_to_close = []
        for p in positions:
            if p['type'] == 'BUY':
                if price < row['final_lb']: # Trend flipped down
                    pos_to_close.append(p)
            elif p['type'] == 'SELL':
                if price > row['final_ub']: # Trend flipped up
                    pos_to_close.append(p)
                    
        for p in pos_to_close:
            pnl = (price - p['price']) * p['volume'] if p['type'] == 'BUY' else (p['price'] - price) * p['volume']
            closed_pnl.append(pnl)
            balance += pnl
            positions.remove(p)
            
        risk_amount = 200.0
        risk_pips = (row['final_ub'] - price) * 10 if trend == -1 else (price - row['final_lb']) * 10
        lot_volume = max(0.01, round(risk_amount / risk_pips, 2) if risk_pips > 0 else 0.01) * 100
        
        # Entry on flip
        if trend == 1 and prev_trend == -1:
            positions.append({'type': 'BUY', 'price': price, 'volume': lot_volume})
        elif trend == -1 and prev_trend == 1:
            positions.append({'type': 'SELL', 'price': price, 'volume': lot_volume})
            
    if current_month is not None:
        monthly_results[current_month] = closed_pnl.copy()
    return monthly_results

def evaluate():
    df = get_data()
    if df is None: return
    res = run_simulation(df)
    
    print("\n--- SUPERTREND ALL-WEATHER RESULTS ---")
    total_prof = 0
    for m, pnl in res.items():
        p = sum(pnl)
        total_prof += p
        wins = len([x for x in pnl if x > 0])
        trades = len(pnl)
        wr = (wins/trades*100) if trades>0 else 0
        print(f"{m}: ${p:>10,.2f} | WR: {wr:.1f}%")
    print(f"TOTAL: ${total_prof:,.2f}")

if __name__ == '__main__':
    evaluate()
