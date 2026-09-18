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
    
    # ATR & ADX
    high, low, close = df['high'], df['low'], df['close']
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = abs(minus_dm)
    
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)
    atr = tr.rolling(14).mean().fillna(3.0)
    df['atr'] = atr
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/14).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/14).mean() / atr)
    dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
    df['adx'] = dx.ewm(alpha=1/14).mean()
    
    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # BB 2.0
    rolling_mean = close.rolling(20).mean()
    rolling_std = close.rolling(20).std()
    df['upper_bb'] = rolling_mean + (rolling_std * 2.0)
    df['lower_bb'] = rolling_mean - (rolling_std * 2.0)
    
    # Supertrend 3.0
    hl2 = (high + low) / 2
    df['basic_ub'] = hl2 + (3.0 * atr)
    df['basic_lb'] = hl2 - (3.0 * atr)
    df['final_ub'] = 0.0
    df['final_lb'] = 0.0
    df['st_trend'] = 1
    
    for i in range(1, len(df)):
        if df['basic_ub'].iloc[i] < df['final_ub'].iloc[i-1] or close.iloc[i-1] > df['final_ub'].iloc[i-1]:
            df.loc[df.index[i], 'final_ub'] = df['basic_ub'].iloc[i]
        else:
            df.loc[df.index[i], 'final_ub'] = df['final_ub'].iloc[i-1]
            
        if df['basic_lb'].iloc[i] > df['final_lb'].iloc[i-1] or close.iloc[i-1] < df['final_lb'].iloc[i-1]:
            df.loc[df.index[i], 'final_lb'] = df['basic_lb'].iloc[i]
        else:
            df.loc[df.index[i], 'final_lb'] = df['final_lb'].iloc[i-1]
            
        if df['st_trend'].iloc[i-1] == 1 and close.iloc[i] < df['final_lb'].iloc[i]:
            df.loc[df.index[i], 'st_trend'] = -1
        elif df['st_trend'].iloc[i-1] == -1 and close.iloc[i] > df['final_ub'].iloc[i]:
            df.loc[df.index[i], 'st_trend'] = 1
        else:
            df.loc[df.index[i], 'st_trend'] = df['st_trend'].iloc[i-1]
            
    # H4 EMA 200
    start_h4 = start_dt - datetime.timedelta(days=100)
    rates_h4 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_H4, start_h4, end_dt)
    df_h4 = pd.DataFrame(rates_h4)
    df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
    df_h4['ema_200_h4'] = df_h4['close'].ewm(span=200, adjust=False).mean()
    df = pd.merge_asof(df, df_h4[['time', 'ema_200_h4']], on='time', direction='backward')
    
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
        adx = row['adx']
        st_trend = row['st_trend']
        prev_st_trend = prev['st_trend']
        trend_h4 = "UP" if price > row['ema_200_h4'] else "DOWN"
        
        is_trending = adx > 25
        
        float_profit = 0
        pos_to_close = []
        for p in positions:
            if p['strategy'] == 'SUPERTREND':
                if p['type'] == 'BUY' and price < row['final_lb']:
                    pos_to_close.append(p)
                elif p['type'] == 'SELL' and price > row['final_ub']:
                    pos_to_close.append(p)
            elif p['strategy'] == 'SNIPER':
                p_float = (price - p['price']) * p['volume'] if p['type'] == 'BUY' else (p['price'] - price) * p['volume']
                if p_float >= (atr * 1.5 * 100 * p['volume'] / 100) or p_float <= -(atr * 2.0 * 100 * p['volume'] / 100):
                    pos_to_close.append(p)
                    
        for p in pos_to_close:
            pnl = (price - p['price']) * p['volume'] if p['type'] == 'BUY' else (p['price'] - price) * p['volume']
            closed_pnl.append(pnl)
            balance += pnl
            positions.remove(p)
            
        risk_amount = 200.0
        
        can_buy_sniper = len([p for p in positions if p['type'] == 'BUY']) < 3
        can_sell_sniper = len([p for p in positions if p['type'] == 'SELL']) < 3
        
        if is_trending:
            risk_pips = (row['final_ub'] - price) * 10 if st_trend == -1 else (price - row['final_lb']) * 10
            lot_volume = max(0.01, round(risk_amount / risk_pips, 2) if risk_pips > 0 else 0.01) * 100
            if st_trend == 1 and prev_st_trend == -1 and len(positions) == 0:
                positions.append({'type': 'BUY', 'price': price, 'volume': lot_volume, 'strategy': 'SUPERTREND'})
            elif st_trend == -1 and prev_st_trend == 1 and len(positions) == 0:
                positions.append({'type': 'SELL', 'price': price, 'volume': lot_volume, 'strategy': 'SUPERTREND'})
        else:
            risk_pips = atr * 2.0 * 10
            lot_volume = max(0.01, round(risk_amount / risk_pips, 2) if risk_pips > 0 else 0.01) * 100
            if trend_h4 != "DOWN" and row['low'] <= row['lower_bb'] and row['rsi'] < 30 and can_buy_sniper:
                positions.append({'type': 'BUY', 'price': price, 'volume': lot_volume, 'strategy': 'SNIPER'})
            elif trend_h4 != "UP" and row['high'] >= row['upper_bb'] and row['rsi'] > 70 and can_sell_sniper:
                positions.append({'type': 'SELL', 'price': price, 'volume': lot_volume, 'strategy': 'SNIPER'})
                
    if current_month is not None:
        monthly_results[current_month] = closed_pnl.copy()
    return monthly_results

def evaluate():
    df = get_data()
    if df is None: return
    res = run_simulation(df)
    
    print("\n--- HYBRID (SUPERTREND + SNIPER) ALL-WEATHER RESULTS ---")
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
