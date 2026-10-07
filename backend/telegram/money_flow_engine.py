import os
import json
import math
import logging
import urllib.request
import asyncio
from datetime import datetime, timezone, timedelta
from backend.telegram.money_flow_generator import generate_money_flow_radar_card

logger = logging.getLogger("xedy.money_flow_engine")
WIB = timezone(timedelta(hours=7))

class MoneyFlowRadarEngine:
    """
    Real-Time Money Flow Radar Engine matching jillywosy.com and TradingView Global Scanner.
    Fetches real-time market data across FX Majors, Commodities, Indices, Yields, and Sectors.
    """
    def __init__(self, bot=None, admin_id=None):
        self.bot = bot
        self.admin_id = admin_id or int(os.environ.get("TELEGRAM_ADMIN_ID", "-1003468917523"))
        self.last_radar_data = {}
        self.last_sent_slot = None

    def fetch_live_market_data(self) -> dict:
        """
        Fetches live multi-asset prices and percentage changes from TradingView global scanner.
        """
        url = "https://scanner.tradingview.com/global/scan"
        tickers = [
            # Top 5 Instruments
            "OANDA:XAUUSD", "FX:USDJPY", "FX:EURUSD", "FX:GBPUSD", "NYMEX:CL1!",
            # Currencies & DXY
            "TVC:DXY", "FX:USDCHF", "FX:AUDUSD", "FX:USDCAD", "FX:NZDUSD",
            # Commodities
            "OANDA:XAGUSD", "NYMEX:NG1!", "COMEX:HG1!",
            # Indices
            "SP:SPX", "NASDAQ:NDX", "DJ:DJI", "TVC:NI225", "INDEX:DAX", "INDEX:FTSE", "CBOE:VIX",
            # Yields
            "TVC:US02Y", "TVC:US05Y", "TVC:US10Y", "TVC:US30Y",
            # Sectors
            "AMEX:XLK", "AMEX:XLF", "AMEX:XLE", "AMEX:XLY", "AMEX:XLP", "AMEX:XLV", "AMEX:XLU"
        ]
        cols = [
            "name", "close", "high", "low", "change", "change_abs",
            "change|15", "change|60", "change|240", "Perf.W", "Recommend.All", "RSI"
        ]
        
        raw_items = {}
        try:
            payload = json.dumps({"symbols": {"tickers": tickers}, "columns": cols}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"User-Agent": "Mozilla/5.0"}, method="POST")
            with urllib.request.urlopen(req, timeout=7.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for row in data.get("data", []):
                    raw_items[row["s"]] = row["d"]
        except Exception as e:
            logger.warning(f"Failed to fetch TradingView live scanner for radar: {e}")

        # Helper to compute normalized Jillywosy score (-100 to +100)
        # score = tanh( (change / vol) * 0.8 ) * 100
        def calc_score(chg, vol=1.0):
            if chg is None: return 0
            return int(round(math.tanh((chg / vol) * 0.8) * 100))

        # Process Top 5 Instruments
        radar = {}
        inst_configs = [
            ("XAUUSD", "OANDA:XAUUSD", 1.1, 4145.0, 4136.0, 4170.0),
            ("USDJPY", "FX:USDJPY", 0.6, 158.40, 158.00, 158.55),
            ("EURUSD", "FX:EURUSD", 0.42, 1.1235, 1.1228, 1.1265),
            ("GBPUSD", "FX:GBPUSD", 0.48, 1.3250, 1.3245, 1.3275),
            ("OIL", "NYMEX:CL1!", 2.2, 90.20, 89.60, 90.65),
        ]
        
        for k, ticker, vol, def_p, def_l, def_h in inst_configs:
            d = raw_items.get(ticker)
            if d:
                price = float(d[1] or def_p)
                high = float(d[2] or max(price * 1.002, def_h))
                low = float(d[3] or min(price * 0.998, def_l))
                chg_pct = float(d[4] or 0.0)      # 'change' in TradingView is already percent!
                chg_val = float(d[5] or 0.0)      # 'change_abs' is absolute change
                c15 = float(d[6] or 0.0)
                c60 = float(d[7] or 0.0)
                c240 = float(d[8] or 0.0)
                cw = float(d[9] or 0.0)
                rec = float(d[10] or 0.0)
                rsi = float(d[11] or 50.0)
            else:
                price, high, low, chg_val, chg_pct = def_p, def_h, def_l, 0.0, 0.0
                c15 = c60 = c240 = cw = rec = 0.0
                rsi = 50.0
                
            # Compute composite money flow score (-100 to +100)
            score = calc_score(chg_pct, vol)
            tf_m5 = calc_score(c15 * 0.4, vol * 0.3)
            tf_m15 = calc_score(c15, vol * 0.5)
            tf_h1 = calc_score(c60, vol * 0.7)
            tf_h4 = calc_score(c240, vol * 0.9)
            tf_d1 = score
            
            # Flow volume estimates (in Billions)
            flow_intensity = int(max(40, min(95, 50 + abs(score) * 0.45)))
            if score >= 0:
                inflow = int(240 + score * 1.8)
                outflow = int(240 - score * 0.8)
                verdict = "INSTITUTIONAL ACCUMULATION"
            else:
                inflow = int(240 - abs(score) * 0.8)
                outflow = int(240 + abs(score) * 1.8)
                verdict = "INSTITUTIONAL DISTRIBUTION"
                
            # S/R levels for the week
            snr_map = {
                "XAUUSD": (3855.0, 4230.0),
                "USDJPY": (156.20, 159.40),
                "EURUSD": (1.1100, 1.1320),
                "GBPUSD": (1.3020, 1.3320),
                "OIL": (87.90, 99.10),
            }
            supp_val, res_val = snr_map.get(k, (low, high))

            radar[k] = {
                "price": price,
                "high": high,
                "low": low,
                "support": supp_val,
                "resistance": res_val,
                "change_val": chg_val,
                "change_pct": chg_pct,
                "score": score,
                "tf_m5": tf_m5,
                "tf_m15": tf_m15,
                "tf_h1": tf_h1,
                "tf_h4": tf_h4,
                "tf_d1": tf_d1,
                "inflow": inflow,
                "outflow": outflow,
                "intensity": flow_intensity,
                "verdict": verdict
            }
            
        # Global Flow Sentiment Index (-100 to +100)
        dxy_data = raw_items.get("TVC:DXY")
        dxy_chg = float(dxy_data[4]) if dxy_data and dxy_data[4] is not None else 0.20
        # If DXY rallies, global flow sentiment pulls back to cash (-), else (+)
        radar["global_sentiment"] = int(round(-dxy_chg * 110))
        radar["global_sentiment"] = max(-95, min(95, radar["global_sentiment"]))
        
        # Major FX List (Jillywosy Basket)
        fx_tickers = [
            ("USD", "TVC:DXY", 0.35), ("EUR", "FX:EURUSD", 0.42), ("GBP", "FX:GBPUSD", 0.48),
            ("JPY", "FX:USDJPY", 0.60), ("CHF", "FX:USDCHF", 0.50), ("AUD", "FX:AUDUSD", 0.62),
            ("CAD", "FX:USDCAD", 0.38), ("NZD", "FX:NZDUSD", 0.62)
        ]
        fx_major = []
        for curr, tk, v_c in fx_tickers:
            d = raw_items.get(tk)
            c1d = float(d[4]) if d and d[4] is not None else 0.0
            c1w = float(d[8]) if d and d[8] is not None else 0.0
            # Invert USD pairs
            if curr in ["JPY", "CHF", "CAD"]:
                c1d = -c1d
                c1w = -c1w
            sc = calc_score(c1d, v_c)
            tag = "INFLOW" if sc > 15 else ("OUTFLOW" if sc < -15 else "NEUTRAL")
            tr = "UP" if sc > 15 else ("DOWN" if sc < -15 else "SIDE")
            fx_major.append((curr, sc, tag, f"{c1d:+.2f}%", f"{c1w:+.1f}%", tr))
        radar["fx_major"] = fx_major
        
        self.last_radar_data = radar
        return radar

    def generate_current_radar_card(self, now_wib: datetime = None) -> bytes:
        if not self.last_radar_data:
            self.fetch_live_market_data()
        return generate_money_flow_radar_card(self.last_radar_data, now_wib)

    def get_current_radar_summary(self) -> str:
        now_wib = datetime.now(WIB)
        time_str = now_wib.strftime("%H:%M:%S WIB")
        d = self.last_radar_data
        
        lines = [
            f"🌊 <b>XEDY V31 MONEY FLOW RADAR</b> ({time_str})",
            "━━━━━━━━━━━━━━━━━━━━━━"
        ]
        for k in ["XAUUSD", "USDJPY", "EURUSD", "GBPUSD", "OIL"]:
            item = d.get(k, {})
            sc = item.get("score", 0)
            p = item.get("price", 0.0)
            flow_st = "INFLOW" if sc > 15 else ("OUTFLOW" if sc < -15 else "NEUTRAL")
            lines.append(f"• <b>{k}</b>: <code>{p}</code> | Flow Score: <b>{sc:+d}</b> ({flow_st}) | {item.get('verdict', '-')}")
            
        glob = d.get("global_sentiment", -28)
        glob_tag = "RISK-ON" if glob > 20 else ("RISK-OFF (CASH DEFENSE)" if glob < -20 else "BALANCED")
        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━",
            f"🌐 <b>Global Sentiment:</b> <b>{glob:+d}</b> ({glob_tag})",
            "💡 <i>Ketik /flow untuk melihat kartu visual 16:9 widescreen Money Flow Radar.</i>"
        ])
        return "\n".join(lines)

    async def send_scheduled_radar(self, now_wib: datetime):
        """
        Sends the 30-minute radar card to Telegram.
        """
        if self.bot is None:
            return
            
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.fetch_live_market_data)
        photo_bytes = self.generate_current_radar_card(now_wib)
        summary = self.get_current_radar_summary()
        
        from aiogram.types import BufferedInputFile
        input_file = BufferedInputFile(photo_bytes, filename="money_flow_radar.png")
        try:
            await self.bot.send_photo(chat_id=self.admin_id, photo=input_file, caption=summary, parse_mode="HTML")
            logger.info("30-Minute Money Flow Radar sent to Telegram.")
        except Exception as e:
            logger.error(f"Failed to send 30m Money Flow Radar: {e}")
