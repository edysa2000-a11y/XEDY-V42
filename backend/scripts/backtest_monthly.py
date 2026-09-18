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

def get_data():
    if not mt5.initialize():
        print("MT5 Init Failed")
        return None
        
    start_dt = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2026, 7, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
    
    # Get M15 Data
    rates_m15 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M15, start_dt, end_dt)
    df_m15 = pd.DataFrame(rates_m15)
    df_m15['time'] = pd.to_datetime(df_m15['time'], unit='s')
    
    # Get H4 Data for Fundamental Trend Filter (EMA 200)
    start_h4 = start_dt - datetime.timedelta(days=100) # Get more history for EMA200
    rates_h4 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_H4, start_h4, end_dt)
    df_h4 = pd.DataFrame(rates_h4)
    df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
    df_h4['ema_200'] = df_h4['close'].ewm(span=200, adjust=False).mean()
    
    # Map H4 EMA to M15
    df_m15 = pd.merge_asof(df_m15, df_h4[['time', 'ema_200']], on='time', direction='backward')
    
    # Pre-calculate common indicators
    df_m15['rsi'] = calculate_rsi(df_m15)
    df_m15['tr'] = df_m15[['high', 'low', 'close']].apply(lambda x: max(x['high']-x['low'], 0), axis=1)
    df_m15['atr'] = df_m15['tr'].rolling(14).mean().fillna(3.0)
    df_m15['upper_bb'], df_m15['lower_bb'] = calculate_bollinger_bands(df_m15, num_of_std=2.0)
        
    return df_m15

def run_monthly_simulation(df):
    balance = 10000.0
    positions = []
    closed_pnl = []
    
    rsi_upper, rsi_lower = 70, 30
    sl_atr, tp_atr = 2.0, 1.5
    
    monthly_results = {}
    current_month = None
    
    for i in range(50, len(df)):
        row = df.iloc[i]
        dt = row['time']
        month_key = dt.strftime('%Y-%m')
        
        if current_month != month_key:
            if current_month is not None:
                monthly_results[current_month] = closed_pnl.copy()
            closed_pnl = []
            current_month = month_key
            balance = 10000.0 # Reset balance per month for consistent $200 risk evaluation
            positions = []
            
        price = row['close']
        low = row['low']
        high = row['high']
        rsi = row['rsi']
        lower_bb = row['lower_bb']
        upper_bb = row['upper_bb']
        atr = row['atr']
        ema_200 = row['ema_200']
        
        trend = "UP" if price > ema_200 else "DOWN"
        
        float_profit = 0
        for p in positions:
            float_profit += (price - p['price']) * p['volume'] if p['type'] == 'BUY' else (p['price'] - price) * p['volume']
            
        basket_tp_pips = atr * tp_atr * 100
        if len(positions) >= 1 and float_profit >= (basket_tp_pips * sum(p['volume'] for p in positions) / 100):
            balance += float_profit
            closed_pnl.append(float_profit)
            positions = []
            continue
            
        basket_sl_pips = atr * sl_atr * 100
        if len(positions) >= 1 and float_profit <= -(basket_sl_pips * sum(p['volume'] for p in positions) / 100):
            balance += float_profit
            closed_pnl.append(float_profit)
            positions = []
            continue
            
        can_buy = len([p for p in positions if p['type'] == 'BUY']) < 3
        can_sell = len([p for p in positions if p['type'] == 'SELL']) < 3
        
        # Grid Spacing
        if len(positions) > 0:
            last_p = positions[-1]
            if abs(price - last_p['price']) < atr:
                can_buy = False
                can_sell = False
                
        if trend == "DOWN": can_buy = False
        if trend == "UP": can_sell = False
            
        risk_amount = 200.0
        risk_pips = atr * sl_atr * 10
        lot_volume = round(risk_amount / risk_pips, 2) if risk_pips > 0 else 0.01
        lot_volume = max(0.01, lot_volume) * 100
        
        if len(positions) == 0 or (len(positions) > 0 and positions[0]['type'] == 'BUY'):
            if low <= lower_bb and rsi < rsi_lower and can_buy:
                positions.append({'type': 'BUY', 'price': price, 'volume': lot_volume})
                
        if len(positions) == 0 or (len(positions) > 0 and positions[0]['type'] == 'SELL'):
            if high >= upper_bb and rsi > rsi_upper and can_sell:
                positions.append({'type': 'SELL', 'price': price, 'volume': lot_volume})
                
    if current_month is not None:
        monthly_results[current_month] = closed_pnl.copy()
        
    return monthly_results

def main():
    print("Mengunduh data XAUUSD (Jan-Jul 2026)...")
    df = get_data()
    if df is None:
        return
        
    print("Menjalankan simulasi per bulan...")
    results = run_monthly_simulation(df)
    
    print("\n--- LAPORAN BACKTEST BULANAN (JAN - JUL 2026) ---")
    print("Parameter: BB=2.0, RSI=70/30, SL=2.0, TP=1.5, Filter=True")
    print("="*65)
    print(f"{'Bulan':<10} | {'Profit Net':<15} | {'Winrate':<10} | {'Total OP'}")
    print("-" * 65)
    
    total_profit = 0
    total_wins = 0
    total_trades = 0
    
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
