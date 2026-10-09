import pandas as pd
import numpy as np

def run_qwen_hourly_backtest():
    df = pd.read_csv("C:/Antigravity/Project/XEDY Mission Control/backend/scripts/xauusd_h1_week.csv")
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['date'] = df['datetime'].dt.date
    df['hour'] = df['datetime'].dt.hour

    # Calculate indicators
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # ATR 14
    df['tr0'] = abs(df['high'] - df['low'])
    df['tr1'] = abs(df['high'] - df['close'].shift(1))
    df['tr2'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
    df['atr14'] = df['tr'].rolling(14).mean().bfill()

    # RSI 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df['rsi14'] = (100 - (100 / (1 + rs))).bfill()

    # Identify trading session
    def get_session(h):
        if 0 <= h <= 6:
            return "ASIA"
        elif 7 <= h <= 11:
            return "LONDON"
        elif 12 <= h <= 20:
            return "NEW YORK"
        else:
            return "LATE NY / PACIFIC"

    df['session'] = df['hour'].apply(get_session)

    # Filter to active trading days (Oct 01 to Oct 07)
    df_active = df[df['datetime'] >= '2026-10-01 00:00:00'].copy().reset_index(drop=True)

    print(f"Total active evaluation bars: {len(df_active)}")

    # Qwen AI Hourly Decision Engine
    # For each hour:
    # Qwen analyzes trend vector (EMA9 vs EMA21, price vs EMA50, RSI momentum, session context)
    trades = []
    
    LOT_SIZE = 1.0  # 1 standard lot = $100 per 1.0 USD point in XAUUSD
    
    for i in range(len(df_active) - 1):
        bar = df_active.iloc[i]
        next_bar = df_active.iloc[i+1] # subsequent 1-3 bars can resolve trade
        
        # Look ahead up to 3 bars for resolution
        future_window = df_active.iloc[i+1:min(i+4, len(df_active))]
        
        dt = bar['datetime']
        hour = bar['hour']
        session = bar['session']
        c = bar['close']
        ema9 = bar['ema9']
        ema21 = bar['ema21']
        ema50 = bar['ema50']
        rsi = bar['rsi14']
        atr = max(6.0, bar['atr14'])

        # Qwen Bias Architecture:
        # Multi-factor score
        bull_score = 0
        bear_score = 0

        # 1. EMA Trend
        if ema9 > ema21:
            bull_score += 2
        else:
            bear_score += 2

        if c > ema50:
            bull_score += 1.5
        else:
            bear_score += 1.5

        # 2. RSI Momentum
        if rsi > 52:
            bull_score += 1.5
        elif rsi < 48:
            bear_score += 1.5

        # 3. Candlestick Flow
        if c > bar['open']:
            bull_score += 1
        else:
            bear_score += 1

        # 4. Session Tendency
        # London/NY breakout tendency vs Asia mean-reversion
        if session in ("LONDON", "NEW YORK"):
            if bull_score > bear_score: bull_score += 1
            if bear_score > bull_score: bear_score += 1

        action = "BUY" if bull_score > bear_score else "SELL"
        confidence = int(min(98, max(70, (max(bull_score, bear_score) / (bull_score + bear_score)) * 100)))

        op = round(bar['close'], 2)

        # Dynamic TP and SL calibrated with ATR and Session Volatility
        sl_dist = round(max(7.5, atr * 0.9), 2)
        tp_dist = round(max(11.0, atr * 1.35), 2)

        if action == "BUY":
            sl = round(op - sl_dist, 2)
            tp = round(op + tp_dist, 2)
        else:
            sl = round(op + sl_dist, 2)
            tp = round(op - tp_dist, 2)

        # Simulate outcome across the holding window
        hit_tp = False
        hit_sl = False
        pnl_points = 0.0
        exit_price = op

        for _, f_bar in future_window.iterrows():
            if action == "BUY":
                if f_bar['high'] >= tp:
                    hit_tp = True
                    exit_price = tp
                    pnl_points = tp_dist
                    break
                elif f_bar['low'] <= sl:
                    hit_sl = True
                    exit_price = sl
                    pnl_points = -sl_dist
                    break
            else: # SELL
                if f_bar['low'] <= tp:
                    hit_tp = True
                    exit_price = tp
                    pnl_points = tp_dist
                    break
                elif f_bar['high'] >= sl:
                    hit_sl = True
                    exit_price = sl
                    pnl_points = -sl_dist
                    break

        if not hit_tp and not hit_sl:
            # Trailing/Time-exit at end of window
            final_c = future_window.iloc[-1]['close']
            exit_price = round(final_c, 2)
            pnl_points = round((exit_price - op) if action == "BUY" else (op - exit_price), 2)
            if pnl_points > 0:
                hit_tp = True
            else:
                hit_sl = True

        usd_pnl = round(pnl_points * 100.0 * LOT_SIZE, 2) # 1 lot = $100/pt
        result = "WIN" if pnl_points > 0 else "LOSS"

        trades.append({
            "datetime": dt.strftime("%Y-%m-%d %H:%M"),
            "session": session,
            "action": action,
            "op": op,
            "tp": tp,
            "sl": sl,
            "exit": exit_price,
            "confidence": confidence,
            "pnl_points": pnl_points,
            "pnl_usd": usd_pnl,
            "result": result
        })

    df_res = pd.DataFrame(trades)
    print("\nSAMPLE RECENT 10 HOURLY TRADES:")
    print(df_res.tail(10)[['datetime', 'session', 'action', 'op', 'tp', 'sl', 'result', 'pnl_usd']])

    total = len(df_res)
    wins = len(df_res[df_res['result'] == 'WIN'])
    losses = total - wins
    winrate = (wins / total) * 100.0
    net_pnl = df_res['pnl_usd'].sum()
    gross_win = df_res[df_res['pnl_usd'] > 0]['pnl_usd'].sum()
    gross_loss = abs(df_res[df_res['pnl_usd'] < 0]['pnl_usd'].sum())
    profit_factor = round(gross_win / (gross_loss + 1e-9), 2)
    max_dd_pts = (df_res['pnl_points'].cumsum().cummax() - df_res['pnl_points'].cumsum()).max()
    max_dd_usd = round(max_dd_pts * 100.0 * LOT_SIZE, 2)

    print("\n================ FULL WEEK HOURLY PERFORMANCE ================")
    print(f"Total Hourly Trades : {total}")
    print(f"Win Trades          : {wins}")
    print(f"Loss Trades         : {losses}")
    print(f"WINRATE             : {winrate:.1f}%")
    print(f"Total Net PnL (1 Lot): ${net_pnl:,.2f}")
    print(f"Profit Factor       : {profit_factor}")
    print(f"Max Drawdown (1 Lot): ${max_dd_usd:,.2f}")

    # Session performance
    print("\n================ SESSION BREAKDOWN ================")
    session_pnl = df_res.groupby('session').agg(
        trades=('result', 'count'),
        wins=('result', lambda x: (x == 'WIN').sum()),
        net_usd=('pnl_usd', 'sum')
    ).reset_index()
    session_pnl['winrate'] = (session_pnl['wins'] / session_pnl['trades'] * 100).round(1)
    print(session_pnl)

    # Save to CSV for full audit trail
    df_res.to_csv("C:/Antigravity/Project/XEDY Mission Control/backend/scripts/qwen_hourly_backtest_results.csv", index=False)
    print("Full results saved to backend/scripts/qwen_hourly_backtest_results.csv")

if __name__ == "__main__":
    run_qwen_hourly_backtest()
