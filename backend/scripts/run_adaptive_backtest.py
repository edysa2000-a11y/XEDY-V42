import MetaTrader5 as mt5
import datetime
import pandas as pd
import numpy as np

def calculate_bollinger_bands(df, window=20, num_of_std=2.5):
    rolling_mean = df['close'].rolling(window=window).mean()
    rolling_std = df['close'].rolling(window=window).std()
    return rolling_mean + (rolling_std * num_of_std), rolling_mean - (rolling_std * num_of_std)

def calculate_rsi(df, window=14):
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    rs = gain.rolling(window=window).mean() / loss.rolling(window=window).mean()
    return 100 - (100 / (1 + rs))

def main():
    mt5.initialize()
    end_dt = datetime.datetime.now(datetime.timezone.utc)
    rates = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M15, end_dt - datetime.timedelta(days=30), end_dt)
    df = pd.DataFrame(rates)
    df['upper_band'], df['lower_band'] = calculate_bollinger_bands(df)
    df['rsi'] = calculate_rsi(df)
    df['tr'] = df[['high', 'low', 'close']].apply(lambda x: max(x['high']-x['low'], 0), axis=1) # simplified ATR for speed
    df['atr'] = df['tr'].rolling(14).mean().fillna(3.0)
    
    balance = 10000.0
    positions = []
    closed = []
    
    for i in range(20, len(df)):
        price = df['close'].iloc[i]
        low = df['low'].iloc[i]
        high = df['high'].iloc[i]
        rsi = df['rsi'].iloc[i]
        lower_bb = df['lower_band'].iloc[i]
        upper_bb = df['upper_band'].iloc[i]
        atr = df['atr'].iloc[i]
        
        float_profit = 0
        for p in positions:
            float_profit += (price - p['price']) * 100 if p['type'] == 'BUY' else (p['price'] - price) * 100
            
        # Basket TP
        if len(positions) >= 1 and float_profit >= (atr * 1.5 * 100):
            balance += float_profit
            closed.append(float_profit)
            positions = []
            continue
            
        # Stop Loss / Hedge Lock Trigger (2.0 ATR)
        if len(positions) >= 1 and float_profit <= -(atr * 2.0 * 100 * len(positions)):
            balance += float_profit
            closed.append(float_profit)
            positions = []
            continue
            
        # Averaging logic (Max 3)
        can_buy = len([p for p in positions if p['type'] == 'BUY']) < 3
        can_sell = len([p for p in positions if p['type'] == 'SELL']) < 3
        
        if len(positions) > 0:
            last_p = positions[-1]
            if abs(price - last_p['price']) < atr:
                can_buy = False
                can_sell = False
                
        if len(positions) == 0 or (len(positions) > 0 and positions[0]['type'] == 'BUY'):
            if low <= lower_bb and rsi < 60 and can_buy:
                positions.append({'type': 'BUY', 'price': price})
        
        if len(positions) == 0 or (len(positions) > 0 and positions[0]['type'] == 'SELL'):
            if high >= upper_bb and rsi > 40 and can_sell:
                positions.append({'type': 'SELL', 'price': price})
                
    print("\n=== FULL ADAPTIVE (RSI+BB) + GRID AVERAGING BACKTEST ===")
    print(f"Total Baskets Closed: {len(closed)}")
    wins = len([t for t in closed if t > 0])
    print(f"Winrate: {wins/len(closed)*100 if closed else 0:.1f}%")
    print(f"Net Profit: ${sum(closed):.2f}")

if __name__ == '__main__':
    main()
