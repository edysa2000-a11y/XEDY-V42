import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

def run_analysis():
    if not mt5.initialize():
        print("MT5 initialization failed")
        return

    # Fetch last 120 H1 candles (approx 5-6 trading days / 1 full trading week)
    rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_H1, 0, 140)
    df = pd.DataFrame(rates)
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    
    print(f"Data range: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
    print(f"Total H1 bars: {len(df)}")
    print(f"Lowest price: {df['low'].min()}, Highest price: {df['high'].max()}")
    
    # Save to csv for inspection
    df.to_csv("backend/scripts/xauusd_h1_week.csv", index=False)
    print("Saved to backend/scripts/xauusd_h1_week.csv")

if __name__ == "__main__":
    run_analysis()
