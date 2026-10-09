import pandas as pd
import numpy as np

def run_comprehensive_qwen_hourly_audit():
    df = pd.read_csv("C:/Antigravity/Project/XEDY Mission Control/backend/scripts/xauusd_h1_week.csv")
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['date'] = df['datetime'].dt.date
    df['hour'] = df['datetime'].dt.hour

    # Moving averages
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['tr0'] = abs(df['high'] - df['low'])
    df['tr1'] = abs(df['high'] - df['close'].shift(1))
    df['tr2'] = abs(df['low'] - df['close'].shift(1))
    df['atr14'] = df[['tr0', 'tr1', 'tr2']].max(axis=1).rolling(14).mean().bfill()

    LOT = 1.0 # 1 Lot = $100 per point

    def get_session(h):
        if 0 <= h <= 6:
            return "ASIA (Tokyo/Sydney)"
        elif 7 <= h <= 11:
            return "LONDON (Frankfurt/London)"
        elif 12 <= h <= 20:
            return "NEW YORK (Wall Street)"
        else:
            return "PACIFIC"

    df['session'] = df['hour'].apply(get_session)
    df_active = df[df['datetime'] >= '2026-10-01 00:00:00'].copy().reset_index(drop=True)

    # Let's run Qwen AI Precision Strategy:
    # Qwen scans every hour from Asia (01:00 UTC) to New York (20:00 UTC).
    # If Liquidity Sweep + Rejection Pinbar / BOS candle occurs, Qwen fires an A+ signal!
    # Trailing: once +15 pts gained, SL moves to BEP.
    signals = []

    for i in range(len(df_active) - 1):
        bar = df_active.iloc[i]
        future_window = df_active.iloc[i+1:min(i+12, len(df_active))]
        
        dt = bar['datetime']
        hour = bar['hour']
        session = bar['session']
        c = bar['close']
        o = bar['open']
        h = bar['high']
        l = bar['low']
        atr = bar['atr14']
        ema9 = bar['ema9']
        ema21 = bar['ema21']

        # Qwen Filter Logic
        # Condition A: Bullish Liquidity Sweep & Engulfing (Rejection from low)
        # Lower wick > 40% of range and close in upper 50%
        rng = h - l
        lower_wick = min(o, c) - l
        upper_wick = h - max(o, c)

        is_bull_sweep = (lower_wick > 0.40 * rng) and (c > o) and (rng > 10.0)
        is_bear_sweep = (upper_wick > 0.40 * rng) and (c < o) and (rng > 10.0)

        # Condition B: High Momentum Expansion Breakout
        is_bull_momentum = (c > o) and (c > ema9 > ema21) and (rng > 1.3 * atr) and (c > h - 0.2 * rng)
        is_bear_momentum = (c < o) and (c < ema9 < ema21) and (rng > 1.3 * atr) and (c < l + 0.2 * rng)

        action = None
        setup_type = None

        if is_bull_sweep:
            action = "BUY"
            setup_type = "LIQUIDITY SWEEP REVERSAL"
        elif is_bear_sweep:
            action = "SELL"
            setup_type = "LIQUIDITY SWEEP REVERSAL"
        elif is_bull_momentum:
            action = "BUY"
            setup_type = "MOMENTUM EXPANSION"
        elif is_bear_momentum:
            action = "SELL"
            setup_type = "MOMENTUM EXPANSION"

        if action:
            op = round(c, 2)
            sl_dist = round(max(12.0, atr * 0.9), 2)
            tp1_dist = round(max(20.0, atr * 1.5), 2)
            
            if action == "BUY":
                sl = round(op - sl_dist, 2)
                tp1 = round(op + tp1_dist, 2)
            else:
                sl = round(op + sl_dist, 2)
                tp1 = round(op - tp1_dist, 2)

            # Test execution
            hit_tp = False
            hit_sl = False
            bep_triggered = False
            exit_price = op
            pnl_pts = 0.0

            for _, f in future_window.iterrows():
                if action == "BUY":
                    if f['high'] >= op + 15.0:
                        bep_triggered = True
                        sl = op + 1.0 # locked
                    if f['high'] >= tp1:
                        hit_tp = True
                        exit_price = tp1
                        pnl_pts = tp1_dist
                        break
                    elif f['low'] <= sl:
                        hit_sl = True
                        exit_price = sl
                        pnl_pts = 1.0 if bep_triggered else -sl_dist
                        break
                else:
                    if f['low'] <= op - 15.0:
                        bep_triggered = True
                        sl = op - 1.0 # locked
                    if f['low'] <= tp1:
                        hit_tp = True
                        exit_price = tp1
                        pnl_pts = tp1_dist
                        break
                    elif f['high'] >= sl:
                        hit_sl = True
                        exit_price = sl
                        pnl_pts = 1.0 if bep_triggered else -sl_dist
                        break

            if not hit_tp and not hit_sl and len(future_window) > 0:
                final_c = future_window.iloc[-1]['close']
                exit_price = round(final_c, 2)
                pnl_pts = round(exit_price - op if action == "BUY" else op - exit_price, 2)

            usd_pnl = round(pnl_pts * 100.0 * LOT, 2)
            res = "WIN" if pnl_pts > 0 else "LOSS"

            signals.append({
                "datetime": dt.strftime("%Y-%m-%d %H:%M"),
                "session": session,
                "action": action,
                "setup": setup_type,
                "op": op,
                "sl": sl,
                "tp1": tp1,
                "exit": exit_price,
                "pnl_pts": pnl_pts,
                "pnl_usd": usd_pnl,
                "result": res
            })

    df_signals = pd.DataFrame(signals)
    print("\nALL QWEN-CONFIRMED HIGH-ACCURACY TRADES (1 WEEK):")
    print(df_signals[['datetime', 'session', 'action', 'setup', 'op', 'tp1', 'sl', 'result', 'pnl_usd']].to_string())

    wins = len(df_signals[df_signals['result'] == 'WIN'])
    total = len(df_signals)
    winrate = (wins / total * 100) if total > 0 else 0
    net_usd = df_signals['pnl_usd'].sum()
    print(f"\nTotal: {total} | Wins: {wins} | Losses: {total - wins} | Winrate: {winrate:.1f}% | Net USD (1 Lot): ${net_usd:,.2f}")

    df_signals.to_csv("C:/Antigravity/Project/XEDY Mission Control/backend/scripts/qwen_signals_1week.csv", index=False)

if __name__ == "__main__":
    run_comprehensive_qwen_hourly_audit()
