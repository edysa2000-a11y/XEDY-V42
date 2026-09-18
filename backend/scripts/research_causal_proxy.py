import MetaTrader5 as mt5
import datetime
import pandas as pd
import numpy as np

def get_data():
    mt5.initialize()
    start_dt = datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2022, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
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
    
    # ATR
    high, low, close = df['high'], df['low'], df['close']
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)
    df['atr'] = tr.rolling(14).mean().fillna(3.0)
    
    # MACRO PROXY: Daily EMA (Trend Jangka Panjang yang disetir oleh Makroekonomi)
    start_d1 = start_dt - datetime.timedelta(days=200)
    rates_d1 = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_D1, start_d1, end_dt)
    df_d1 = pd.DataFrame(rates_d1)
    df_d1['time'] = pd.to_datetime(df_d1['time'], unit='s')
    df_d1['macro_bias'] = df_d1['close'].ewm(span=50, adjust=False).mean() # D1 EMA 50 sebagai proxy Fundamental
    df = pd.merge_asof(df, df_d1[['time', 'macro_bias']], on='time', direction='backward')
    
    return df.dropna()

def run_simulation(df):
    balance = 10000.0
    positions = []
    closed_pnl = []
    monthly_results = {}
    current_month = None
    
    # Trailing Stop Settings
    SL_ATR = 1.5
    TRAIL_STEP_ATR = 0.5
    
    for i in range(50, len(df)):
        row = df.iloc[i]
        dt = row['time']
        month_key = dt.strftime('%Y-%m')
        
        if current_month != month_key:
            if current_month is not None:
                monthly_results[current_month] = closed_pnl.copy()
            closed_pnl = []
            current_month = month_key
            balance = 10000.0 # reset per month for consistency
            positions = []
            
        price = row['close']
        atr = row['atr']
        
        # Macro Bias (Fundamental Proxy)
        macro_bias = "UP" if price > row['macro_bias'] else "DOWN"
        
        # Update Trailing Stop
        pos_to_close = []
        for p in positions:
            if p['type'] == 'BUY':
                # If price moves in our favor, trail the SL up
                if price - p['price'] > (atr * TRAIL_STEP_ATR):
                    new_sl = price - (atr * SL_ATR)
                    if new_sl > p['sl']:
                        p['sl'] = new_sl
                # Check if stopped out
                if price <= p['sl']:
                    pos_to_close.append(p)
            elif p['type'] == 'SELL':
                if p['price'] - price > (atr * TRAIL_STEP_ATR):
                    new_sl = price + (atr * SL_ATR)
                    if new_sl < p['sl']:
                        p['sl'] = new_sl
                if price >= p['sl']:
                    pos_to_close.append(p)
                    
        for p in pos_to_close:
            pnl = (p['sl'] - p['price']) * p['volume'] if p['type'] == 'BUY' else (p['price'] - p['sl']) * p['volume']
            closed_pnl.append(pnl)
            balance += pnl
            positions.remove(p)
            
        # Entry Rules (Only following Macro Bias)
        can_buy = macro_bias == "UP" and len([p for p in positions if p['type'] == 'BUY']) < 3
        can_sell = macro_bias == "DOWN" and len([p for p in positions if p['type'] == 'SELL']) < 3
        
        if len(positions) > 0 and abs(price - positions[-1]['price']) < atr:
            can_buy = False
            can_sell = False
            
        risk_amount = 200.0
        risk_pips = atr * SL_ATR * 10
        lot_volume = max(0.01, round(risk_amount / risk_pips, 2) if risk_pips > 0 else 0.01) * 100
        
        if can_buy and row['low'] <= row['lower_bb'] and row['rsi'] < 30:
            positions.append({'type': 'BUY', 'price': price, 'volume': lot_volume, 'sl': price - (atr * SL_ATR)})
        elif can_sell and row['high'] >= row['upper_bb'] and row['rsi'] > 70:
            positions.append({'type': 'SELL', 'price': price, 'volume': lot_volume, 'sl': price + (atr * SL_ATR)})
            
    if current_month is not None:
        monthly_results[current_month] = closed_pnl.copy()
    return monthly_results

def evaluate():
    print("Memulai Backtest Trailing Stop & Macro Bias Proxy...")
    df = get_data()
    if df is None: return
    res = run_simulation(df)
    
    print("\n--- CAUSAL SUPREMACY PROXY RESULTS (2021 - 2022) ---")
    print(f"{'Bulan':<10} | {'Profit Net':<15} | {'Winrate':<10} | {'Total OP'}")
    print("-" * 55)
    
    total_prof = 0
    total_wins = 0
    total_trades = 0
    for m, pnl in res.items():
        p = sum(pnl)
        total_prof += p
        wins = len([x for x in pnl if x > 0])
        trades = len(pnl)
        wr = (wins/trades*100) if trades>0 else 0
        total_wins += wins
        total_trades += trades
        print(f"{m:<10} | ${p:>13,.2f} | {wr:>8.1f}% | {trades}")
        
    print("-" * 55)
    avg_wr = (total_wins/total_trades*100) if total_trades>0 else 0
    print(f"TOTAL      | ${total_prof:>13,.2f} | {avg_wr:>8.1f}% | {total_trades}")

if __name__ == '__main__':
    evaluate()
