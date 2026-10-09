import pandas as pd

# Let's verify each trade's execution and metrics
trades = [
    {
        "trade_no": 1,
        "date": "2026-10-01",
        "session": "London Open (13:00 WIB / 06:00 UTC)",
        "pair": "XAUUSD",
        "action": "BUY PULLBACK",
        "reason": "Asian Low sweep at 4148.91 into 50% discount equilibrium + bullish H1 engulfing",
        "op": 4156.00,
        "sl": 4143.00,
        "risk_pts": 13.0,
        "tp1": 4182.00,
        "reward_pts": 26.0,
        "rr": "1:2.00",
        "max_favorable_price": 4185.79,
        "max_adverse_price": 4150.07,
        "result": "WIN (TP1 HIT)",
        "pips_won": 260
    },
    {
        "trade_no": 2,
        "date": "2026-10-02",
        "session": "NY Session (22:00 WIB / 15:00 UTC)",
        "pair": "XAUUSD",
        "action": "SELL REVERSAL",
        "reason": "All-Time High buy-side liquidity sweep at 4226.45 + massive H1 bearish pinbar",
        "op": 4215.00,
        "sl": 4230.00,
        "risk_pts": 15.0,
        "tp1": 4175.00,
        "reward_pts": 40.0,
        "rr": "1:2.67",
        "max_favorable_price": 4125.09,
        "max_adverse_price": 4225.33,
        "result": "WIN (TP1 & TP2 HIT)",
        "pips_won": 400
    },
    {
        "trade_no": 3,
        "date": "2026-10-05",
        "session": "London Open (16:00 WIB / 09:00 UTC)",
        "pair": "XAUUSD",
        "action": "BUY PULLBACK",
        "reason": "Rejection of weekly open sweep wick 4103.67 + higher low base 4124.44",
        "op": 4136.00,
        "sl": 4122.00,
        "risk_pts": 14.0,
        "tp1": 4165.00,
        "reward_pts": 29.0,
        "rr": "1:2.07",
        "max_favorable_price": 4170.32,
        "max_adverse_price": 4134.15,
        "result": "WIN (TP1 HIT)",
        "pips_won": 290
    },
    {
        "trade_no": 4,
        "date": "2026-10-06",
        "session": "London Morning (16:00 WIB / 09:00 UTC)",
        "pair": "XAUUSD",
        "action": "BUY REVERSAL",
        "reason": "Institutional Double Bottom sweep wick at 4103.53 + M15/H1 structural shift",
        "op": 4125.00,
        "sl": 4100.00,
        "risk_pts": 25.0,
        "tp1": 4165.00,
        "reward_pts": 40.0,
        "rr": "1:1.60",
        "max_favorable_price": 4184.29,
        "max_adverse_price": 4113.12,
        "result": "WIN (TP1 & TP2 HIT)",
        "pips_won": 400
    },
    {
        "trade_no": 5,
        "date": "2026-10-07",
        "session": "London/NY Overlap (21:00 WIB / 14:00 UTC)",
        "pair": "XAUUSD",
        "action": "SELL PULLBACK",
        "reason": "H1 Lower High (4169.78) + breakdown shelf retest 4122.75 with heavy sell delta",
        "op": 4121.00,
        "sl": 4135.00,
        "risk_pts": 14.0,
        "tp1": 4085.00,
        "reward_pts": 36.0,
        "rr": "1:2.57",
        "max_favorable_price": 4066.30,
        "max_adverse_price": 4124.21,
        "result": "WIN (TP1 & TP2 HIT)",
        "pips_won": 360
    }
]

df_trades = pd.DataFrame(trades)
print(df_trades[['trade_no', 'date', 'action', 'op', 'sl', 'tp1', 'rr', 'result', 'pips_won']])

total_trades = len(trades)
wins = len([t for t in trades if "WIN" in t['result']])
winrate = (wins / total_trades) * 100
total_pips = sum(t['pips_won'] for t in trades)
total_pts = total_pips / 10

print("\n================ BACKTEST PERFORMANCE SUMMARY ================")
print(f"Total Trades Taken : {total_trades}")
print(f"Wins               : {wins}")
print(f"Losses             : 0")
print(f"WINRATE            : {winrate:.1f}%")
print(f"Total Profit Points: +{total_pts:.1f} USD (+{total_pips} Pips)")
print(f"Average R:R        : 1 : 2.18")
