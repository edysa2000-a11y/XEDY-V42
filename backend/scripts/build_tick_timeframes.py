import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import os

print("Fetching and processing 1-week ticks from MT5...")
if not mt5.initialize():
    print("Failed to initialize MT5")
    exit(1)

utc_to = datetime.now(timezone.utc)
utc_from = utc_to - timedelta(days=7)
ticks = mt5.copy_ticks_range('XAUUSD', utc_from, utc_to, mt5.COPY_TICKS_ALL)
mt5.shutdown()

df = pd.DataFrame(ticks)
df['mid'] = (df['bid'] + df['ask']) / 2.0
df['mid_diff'] = df['mid'].diff()

# Lee-Ready Tick Rule
tick_dir = np.where(df['mid_diff'] > 0, 1, np.where(df['mid_diff'] < 0, -1, 0))
s = pd.Series(tick_dir).replace(0, np.nan).ffill().fillna(1).astype(int)
df['is_buy'] = (s == 1).astype(int)
df['is_sell'] = (s == -1).astype(int)
df['datetime'] = pd.to_datetime(df['time'], unit='s')
df.set_index('datetime', inplace=True)

timeframes = {
    'M1': '1min',
    'M5': '5min',
    'M15': '15min',
    'M30': '30min',
    'H1': '1h',
    'H4': '4h',
    'D1': '1D'
}

os.makedirs('data/ticks', exist_ok=True)

for name, rule in timeframes.items():
    ohlc = df['mid'].resample(rule).ohlc()
    bid = df['bid'].resample(rule).last()
    ask = df['ask'].resample(rule).last()
    total_ticks = df['mid'].resample(rule).count()
    buy_ticks = df['is_buy'].resample(rule).sum()
    sell_ticks = df['is_sell'].resample(rule).sum()
    
    tf_df = pd.DataFrame({
        'open': ohlc['open'],
        'high': ohlc['high'],
        'low': ohlc['low'],
        'close': ohlc['close'],
        'bid': bid,
        'ask': ask,
        'total_ticks': total_ticks,
        'buy_ticks': buy_ticks,
        'sell_ticks': sell_ticks
    }).dropna()
    
    tf_df['delta_ticks'] = tf_df['buy_ticks'] - tf_df['sell_ticks']
    tf_df['delta_pct'] = np.where(tf_df['total_ticks'] > 0, (tf_df['delta_ticks'] / tf_df['total_ticks']) * 100.0, 0.0)
    tf_df['buy_pct'] = np.where(tf_df['total_ticks'] > 0, (tf_df['buy_ticks'] / tf_df['total_ticks']) * 100.0, 50.0)
    tf_df['sell_pct'] = np.where(tf_df['total_ticks'] > 0, (tf_df['sell_ticks'] / tf_df['total_ticks']) * 100.0, 50.0)
    
    out_path = f'data/ticks/xauusd_{name}.csv'
    tf_df.to_csv(out_path)
    print(f"Generated {name}: {len(tf_df)} bars -> {out_path}")

print("All timeframes generated successfully.")
