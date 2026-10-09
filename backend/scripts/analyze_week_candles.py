import pandas as pd
import numpy as np

df = pd.read_csv("C:/Antigravity/Project/XEDY Mission Control/backend/scripts/xauusd_h1_week.csv")
df['datetime'] = pd.to_datetime(df['datetime'])
df['date'] = df['datetime'].dt.date
df['hour'] = df['datetime'].dt.hour

daily_summary = df.groupby('date').agg(
    open=('open', 'first'),
    high=('high', 'max'),
    low=('low', 'min'),
    close=('close', 'last'),
    volume=('tick_volume', 'sum'),
    bars=('open', 'count')
).reset_index()

print("DAILY SUMMARY (PAST WEEK):")
print(daily_summary.to_string())
