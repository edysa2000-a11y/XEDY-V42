import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
import MetaTrader5 as mt5

logger = logging.getLogger("xedy.telegram.sr_monitor")
WIB = timezone(timedelta(hours=7))

class SRMonitorEngine:
    """
    AI Real-Time Support & Resistance Monitoring Agent.
    Monitors XAUUSD and USDJPY live MT5 prices every 1 minute.
    Enforces state-machine anti-spam, 2-reading breakout confirmations,
    high priority alerts, and hourly market reports in WIB timezone.
    """
    
    # LEVEL S/R BERLAKU: 27 September 2026 - 4 Oktober 2026
    CONFIG = {
        "XAUUSD": {
            "support": 4220.0,
            "resistance": 4580.0,
            "near_pct": 0.005, # 0.50%
            "digits": 2
        },
        "USDJPY": {
            "support": 152.80,
            "resistance": 158.30,
            "near_pct": 0.003, # 0.30%
            "digits": 2
        }
    }

    def __init__(self, bot=None, admin_id=None):
        self.bot = bot
        self.admin_id = admin_id or int(os.environ.get("TELEGRAM_ADMIN_ID", "0"))
        self._running = False
        self._monitor_task = None
        
        # State Tracking
        self.current_state = {s: "NORMAL" for s in self.CONFIG}
        self.raw_outside_count = {s: {"BREAKOUT": 0, "BREAKDOWN": 0} for s in self.CONFIG}
        self.last_price_data = {}
        self.last_error_sent = {s: 0.0 for s in self.CONFIG}
        self.last_hourly_hour = -1

    async def start(self, bot=None, admin_id=None):
        if bot:
            self.bot = bot
        if admin_id:
            self.admin_id = admin_id
            
        logger.info("Memulai AI Real-Time Support & Resistance Monitor...")
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
        logger.info("AI Real-Time Support & Resistance Monitor dihentikan.")

    async def _send_safe(self, text: str):
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        admin_id = self.admin_id or int(os.environ.get("TELEGRAM_ADMIN_ID", "0"))
        
        try:
            if self.bot and admin_id:
                await self.bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
            elif token and admin_id:
                await self._send_http(token, admin_id, text)
            else:
                logger.warning(f"[TELEGRAM NOT SENT] {text[:60]}...")
        except Exception as e:
            logger.warning(f"aiogram bot send failed: {e}. Trying urllib fallback...")
            if token and admin_id:
                await self._send_http(token, admin_id, text)

    async def _send_http(self, token: str, chat_id: int, text: str):
        import urllib.request
        import json
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        loop = asyncio.get_running_loop()
        def _do_post():
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                resp.read()
        try:
            await loop.run_in_executor(None, _do_post)
        except Exception as ex:
            logger.error(f"urllib Telegram fallback failed: {ex}")

    async def _monitor_loop(self):
        while self._running:
            try:
                now_wib = datetime.now(WIB)
                
                # Perform 1-minute S/R check for all configured symbols
                await self.check_all_symbols(now_wib)
                
                # Check for Hourly Report trigger (on every new hour)
                if self.last_hourly_hour != now_wib.hour:
                    if self.last_hourly_hour != -1:
                        await self.send_hourly_report(now_wib)
                    self.last_hourly_hour = now_wib.hour
                    
            except Exception as e:
                logger.error(f"Error in SRMonitorEngine loop: {e}", exc_info=True)
                
            await asyncio.sleep(60) # Pengecekan setiap 1 menit

    async def check_all_symbols(self, now_wib: datetime):
        if not mt5.initialize():
            logger.error("MT5 Initialization failed in S/R Monitor Engine.")
            for sym in self.CONFIG:
                await self._handle_data_error(sym, "MT5 INITIALIZATION FAILED")
            return

        is_weekend = now_wib.weekday() in [5, 6] # 5=Saturday, 6=Sunday

        for symbol, cfg in self.CONFIG.items():
            # Try symbol aliases (e.g. XAUUSD, GOLD, XAUUSD.a, XAUUSDm, USDJPY, USDJPY.a, USDJPYm)
            aliases = [symbol]
            if symbol == "XAUUSD":
                aliases.extend(["GOLD", "XAUUSD.a", "XAUUSDm", "XAUUSD.i", "XAUUSD_i"])
            elif symbol == "USDJPY":
                aliases.extend(["USDJPY.a", "USDJPYm", "USDJPY.i", "USDJPY_i"])

            tick = None
            found_symbol = symbol
            for alias in aliases:
                t = mt5.symbol_info_tick(alias)
                if t and t.bid > 0:
                    tick = t
                    found_symbol = alias
                    break

            bid = 0.0
            ask = 0.0
            if tick and tick.bid > 0:
                bid = float(tick.bid)
                ask = float(tick.ask)
            else:
                # Try getting last closed M1 rate if tick stream is unavailable
                rates = mt5.copy_rates_from_pos(found_symbol, mt5.TIMEFRAME_M1, 0, 1)
                if rates is not None and len(rates) > 0:
                    c_price = float(rates[-1][4])
                    bid = c_price
                    ask = c_price
                else:
                    await self._handle_data_error(symbol, "MT5 PRICE UNAVAILABLE")
                    continue

            mid = round((bid + ask) / 2.0, cfg["digits"])
            
            # Check price freshness (Enforce >300s stale check ONLY on weekdays when market is OPEN)
            now_ts = datetime.now().timestamp()
            if not is_weekend and tick and tick.time > 0 and (now_ts - tick.time) > 300:
                await self._handle_data_error(symbol, "MT5 PRICE STALE (>300s)")
                continue

            # Calculate distances
            supp = cfg["support"]
            res = cfg["resistance"]
            dist_s = round(mid - supp, cfg["digits"])
            dist_r = round(res - mid, cfg["digits"])
            
            # Calculate raw state
            raw_state = "NORMAL"
            
            if mid > res:
                self.raw_outside_count[symbol]["BREAKOUT"] += 1
                self.raw_outside_count[symbol]["BREAKDOWN"] = 0
                if self.raw_outside_count[symbol]["BREAKOUT"] >= 2:
                    raw_state = "BREAKOUT"
                else:
                    raw_state = self.current_state[symbol] # Hold state until confirmed
            elif mid < supp:
                self.raw_outside_count[symbol]["BREAKDOWN"] += 1
                self.raw_outside_count[symbol]["BREAKOUT"] = 0
                if self.raw_outside_count[symbol]["BREAKDOWN"] >= 2:
                    raw_state = "BREAKDOWN"
                else:
                    raw_state = self.current_state[symbol] # Hold state until confirmed
            else:
                # Reset breakout/breakdown consecutive counters when price returns inside
                self.raw_outside_count[symbol]["BREAKOUT"] = 0
                self.raw_outside_count[symbol]["BREAKDOWN"] = 0
                
                # Check Near thresholds
                # Near Support: within near_pct above support
                near_s_bound = supp + (supp * cfg["near_pct"])
                # Near Resistance: within near_pct below resistance
                near_r_bound = res - (res * cfg["near_pct"])
                
                if mid >= near_r_bound:
                    raw_state = "NEAR_RESISTANCE"
                elif mid <= near_s_bound:
                    raw_state = "NEAR_SUPPORT"
                else:
                    raw_state = "NORMAL"

            prev_state = self.current_state[symbol]
            alert_sent = "NONE"

            # STATE MACHINE ANTI-SPAM: Alert ONLY on state change
            if raw_state != prev_state:
                self.current_state[symbol] = raw_state
                alert_sent = await self.send_instant_alert(symbol, mid, supp, res, dist_s, dist_r, raw_state, now_wib)
                
            # Store price data for hourly report & logging
            self.last_price_data[symbol] = {
                "bid": bid,
                "ask": ask,
                "mid": mid,
                "supp": supp,
                "res": res,
                "dist_s": dist_s,
                "dist_r": dist_r,
                "status": self.current_state[symbol],
                "time": now_wib
            }

            # Logging Section (Section 12)
            time_str = now_wib.strftime("%Y-%m-%d %H:%M:%S WIB")
            logger.info(
                f"S/R LOG | {time_str} | {symbol} | Price={mid:.2f} (Bid={bid:.2f}, Ask={ask:.2f}) | "
                f"S={supp} | R={res} | DistS={dist_s:+.2f} | DistR={dist_r:+.2f} | "
                f"Status={self.current_state[symbol]} | PrevStatus={prev_state} | Alert={alert_sent}"
            )

    async def _handle_data_error(self, symbol: str, error_msg: str):
        now_ts = datetime.now().timestamp()
        # Throttle data error alerts to max 1 per 15 minutes per symbol to prevent spam
        if now_ts - self.last_error_sent.get(symbol, 0) > 900:
            self.last_error_sent[symbol] = now_ts
            msg = (
                f"⚠️ <b>DATA ERROR</b>\n\n"
                f"Instrument:\n<b>{symbol}</b>\n\n"
                f"Status:\n<b>{error_msg}</b>"
            )
            await self._send_safe(msg)

    async def send_instant_alert(self, symbol: str, mid: float, supp: float, res: float, dist_s: float, dist_r: float, status: str, now_wib: datetime) -> str:
        time_str = now_wib.strftime("%H:%M:%S WIB")
        digits = self.CONFIG[symbol]["digits"]
        
        status_formatted = ""
        is_high_priority = False
        
        if status == "NEAR_SUPPORT":
            status_formatted = "🔴 NEAR SUPPORT"
        elif status == "NEAR_RESISTANCE":
            status_formatted = "🟢 NEAR RESISTANCE"
        elif status == "BREAKOUT":
            status_formatted = "🚨 BREAKOUT"
            is_high_priority = True
        elif status == "BREAKDOWN":
            status_formatted = "⚠️ BREAKDOWN"
            is_high_priority = True
        else: # NORMAL (No alert needed when returning to NORMAL)
            return "NONE"

        header = "🚨🚨 <b>HIGH PRIORITY ALERT</b>" if is_high_priority else "🚨 <b>S/R ALERT</b>"

        msg = (
            f"{header}\n\n"
            f"<b>{symbol}</b>\n"
            f"Price: {mid:.{digits}f}\n"
            f"Support: {supp:.{digits}f}\n"
            f"Resistance: {res:.{digits}f}\n\n"
            f"Status:\n{status_formatted}\n\n"
            f"Distance S: {dist_s:+.{digits}f}\n"
            f"Distance R: {dist_r:+.{digits}f}\n\n"
            f"Time: {time_str}"
        )
        await self._send_safe(msg)
        return f"SENT ({status})"

    async def send_hourly_report(self, now_wib: datetime):
        time_str = now_wib.strftime("%H:%M WIB")
        
        blocks = []
        alert_statuses = []
        
        for symbol, cfg in self.CONFIG.items():
            data = self.last_price_data.get(symbol)
            digits = cfg["digits"]
            
            if data:
                live_price = f"{data['mid']:.{digits}f}"
                dist_s = f"{data['dist_s']:+.{digits}f}"
                dist_r = f"{data['dist_r']:+.{digits}f}"
                st = data["status"]
                
                if st == "NEAR_SUPPORT":
                    st_fmt = "🔴 NEAR SUPPORT"
                elif st == "NEAR_RESISTANCE":
                    st_fmt = "🟢 NEAR RESISTANCE"
                elif st == "BREAKOUT":
                    st_fmt = "🚨 BREAKOUT"
                elif st == "BREAKDOWN":
                    st_fmt = "⚠️ BREAKDOWN"
                else:
                    st_fmt = "🟢 NORMAL"
            else:
                live_price = "N/A"
                dist_s = "N/A"
                dist_r = "N/A"
                st = "NO DATA"
                st_fmt = "⚠️ NO DATA"
                
            icon = "🟡" if symbol == "XAUUSD" else "💴"
            block = (
                f"{icon} <b>{symbol}</b>\n\n"
                f"💰 Live: {live_price}\n\n"
                f"S: <b>{cfg['support']:.{digits}f}</b>\n"
                f"R: <b>{cfg['resistance']:.{digits}f}</b>\n\n"
                f"Distance S: {dist_s}\n"
                f"Distance R: {dist_r}\n\n"
                f"Status: {st_fmt}"
            )
            blocks.append(block)
            alert_statuses.append(f"{symbol}:\n{st}")

        report_msg = (
            f"📊 <b>HOURLY S/R MARKET REPORT</b>\n\n"
            f"⏰ Time: {time_str}\n\n"
            f"━━━━━━━━━━━━━━\n\n" +
            "\n\n━━━━━━━━━━━━━━\n\n".join(blocks) +
            f"\n\n━━━━━━━━━━━━━━\n\n"
            f"### ALERT STATUS\n\n" +
            "\n".join(alert_statuses)
        )
        await self._send_safe(report_msg)
        logger.info(f"Hourly S/R Market Report sent at {time_str}.")

    def get_current_status_summary(self) -> str:
        now_wib = datetime.now(WIB)
        time_str = now_wib.strftime("%H:%M:%S WIB")
        summary_lines = [f"📊 <b>S/R MONITOR STATUS</b> ({time_str})\n"]
        for symbol, cfg in self.CONFIG.items():
            data = self.last_price_data.get(symbol)
            if data:
                summary_lines.append(
                    f"• <b>{symbol}</b>: Price=${data['mid']} | S={cfg['support']} | R={cfg['resistance']} | Status=<b>{data['status']}</b>"
                )
            else:
                summary_lines.append(f"• <b>{symbol}</b>: Waiting for MT5 price tick...")
        return "\n".join(summary_lines)
