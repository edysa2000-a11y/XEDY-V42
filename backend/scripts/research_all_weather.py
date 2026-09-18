import MetaTrader5 as mt5
import datetime
import pandas as pd
import numpy as np

def get_data():
    if not mt5.initialize():
        print("MT5 Init Failed")
        return None
        
    start_dt = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2026, 7, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
    
    rates_m15 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M15, start_dt, end_dt)
    df = pd.DataFrame(rates_m15)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # BB 2.0
    rolling_mean = df['close'].rolling(20).mean()
    rolling_std = df['close'].rolling(20).std()
    df['upper_bb'] = rolling_mean + (rolling_std * 2.0)
    df['lower_bb'] = rolling_mean - (rolling_std * 2.0)
    
    # BB 1.0 (for breakout confirmation)
    df['upper_bb_1'] = rolling_mean + (rolling_std * 1.0)
    df['lower_bb_1'] = rolling_mean - (rolling_std * 1.0)
    
    # ADX
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
    
    atr = tr.rolling(14).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/14).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/14).mean() / atr)
    dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
    df['adx'] = dx.ewm(alpha=1/14).mean()
    
    # ATR
    df['atr'] = atr.fillna(3.0)
    
    # H4 EMA 200
    start_h4 = start_dt - datetime.timedelta(days=100)
    rates_h4 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_H4, start_h4, end_dt)
    df_h4 = pd.DataFrame(rates_h4)
    df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
    df_h4['ema_200_h4'] = df_h4['close'].ewm(span=200, adjust=False).mean()
    df = pd.merge_asof(df, df_h4[['time', 'ema_200_h4']], on='time', direction='backward')
    
    return df.dropna()

def run_simulation(df, adx_threshold=25, tp_mult=1.5, sl_mult=2.0):
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
        
        float_profit = 0
        for p in positions:
            float_profit += (price - p['price']) * p['volume'] if p['type'] == 'BUY' else (p['price'] - price) * p['volume']
            
        if len(positions) >= 1 and float_profit >= (atr * tp_mult * 100 * sum(p['volume'] for p in positions) / 100):
            closed_pnl.append(float_profit)
            positions = []
            continue
            
        if len(positions) >= 1 and float_profit <= -(atr * sl_mult * 100 * sum(p['volume'] for p in positions) / 100):
            closed_pnl.append(float_profit)
            positions = []
            continue
            
        can_buy = len([p for p in positions if p['type'] == 'BUY']) < 3
        can_sell = len([p for p in positions if p['type'] == 'SELL']) < 3
        if len(positions) > 0 and abs(price - positions[-1]['price']) < atr:
            can_buy = False
            can_sell = False
            
        risk_amount = 200.0
        lot_volume = max(0.01, round(risk_amount / (atr * sl_mult * 10), 2) if atr > 0 else 0.01) * 100
        
        signal = None
        trend_h4 = "UP" if price > row['ema_200_h4'] else "DOWN"
        
        # All Weather Logic
        if row['adx'] > adx_threshold:
            # TRENDING: Volatility Breakout
            # Buy if price breaks strongly above upper BB 1.0
            if trend_h4 == "UP" and price > row['upper_bb_1'] and prev['close'] <= prev['upper_bb_1']:
                signal = "BUY"
            # Sell if price breaks strongly below lower BB 1.0
            elif trend_h4 == "DOWN" and price < row['lower_bb_1'] and prev['close'] >= prev['lower_bb_1']:
                signal = "SELL"
        else:
            # SIDEWAYS: Mean Reversion Sniper
            if trend_h4 != "DOWN" and row['low'] <= row['lower_bb'] and row['rsi'] < 30:
                signal = "BUY"
            elif trend_h4 != "UP" and row['high'] >= row['upper_bb'] and row['rsi'] > 70:
                signal = "SELL"
                
        if signal == "BUY" and can_buy and (len(positions) == 0 or positions[0]['type'] == 'BUY'):
            positions.append({'type': 'BUY', 'price': price, 'volume': lot_volume})
        elif signal == "SELL" and can_sell and (len(positions) == 0 or positions[0]['type'] == 'SELL'):
            positions.append({'type': 'SELL', 'price': price, 'volume': lot_volume})
            
    if current_month is not None:
        monthly_results[current_month] = closed_pnl.copy()
    return monthly_results

def evaluate():
    df = get_data()
    if df is None: return
    
    # Test combinations
    best_profit = -999999
    best_res = None
    
    for adx in [20, 25, 30]:
        res = run_simulation(df, adx_threshold=adx)
        total = sum(sum(pnl) for pnl in res.values())
        print(f"ADX Threshold {adx}: Total Profit ${total:,.2f}")
        
        all_positive = all(sum(pnl) > -2000 for pnl in res.values()) # Allow small drawdowns, but look for consistency
        if total > best_profit:
            best_profit = total
            best_res = res
            
    print("\nBEST RESULT MONTHLY BREAKDOWN:")
    total_prof = 0
    for m, pnl in best_res.items():
        p = sum(pnl)
        total_prof += p
        print(f"{m}: ${p:,.2f}")
    print(f"TOTAL: ${total_prof:,.2f}")

if __name__ == '__main__':
    evaluate()
