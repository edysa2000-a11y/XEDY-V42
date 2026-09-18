import MetaTrader5 as mt5
import datetime
import pandas as pd
import numpy as np

def calculate_bollinger_bands(df, window=20, num_of_std=2.0):
    rolling_mean = df['close'].rolling(window=window).mean()
    rolling_std = df['close'].rolling(window=window).std()
    return rolling_mean + (rolling_std * num_of_std), rolling_mean - (rolling_std * num_of_std)

def calculate_rsi(df, window=14):
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    rs = gain.rolling(window=window).mean() / loss.rolling(window=window).mean()
    return 100 - (100 / (1 + rs))
    
def calculate_stoch_rsi(df, window=14, smoothK=3, smoothD=3):
    rsi = calculate_rsi(df, window)
    stoch_rsi = (rsi - rsi.rolling(window).min()) / (rsi.rolling(window).max() - rsi.rolling(window).min() + 1e-10)
    k = stoch_rsi.rolling(smoothK).mean() * 100
    d = k.rolling(smoothD).mean()
    return k, d

def calculate_adx(df, window=14):
    high = df['high']
    low = df['low']
    close = df['close']
    
    plus_dm = high.diff()
    minus_dm = low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = abs(minus_dm)
    
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    frames = [tr1, tr2, tr3]
    tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
    
    atr = tr.rolling(window).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/window).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/window).mean() / atr)
    
    dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
    adx = dx.ewm(alpha=1/window).mean()
    return adx, plus_di, minus_di

def get_data():
    if not mt5.initialize():
        print("MT5 Init Failed")
        return None
        
    start_dt = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2026, 7, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
    
    rates_m15 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M15, start_dt, end_dt)
    df = pd.DataFrame(rates_m15)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    df['rsi'] = calculate_rsi(df)
    df['stoch_k'], df['stoch_d'] = calculate_stoch_rsi(df)
    df['adx'], df['pdi'], df['mdi'] = calculate_adx(df)
    df['upper_bb'], df['lower_bb'] = calculate_bollinger_bands(df)
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    start_h4 = start_dt - datetime.timedelta(days=100)
    rates_h4 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_H4, start_h4, end_dt)
    df_h4 = pd.DataFrame(rates_h4)
    df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
    df_h4['ema_200_h4'] = df_h4['close'].ewm(span=200, adjust=False).mean()
    
    df = pd.merge_asof(df, df_h4[['time', 'ema_200_h4']], on='time', direction='backward')
    
    df['tr'] = df[['high', 'low', 'close']].apply(lambda x: max(x['high']-x['low'], 0), axis=1)
    df['atr'] = df['tr'].rolling(14).mean().fillna(3.0)
    
    return df.dropna()

def run_adaptive_simulation(df):
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
        low = row['low']
        high = row['high']
        atr = row['atr']
        
        # Regimes
        adx = row['adx']
        is_trending = adx > 25
        
        trend_h4 = "UP" if price > row['ema_200_h4'] else "DOWN"
        
        float_profit = 0
        for p in positions:
            float_profit += (price - p['price']) * p['volume'] if p['type'] == 'BUY' else (p['price'] - price) * p['volume']
            
        # TP / SL logic (dynamic based on regime)
        sl_atr = 3.0 if is_trending else 2.0
        tp_atr = 2.0 if is_trending else 1.5
        
        if len(positions) >= 1 and float_profit >= (atr * tp_atr * 100 * sum(p['volume'] for p in positions) / 100):
            balance += float_profit
            closed_pnl.append(float_profit)
            positions = []
            continue
            
        if len(positions) >= 1 and float_profit <= -(atr * sl_atr * 100 * sum(p['volume'] for p in positions) / 100):
            balance += float_profit
            closed_pnl.append(float_profit)
            positions = []
            continue
            
        can_buy = len([p for p in positions if p['type'] == 'BUY']) < 3
        can_sell = len([p for p in positions if p['type'] == 'SELL']) < 3
        
        if len(positions) > 0:
            last_p = positions[-1]
            if abs(price - last_p['price']) < atr:
                can_buy = False
                can_sell = False
                
        risk_amount = 200.0
        risk_pips = atr * sl_atr * 10
        lot_volume = max(0.01, round(risk_amount / risk_pips, 2) if risk_pips > 0 else 0.01) * 100
        
        signal = None
        
        if is_trending:
            # Weapon B: EMA Ribbon + Stoch RSI
            # Uptrend
            if trend_h4 == "UP" and row['pdi'] > row['mdi']:
                # Discount zone: low crosses below EMA 20, but above EMA 50
                if low < row['ema_20'] and price > row['ema_50']:
                    # Stoch RSI crossover from oversold
                    if prev['stoch_k'] < 20 and row['stoch_k'] > row['stoch_d'] and prev['stoch_k'] <= prev['stoch_d']:
                        signal = "BUY"
            # Downtrend
            elif trend_h4 == "DOWN" and row['mdi'] > row['pdi']:
                if high > row['ema_20'] and price < row['ema_50']:
                    if prev['stoch_k'] > 80 and row['stoch_k'] < row['stoch_d'] and prev['stoch_k'] >= prev['stoch_d']:
                        signal = "SELL"
        else:
            # Weapon A: Sniper BB + RSI
            if trend_h4 != "DOWN" and low <= row['lower_bb'] and row['rsi'] < 30:
                signal = "BUY"
            elif trend_h4 != "UP" and high >= row['upper_bb'] and row['rsi'] > 70:
                signal = "SELL"
                
        if signal == "BUY" and can_buy and (len(positions) == 0 or positions[0]['type'] == 'BUY'):
            positions.append({'type': 'BUY', 'price': price, 'volume': lot_volume})
        elif signal == "SELL" and can_sell and (len(positions) == 0 or positions[0]['type'] == 'SELL'):
            positions.append({'type': 'SELL', 'price': price, 'volume': lot_volume})
            
    if current_month is not None:
        monthly_results[current_month] = closed_pnl.copy()
        
    return monthly_results

def main():
    print("Mengunduh data XAUUSD (Jan-Jul 2026)...")
    df = get_data()
    if df is None: return
    
    print("Menjalankan simulasi Adaptive Regime (Weapon A vs Weapon B)...")
    results = run_adaptive_simulation(df)
    
    print("\n--- LAPORAN BACKTEST BULANAN ADAPTIVE (JAN - JUL 2026) ---")
    print("Parameter: ADX Regime, EMA Ribbon + Stoch RSI (Trend), BB+RSI (Sideways)")
    print("="*65)
    print(f"{'Bulan':<10} | {'Profit Net':<15} | {'Winrate':<10} | {'Total OP'}")
    print("-" * 65)
    
    total_profit, total_wins, total_trades = 0, 0, 0
    for month, pnl in results.items():
        profit = sum(pnl)
        trades = len(pnl)
        wins = len([p for p in pnl if p > 0])
        winrate = (wins / trades * 100) if trades > 0 else 0
        total_profit += profit
        total_wins += wins
        total_trades += trades
        print(f"{month:<10} | ${profit:>13,.2f} | {winrate:>8.1f}% | {trades}")
        
    print("="*65)
    avg_winrate = (total_wins / total_trades * 100) if total_trades > 0 else 0
    print(f"TOTAL      | ${total_profit:>13,.2f} | {avg_winrate:>8.1f}% | {total_trades}")

if __name__ == '__main__':
    main()
