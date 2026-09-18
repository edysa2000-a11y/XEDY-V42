import MetaTrader5 as mt5
import datetime
import pandas as pd
import numpy as np
from itertools import product

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

def get_data():
    if not mt5.initialize():
        print("MT5 Init Failed")
        return None, None
        
    end_dt = datetime.datetime.now(datetime.timezone.utc)
    start_dt = end_dt - datetime.timedelta(days=30)
    
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
    
    # Pre-calculate BB for all STDs
    for std in [2.0, 2.5, 3.0]:
        df_m15[f'upper_bb_{std}'], df_m15[f'lower_bb_{std}'] = calculate_bollinger_bands(df_m15, num_of_std=std)
        
    return df_m15

def run_simulation(df, bb_std, rsi_bounds, sl_atr, tp_atr, use_trend_filter):
    balance = 10000.0
    positions = []
    closed_pnl = []
    
    rsi_upper, rsi_lower = rsi_bounds
    upper_bb_col = f'upper_bb_{bb_std}'
    lower_bb_col = f'lower_bb_{bb_std}'
    
    for i in range(50, len(df)):
        row = df.iloc[i]
        price = row['close']
        low = row['low']
        high = row['high']
        rsi = row['rsi']
        lower_bb = row[lower_bb_col]
        upper_bb = row[upper_bb_col]
        atr = row['atr']
        ema_200 = row['ema_200']
        
        # Current trend based on EMA200 H4
        trend = "UP" if price > ema_200 else "DOWN"
        
        float_profit = 0
        for p in positions:
            float_profit += (price - p['price']) * p['volume'] if p['type'] == 'BUY' else (p['price'] - price) * p['volume']
            
        # Basket TP
        basket_tp_pips = atr * tp_atr * 100
        if len(positions) >= 1 and float_profit >= (basket_tp_pips * sum(p['volume'] for p in positions) / 100):
            balance += float_profit
            closed_pnl.append(float_profit)
            positions = []
            continue
            
        # SL
        basket_sl_pips = atr * sl_atr * 100
        if len(positions) >= 1 and float_profit <= -(basket_sl_pips * sum(p['volume'] for p in positions) / 100):
            balance += float_profit
            closed_pnl.append(float_profit)
            positions = []
            continue
            
        # Max 3 positions
        can_buy = len([p for p in positions if p['type'] == 'BUY']) < 3
        can_sell = len([p for p in positions if p['type'] == 'SELL']) < 3
        
        # Grid Spacing
        if len(positions) > 0:
            last_p = positions[-1]
            if abs(price - last_p['price']) < atr:
                can_buy = False
                can_sell = False
                
        # Filter Trend
        if use_trend_filter:
            if trend == "DOWN": can_buy = False
            if trend == "UP": can_sell = False
            
        # Risk 2% ($200)
        risk_amount = 200.0
        risk_pips = atr * sl_atr * 10
        lot_volume = round(risk_amount / risk_pips, 2) if risk_pips > 0 else 0.01
        lot_volume = max(0.01, lot_volume) * 100 # Multiplier for easier math
        
        if len(positions) == 0 or (len(positions) > 0 and positions[0]['type'] == 'BUY'):
            if low <= lower_bb and rsi < rsi_lower and can_buy:
                positions.append({'type': 'BUY', 'price': price, 'volume': lot_volume})
                
        if len(positions) == 0 or (len(positions) > 0 and positions[0]['type'] == 'SELL'):
            if high >= upper_bb and rsi > rsi_upper and can_sell:
                positions.append({'type': 'SELL', 'price': price, 'volume': lot_volume})
                
    win_count = len([t for t in closed_pnl if t > 0])
    total_trades = len(closed_pnl)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
    net_profit = sum(closed_pnl)
    return net_profit, win_rate, total_trades

def main():
    print("Mengunduh data XAUUSD (1 Bulan Terakhir)...")
    df = get_data()
    if df is None:
        return
        
    bb_stds = [2.0, 2.5, 3.0]
    rsi_bounds = [(60, 40), (70, 30)]
    sl_atrs = [2.0, 3.0]
    tp_atrs = [1.0, 1.5, 2.0]
    use_trend = [True, False]
    
    results = []
    perms = list(product(bb_stds, rsi_bounds, sl_atrs, tp_atrs, use_trend))
    print(f"Memulai Grid Search Optimizer ({len(perms)} kombinasi)...")
    
    for bb, rsi, sl, tp, trend in perms:
        profit, wr, trades = run_simulation(df, bb, rsi, sl, tp, trend)
        results.append({
            'BB': bb, 'RSI': f"{rsi[0]}/{rsi[1]}", 'SL': sl, 'TP': tp, 'TrendFilter': trend,
            'Profit': profit, 'Winrate': wr, 'Trades': trades
        })
        
    df_res = pd.DataFrame(results)
    df_res = df_res.sort_values('Profit', ascending=False).head(3)
    
    print("\n--- TOP 3 SETELAN PALING PROFITABLE (MODAL $10000, RISK 2%) ---")
    print("="*70)
    for idx, row in df_res.iterrows():
        print(f"Profit: ${row['Profit']:,.2f} | Winrate: {row['Winrate']:.1f}% | Trades: {row['Trades']}")
        print(f"  -> BB Std: {row['BB']}, RSI: {row['RSI']}, SL: {row['SL']}x ATR, TP: {row['TP']}x ATR, Trend Filter: {row['TrendFilter']}")
        print("-" * 70)

if __name__ == '__main__':
    main()
