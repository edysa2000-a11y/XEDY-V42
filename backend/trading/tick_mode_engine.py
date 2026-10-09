import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("xedy.trading.tick_mode")
WIB = timezone(timedelta(hours=7))

class TickModeEngine:
    """
    XEDY AI — Institutional Multi-Timeframe TICK Mode Engine
    
    Rule & Mekanisme:
    1. Mengukur rasio Buy Ticks vs Sell Ticks across M1, M5, M15, M30, H1, H4, D1.
    2. Menghitung Tick Delta %: (Buy Ticks - Sell Ticks) / Total Ticks * 100.
    3. Multi-Timeframe Confluence:
       - HTF Bias: H1 / H4 / D1 Tick Direction
       - Intermediate Setup: M30 / M15 Tick Alignment
       - Trigger Execution: M5 / M15
    4. Sizing: 1.00 Lot ($100 per 1 poin USD XAUUSD).
    5. Proteksi: Dynamic TP (+10 pts), Hard SL (15 pts), Tick Exhaustion Exit (<2%), Trailing BEP (+5 pts).
    """

    TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "ticks"
        )

    def load_tf_data(self, tf: str) -> pd.DataFrame:
        file_path = os.path.join(self.data_dir, f"xauusd_{tf}.csv")
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            return df
        return pd.DataFrame()

    def get_latest_mtf_snapshot(self) -> dict:
        """
        Mengambil rekap jumlah tick buy & sell terkini di seluruh 7 timeframe (M1 s/d D1).
        """
        snapshot = {}
        for tf in self.TIMEFRAMES:
            df = self.load_tf_data(tf)
            if not df.empty:
                last_row = df.iloc[-1]
                snapshot[tf] = {
                    "total_ticks": int(last_row.get("total_ticks", 0)),
                    "buy_ticks": int(last_row.get("buy_ticks", 0)),
                    "sell_ticks": int(last_row.get("sell_ticks", 0)),
                    "delta_ticks": int(last_row.get("delta_ticks", 0)),
                    "delta_pct": round(float(last_row.get("delta_pct", 0.0)), 2),
                    "buy_pct": round(float(last_row.get("buy_pct", 50.0)), 2),
                    "sell_pct": round(float(last_row.get("sell_pct", 50.0)), 2),
                    "close_price": round(float(last_row.get("close", 0.0)), 2)
                }
        return snapshot

    def format_mtf_table_text(self) -> str:
        snapshot = self.get_latest_mtf_snapshot()
        if not snapshot:
            return "⚠️ Data tick timeframe belum tersedia."
            
        lines = [
            "📊 <b>XEDY AI — MULTI-TIMEFRAME TICK FLOW RADAR (7-TF)</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "<code>TF   │ BUY TICKS │ SELL TICKS│ DELTA % │ STATUS</code>",
            "─────┼───────────┼───────────┼─────────┼──────────"
        ]
        
        for tf in self.TIMEFRAMES:
            d = snapshot.get(tf)
            if d:
                tot = d["total_ticks"]
                b = d["buy_ticks"]
                s = d["sell_ticks"]
                dp = d["delta_pct"]
                sign = "+" if dp >= 0 else ""
                
                if dp >= 5.0: st = "🟢 BUY ZONE"
                elif dp <= -5.0: st = "🔴 SELL ZONE"
                elif abs(dp) < 2.0: st = "⚪ EXHAUSTED"
                else: st = "🟡 BALANCED"
                
                lines.append(f"<code>{tf:4s}│ {b:9,d} │ {s:9,d} │ {sign}{dp:5.1f}%  │</code> {st}")
                
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)
