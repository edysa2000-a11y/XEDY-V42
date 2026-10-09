import pandas as pd
import numpy as np

def run_qwen_session_anchor_backtest():
    df = pd.read_csv("C:/Antigravity/Project/XEDY Mission Control/backend/scripts/xauusd_h1_week.csv")
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['date'] = df['datetime'].dt.date
    df['hour'] = df['datetime'].dt.hour

    # Moving averages & ATR
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['tr0'] = abs(df['high'] - df['low'])
    df['tr1'] = abs(df['high'] - df['close'].shift(1))
    df['tr2'] = abs(df['low'] - df['close'].shift(1))
    df['atr14'] = df[['tr0', 'tr1', 'tr2']].max(axis=1).rolling(14).mean().bfill()

    LOT_SIZE = 1.0 # 1.00 Lot = $100 per point

    trades = []

    # Daily session boundaries
    # Asia Key Hour: 03:00 - 05:00 UTC (10:00 - 12:00 WIB)
    # London Key Hour: 08:00 - 10:00 UTC (15:00 - 17:00 WIB)
    # New York Key Hour: 13:00 - 15:00 UTC (20:00 - 22:00 WIB)

    days = df[df['datetime'] >= '2026-10-01 00:00:00']['date'].unique()

    for d in days:
        d_bars = df[df['date'] == d].copy().reset_index(drop=True)
        if len(d_bars) < 10: continue

        # 1. ASIA SESSION TRADE (Window 02:00 - 05:00 UTC)
        asia_bars = d_bars[(d_bars['hour'] >= 2) & (d_bars['hour'] <= 5)]
        if len(asia_bars) > 0:
            best_bar = asia_bars.iloc[-1]
            o, h, l, c = best_bar['open'], best_bar['high'], best_bar['low'], best_bar['close']
            atr = best_bar['atr14']
            
            # Mean reversion from extremes
            if c < d_bars.iloc[0]['open'] - 5.0 or (c < best_bar['ema21'] and (c - l) > (h - c)):
                act = "BUY"
                op = round(c, 2)
                sl = round(op - max(10.0, atr * 0.9), 2)
                tp = round(op + max(15.0, atr * 1.5), 2)
            else:
                act = "SELL"
                op = round(c, 2)
                sl = round(op + max(10.0, atr * 0.9), 2)
                tp = round(op - max(15.0, atr * 1.5), 2)

            trades.append({"date": d, "session": "ASIA (10:00 WIB)", "hour": best_bar['hour'], "action": act, "op": op, "sl": sl, "tp": tp, "bar_idx": best_bar.name})

        # 2. LONDON SESSION TRADE (Window 08:00 - 10:00 UTC)
        london_bars = d_bars[(d_bars['hour'] >= 8) & (d_bars['hour'] <= 10)]
        if len(london_bars) > 0:
            best_bar = london_bars.iloc[-1]
            o, h, l, c = best_bar['open'], best_bar['high'], best_bar['low'], best_bar['close']
            atr = best_bar['atr14']
            # Trend continuation
            act = "BUY" if best_bar['ema9'] > best_bar['ema21'] else "SELL"
            op = round(c, 2)
            sl_dist = max(12.0, atr * 0.9)
            tp_dist = max(22.0, atr * 1.6)
            sl = round(op - sl_dist if act == "BUY" else op + sl_dist, 2)
            tp = round(op + tp_dist if act == "BUY" else op - tp_dist, 2)
            trades.append({"date": d, "session": "LONDON (16:00 WIB)", "hour": best_bar['hour'], "action": act, "op": op, "sl": sl, "tp": tp, "bar_idx": best_bar.name})

        # 3. NEW YORK SESSION TRADE (Window 13:00 - 16:00 UTC)
        ny_bars = d_bars[(d_bars['hour'] >= 13) & (d_bars['hour'] <= 16)]
        if len(ny_bars) > 0:
            best_bar = ny_bars.iloc[-1]
            o, h, l, c = best_bar['open'], best_bar['high'], best_bar['low'], best_bar['close']
            atr = best_bar['atr14']
            act = "BUY" if best_bar['ema9'] > best_bar['ema21'] and c > best_bar['ema21'] else "SELL"
            op = round(c, 2)
            sl_dist = max(14.0, atr * 0.9)
            tp_dist = max(26.0, atr * 1.8)
            sl = round(op - sl_dist if act == "BUY" else op + sl_dist, 2)
            tp = round(op + tp_dist if act == "BUY" else op - tp_dist, 2)
            trades.append({"date": d, "session": "NEW YORK (21:00 WIB)", "hour": best_bar['hour'], "action": act, "op": op, "sl": sl, "tp": tp, "bar_idx": best_bar.name})

    print(f"Total session anchor trades planned: {len(trades)}")

    # Evaluate outcomes forward in time
    results = []
    for t in trades:
        # get bars after this trade
        entry_idx = df[(df['date'] == t['date']) & (df['hour'] == t['hour'])].index[0]
        future_bars = df.iloc[entry_idx+1:entry_idx+15] # up to 15 hours holding
        
        hit_tp = False
        hit_sl = False
        exit_p = t['op']
        pnl_pts = 0.0

        for _, f in future_bars.iterrows():
            if t['action'] == "BUY":
                if f['high'] >= t['tp']:
                    hit_tp = True
                    exit_p = t['tp']
                    pnl_pts = round(t['tp'] - t['op'], 2)
                    break
                elif f['low'] <= t['sl']:
                    hit_sl = True
                    exit_p = t['sl']
                    pnl_pts = round(t['sl'] - t['op'], 2)
                    break
            else:
                if f['low'] <= t['tp']:
                    hit_tp = True
                    exit_p = t['tp']
                    pnl_pts = round(t['op'] - t['tp'], 2)
                    break
                elif f['high'] >= t['sl']:
                    hit_sl = True
                    exit_p = t['sl']
                    pnl_pts = round(t['op'] - t['sl'], 2)
                    break

        if not hit_tp and not hit_sl and len(future_bars) > 0:
            final_c = future_bars.iloc[-1]['close']
            exit_p = round(final_c, 2)
            pnl_pts = round(exit_p - t['op'] if t['action'] == "BUY" else t['op'] - exit_p, 2)

        res = "WIN" if pnl_pts > 0 else "LOSS"
        usd = round(pnl_pts * 100.0 * LOT_SIZE, 2)

        results.append({
            "date": t['date'],
            "session": t['session'],
            "action": t['action'],
            "op": t['op'],
            "tp": t['tp'],
            "sl": t['sl'],
            "exit": exit_p,
            "pnl_pts": pnl_pts,
            "pnl_usd": usd,
            "result": res
        })

    df_res = pd.DataFrame(results)
    print("\nRESULTS SUMMARY:")
    print(df_res[['date', 'session', 'action', 'op', 'tp', 'sl', 'result', 'pnl_usd']].to_string())

    wins = len(df_res[df_res['result'] == 'WIN'])
    total = len(df_res)
    winrate = (wins / total) * 100
    net_usd = df_res['pnl_usd'].sum()
    print(f"\nTotal: {total} | Wins: {wins} | Losses: {total-wins} | Winrate: {winrate:.1f}% | Net USD: ${net_usd:,.2f}")

if __name__ == "__main__":
    run_qwen_session_anchor_backtest()
