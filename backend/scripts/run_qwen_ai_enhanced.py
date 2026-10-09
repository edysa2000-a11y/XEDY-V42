import pandas as pd
import numpy as np

def run_qwen_ai_enhanced_backtest():
    df = pd.read_csv("C:/Antigravity/Project/XEDY Mission Control/backend/scripts/xauusd_h1_week.csv")
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['date'] = df['datetime'].dt.date
    df['hour'] = df['datetime'].dt.hour

    # Indicators
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

    def get_session(h):
        if 0 <= h <= 6:
            return "ASIA"
        elif 7 <= h <= 11:
            return "LONDON"
        elif 12 <= h <= 20:
            return "NEW YORK"
        else:
            return "PACIFIC"

    df['session'] = df['hour'].apply(get_session)

    # Active period: Oct 01 to Oct 07
    df_active = df[df['datetime'] >= '2026-10-01 00:00:00'].copy().reset_index(drop=True)

    trades = []
    LOT_SIZE = 1.0  # 1 lot = $100 per pt

    for i in range(len(df_active) - 1):
        bar = df_active.iloc[i]
        future_window = df_active.iloc[i+1:min(i+5, len(df_active))]
        
        session = bar['session']
        c = bar['close']
        o = bar['open']
        h = bar['high']
        l = bar['low']
        ema9 = bar['ema9']
        ema21 = bar['ema21']
        ema50 = bar['ema50']
        rsi = bar['rsi14']
        atr = max(6.0, bar['atr14'])
        vol = bar['tick_volume']

        # Qwen Institutional AI Quality Gate Filters:
        # Rule 1: No trades in Pacific dead hours
        if session == "PACIFIC":
            continue

        # Rule 2: Filter out ultra-tight chop bars (candle range < 0.45 * ATR)
        if (h - l) < (atr * 0.45):
            continue

        # Rule 3: Qwen Deep Trend & Flow Vector
        ema_aligned_bull = (c > ema9 > ema21)
        ema_aligned_bear = (c < ema9 < ema21)
        
        # Mean-reversion trigger for ASIA session
        asia_overbought = (session == "ASIA" and rsi > 68 and (h - c) > (c - o))
        asia_oversold = (session == "ASIA" and rsi < 32 and (c - l) > (o - c))

        action = None
        confidence = 0

        if session == "ASIA":
            if asia_overbought or (ema_aligned_bear and rsi < 45):
                action = "SELL"
                confidence = 85
            elif asia_oversold or (ema_aligned_bull and rsi > 55):
                action = "BUY"
                confidence = 85
            elif ema_aligned_bull:
                action = "BUY"
                confidence = 80
            elif ema_aligned_bear:
                action = "SELL"
                confidence = 80
        elif session in ("LONDON", "NEW YORK"):
            # Strong momentum continuation
            if ema_aligned_bull and rsi >= 50:
                action = "BUY"
                confidence = 90
            elif ema_aligned_bear and rsi <= 50:
                action = "SELL"
                confidence = 90
            elif c > ema9 and rsi > 58:
                action = "BUY"
                confidence = 82
            elif c < ema9 and rsi < 42:
                action = "SELL"
                confidence = 82

        if not action:
            continue

        op = round(c, 2)
        
        # Qwen Dynamic Asymmetric TP/SL:
        # Stop loss placed at prior structural level or 0.85 ATR
        # TP1 at 1.25 ATR, with dynamic BEP at +0.7 ATR
        sl_dist = round(max(8.0, atr * 0.85), 2)
        tp_dist = round(max(14.0, atr * 1.45), 2)
        bep_dist = round(atr * 0.70, 2)

        if action == "BUY":
            sl = round(op - sl_dist, 2)
            tp = round(op + tp_dist, 2)
        else:
            sl = round(op + sl_dist, 2)
            tp = round(op - tp_dist, 2)

        hit_tp = False
        hit_sl = False
        hit_bep = False
        exit_price = op
        pnl_points = 0.0

        for _, f_bar in future_window.iterrows():
            if action == "BUY":
                # Check BEP trigger
                if f_bar['high'] >= op + bep_dist:
                    sl = op + 1.0 # lock in BEP + $1
                    hit_bep = True
                
                if f_bar['high'] >= tp:
                    hit_tp = True
                    exit_price = tp
                    pnl_points = tp_dist
                    break
                elif f_bar['low'] <= sl:
                    hit_sl = True
                    exit_price = sl
                    pnl_points = 1.0 if hit_bep else -sl_dist
                    break
            else: # SELL
                if f_bar['low'] <= op - bep_dist:
                    sl = op - 1.0 # lock in BEP + $1
                    hit_bep = True

                if f_bar['low'] <= tp:
                    hit_tp = True
                    exit_price = tp
                    pnl_points = tp_dist
                    break
                elif f_bar['high'] >= sl:
                    hit_sl = True
                    exit_price = sl
                    pnl_points = 1.0 if hit_bep else -sl_dist
                    break

        if not hit_tp and not hit_sl:
            final_c = future_window.iloc[-1]['close']
            exit_price = round(final_c, 2)
            pnl_points = round((exit_price - op) if action == "BUY" else (op - exit_price), 2)

        usd_pnl = round(pnl_points * 100.0 * LOT_SIZE, 2)
        result = "WIN" if pnl_points > 0 else "LOSS"

        trades.append({
            "datetime": bar['datetime'].strftime("%Y-%m-%d %H:%M"),
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

    print("\n================ QWEN AI ENHANCED HOURLY BACKTEST ================")
    print(f"Total Filtered Trades : {total}")
    print(f"Wins                  : {wins}")
    print(f"Losses                : {losses}")
    print(f"WINRATE               : {winrate:.1f}%")
    print(f"Total Net PnL (1 Lot) : ${net_pnl:,.2f}")
    print(f"Profit Factor         : {profit_factor}")
    print(f"Max Drawdown (1 Lot)  : ${max_dd_usd:,.2f}")

    print("\n================ SESSION PERFORMANCE ================")
    session_pnl = df_res.groupby('session').agg(
        trades=('result', 'count'),
        wins=('result', lambda x: (x == 'WIN').sum()),
        net_usd=('pnl_usd', 'sum')
    ).reset_index()
    session_pnl['winrate'] = (session_pnl['wins'] / session_pnl['trades'] * 100).round(1)
    print(session_pnl.to_string())

    df_res.to_csv("C:/Antigravity/Project/XEDY Mission Control/backend/scripts/qwen_ai_enhanced_results.csv", index=False)
    print("Saved to backend/scripts/qwen_ai_enhanced_results.csv")

if __name__ == "__main__":
    run_qwen_ai_enhanced_backtest()
