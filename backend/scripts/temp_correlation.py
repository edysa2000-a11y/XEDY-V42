import pandas as pd
import numpy as np
try:
    from tvDatafeed import TvDatafeed, Interval
except:
    exit()

def run_correlation():
    tv = TvDatafeed()
    df_gold = tv.get_hist(symbol="XAUUSD", exchange="OANDA", interval=Interval.in_daily, n_bars=365)
    df_oil = tv.get_hist(symbol="USOIL", exchange="TVC", interval=Interval.in_daily, n_bars=365)
    
    if df_gold is not None and df_oil is not None:
        df_gold['gold_return'] = df_gold['close'].pct_change()
        df_oil['oil_return'] = df_oil['close'].pct_change()
        
        merged = df_gold[['gold_return', 'close']].join(df_oil[['oil_return', 'close']], lsuffix='_gold', rsuffix='_oil', how='inner')
        corr = merged['gold_return'].corr(merged['oil_return'])
        
        print(f"XAUUSD and USOIL Daily Returns Correlation (1 Year): {corr:.4f}")
        
if __name__ == "__main__":
    run_correlation()
