import pandas as pd
import numpy as np

timeframes = ['M1', 'M5', 'M15', 'M30', 'H1']

print("="*85)
print("BACKTEST BASELINE TICK MODE (RULE USER: SELISIH 5-10%, CLOSE < 2%)")
print("1.00 Standard Lot ($100 per point move pada XAUUSD)")
print("="*85)

for tf in timeframes:
    df = pd.read_csv(f'data/ticks/xauusd_{tf}.csv')
    df['datetime'] = pd.to_datetime(df['datetime'])
    
    trades = []
    in_pos = False
    pos_type = None
    entry_price = 0.0
    entry_time = None
    
    for i in range(len(df)-1):
        row = df.iloc[i]
        next_row = df.iloc[i+1]
        
        delta_pct = row['delta_pct']
        
        # Check exit if in position
        if in_pos:
            if pos_type == 'BUY':
                if delta_pct < 2.0:
                    exit_price = row['close']
                    pnl = (exit_price - entry_price) * 100.0 # 1 lot = $100/pt
                    trades.append({
                        'type': 'BUY',
                        'entry_time': entry_time,
                        'exit_time': row['datetime'],
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl_usd': pnl,
                        'won': pnl > 0
                    })
                    in_pos = False
                    pos_type = None
            elif pos_type == 'SELL':
                if delta_pct > -2.0:
                    exit_price = row['close']
                    pnl = (entry_price - exit_price) * 100.0
                    trades.append({
                        'type': 'SELL',
                        'entry_time': entry_time,
                        'exit_time': row['datetime'],
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl_usd': pnl,
                        'won': pnl > 0
                    })
                    in_pos = False
                    pos_type = None
                    
        # Check entry if not in position
        if not in_pos:
            # BUY: delta_pct between 5% and 10%
            if 5.0 <= delta_pct <= 10.0:
                in_pos = True
                pos_type = 'BUY'
                entry_price = row['close']
                entry_time = row['datetime']
            # SELL: delta_pct between -10% and -5%
            elif -10.0 <= delta_pct <= -5.0:
                in_pos = True
                pos_type = 'SELL'
                entry_price = row['close']
                entry_time = row['datetime']
                
    if trades:
        tdf = pd.DataFrame(trades)
        wins = tdf['won'].sum()
        total = len(tdf)
        wr = (wins / total) * 100.0
        tot_pnl = tdf['pnl_usd'].sum()
        avg_trade = tdf['pnl_usd'].mean()
        profit_trades = tdf[tdf['pnl_usd'] > 0]['pnl_usd'].sum()
        loss_trades = abs(tdf[tdf['pnl_usd'] < 0]['pnl_usd'].sum())
        pf = (profit_trades / loss_trades) if loss_trades > 0 else 99.0
        
        print(f"[{tf:3s}] Trades: {total:4d} | Win: {wins:4d} | Loss: {total-wins:4d} | WR: {wr:5.1f}% | Net USD: ${tot_pnl:10.2f} | PF: {pf:4.2f} | Avg: ${avg_trade:6.2f}")
    else:
        print(f"[{tf:3s}] No trades generated")
