import pandas as pd
import numpy as np

df = pd.read_csv("C:/Antigravity/Project/XEDY Mission Control/backend/scripts/xauusd_h1_week.csv")
df['datetime'] = pd.to_datetime(df['datetime'])
df['date'] = df['datetime'].dt.date
df['hour'] = df['datetime'].dt.hour

print("Detailed H1 breakdown by day:")
for d, group in df.groupby('date'):
    print(f"\n================ DATE: {d} (Total bars: {len(group)}) ================")
    # Print key session bars: Asia (0-6), London (7-11), NY (12-18)
    for idx, row in group.iterrows():
        dt_str = row['datetime'].strftime("%H:%M")
        o, h, l, c = row['open'], row['high'], row['low'], row['close']
        rng = h - l
        body = abs(c - o)
        direction = "BULL" if c >= o else "BEAR"
        print(f"[{dt_str}] O:{o:.2f} H:{h:.2f} L:{l:.2f} C:{c:.2f} | Rng:{rng:.2f} | {direction} (Vol: {row['tick_volume']})")
