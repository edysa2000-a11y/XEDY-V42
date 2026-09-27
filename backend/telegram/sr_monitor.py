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

    async def _send_photo(self, photo_bytes: bytes, caption: str = ""):
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        admin_id = self.admin_id or int(os.environ.get("TELEGRAM_ADMIN_ID", "0"))
        
        try:
            if self.bot and admin_id:
                from aiogram.types import BufferedInputFile
                input_file = BufferedInputFile(photo_bytes, filename="weekly_sr_monitor.png")
                await self.bot.send_photo(chat_id=admin_id, photo=input_file, caption=caption, parse_mode="HTML")
                logger.info("S/R Card Photo sent via aiogram.")
                return
            elif token and admin_id:
                await self._send_photo_http(token, admin_id, photo_bytes, caption)
                return
        except Exception as e:
            logger.warning(f"aiogram photo send failed: {e}. Trying urllib fallback...")
            if token and admin_id:
                await self._send_photo_http(token, admin_id, photo_bytes, caption)

    async def _send_photo_http(self, token: str, chat_id: int, photo_bytes: bytes, caption: str = ""):
        import urllib.request
        import uuid
        boundary = uuid.uuid4().hex
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        
        parts = []
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode("utf-8"))
        if caption:
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode("utf-8"))
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nHTML\r\n".encode("utf-8"))
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"weekly_sr.png\"\r\nContent-Type: image/png\r\n\r\n".encode("utf-8"))
        parts.append(photo_bytes)
        parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
        
        body = b"".join(parts)
        loop = asyncio.get_running_loop()
        def _do_post():
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=20.0) as resp:
                resp.read()
        try:
            await loop.run_in_executor(None, _do_post)
            logger.info("S/R Card Photo sent via urllib fallback.")
        except Exception as ex:
            logger.error(f"urllib Telegram photo send failed: {ex}")
            if caption:
                await self._send_safe(caption)

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

    def fetch_tradingview_prices(self) -> dict:
        import urllib.request
        import json
        url = "https://scanner.tradingview.com/global/scan"
        payload = {
            "symbols": {
                "tickers": ["OANDA:XAUUSD", "OANDA:USDJPY", "FX_IDC:XAUUSD", "FX:USDJPY"]
            },
            "columns": ["close", "bid", "ask"]
        }
        prices = {}
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data.get("data", []):
                    ticker = item.get("s", "")
                    vals = item.get("d", [])
                    if len(vals) >= 3:
                        close, bid, ask = vals[0], vals[1], vals[2]
                        mid = (bid + ask) / 2.0 if (bid and ask and bid > 0 and ask > 0) else close
                        if "XAUUSD" in ticker and "XAUUSD" not in prices:
                            prices["XAUUSD"] = {"close": close, "bid": bid, "ask": ask, "mid": mid, "source": f"TradingView ({ticker})"}
                        elif "USDJPY" in ticker and "USDJPY" not in prices:
                            prices["USDJPY"] = {"close": close, "bid": bid, "ask": ask, "mid": mid, "source": f"TradingView ({ticker})"}
        except Exception as e:
            logger.warning(f"TradingView price fetch exception: {e}")
        return prices

    async def check_all_symbols(self, now_wib: datetime):
        loop = asyncio.get_running_loop()
        tv_prices = await loop.run_in_executor(None, self.fetch_tradingview_prices)
        
        is_weekend = now_wib.weekday() in [5, 6] # 5=Saturday, 6=Sunday

        for symbol, cfg in self.CONFIG.items():
            bid = 0.0
            ask = 0.0
            mid = 0.0
            source_info = "TradingView"

            # Primary: TradingView Live Price
            if symbol in tv_prices:
                tv_data = tv_prices[symbol]
                bid = float(tv_data["bid"]) if tv_data["bid"] else float(tv_data["close"])
                ask = float(tv_data["ask"]) if tv_data["ask"] else float(tv_data["close"])
                mid = round(float(tv_data["mid"]), cfg["digits"])
                source_info = tv_data["source"]
            else:
                # Fallback: MetaTrader 5 Ticks / Rates
                if mt5.initialize():
                    aliases = [symbol]
                    if symbol == "XAUUSD":
                        aliases.extend(["GOLD", "XAUUSD.a", "XAUUSDm", "XAUUSD.i"])
                    elif symbol == "USDJPY":
                        aliases.extend(["USDJPY.a", "USDJPYm", "USDJPY.i"])

                    tick = None
                    found_symbol = symbol
                    for alias in aliases:
                        t = mt5.symbol_info_tick(alias)
                        if t and t.bid > 0:
                            tick = t
                            found_symbol = alias
                            break

                    if tick and tick.bid > 0:
                        bid = float(tick.bid)
                        ask = float(tick.ask)
                    else:
                        rates = mt5.copy_rates_from_pos(found_symbol, mt5.TIMEFRAME_M1, 0, 1)
                        if rates is not None and len(rates) > 0:
                            c_price = float(rates[-1][4])
                            bid = c_price
                            ask = c_price
                        else:
                            await self._handle_data_error(symbol, "TRADINGVIEW & MT5 PRICE UNAVAILABLE")
                            continue
                    mid = round((bid + ask) / 2.0, cfg["digits"])
                    source_info = "MT5 Fallback"
                else:
                    await self._handle_data_error(symbol, "TRADINGVIEW & MT5 UNAVAILABLE")
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
        digits = self.CONFIG[symbol]["digits"]
        
        if status == "NEAR_SUPPORT":
            dist = round(mid - supp, digits)
            dist_pct = round((mid - supp) / supp * 100.0, 2)
            msg = (
                f"🚨 <b>S/R ALERT — NEAR SUPPORT</b>\n\n"
                f"<b>{symbol}</b>\n"
                f"Price: {mid:.{digits}f}\n"
                f"🔒 Support: {supp:.{digits}f}\n"
                f"Distance: +{dist:.{digits}f}\n"
                f"Distance: +{dist_pct:.2f}%\n\n"
                f"⚠️ <b>PRICE NEAR SUPPORT</b>"
            )
        elif status == "NEAR_RESISTANCE":
            dist = round(res - mid, digits)
            dist_pct = round((res - mid) / res * 100.0, 2)
            msg = (
                f"🚨 <b>S/R ALERT — NEAR RESISTANCE</b>\n\n"
                f"<b>{symbol}</b>\n"
                f"Price: {mid:.{digits}f}\n"
                f"🔒 Resistance: {res:.{digits}f}\n"
                f"Distance: +{dist:.{digits}f}\n"
                f"Distance: +{dist_pct:.2f}%\n\n"
                f"⚠️ <b>PRICE NEAR RESISTANCE</b>"
            )
        elif status == "BREAKOUT":
            msg = (
                f"🚨🚨 <b>BREAKOUT ALERT</b>\n\n"
                f"<b>{symbol}</b>\n"
                f"Price: {mid:.{digits}f}\n"
                f"🔒 Resistance: {res:.{digits}f}\n\n"
                f"<b>BREAKOUT RESISTANCE</b>"
            )
        elif status == "BREAKDOWN":
            msg = (
                f"🚨🚨 <b>BREAKDOWN ALERT</b>\n\n"
                f"<b>{symbol}</b>\n"
                f"Price: {mid:.{digits}f}\n"
                f"🔒 Support: {supp:.{digits}f}\n\n"
                f"<b>BREAKDOWN SUPPORT</b>"
            )
        else: # NORMAL (No alert needed when returning to NORMAL)
            return "NONE"

        await self._send_safe(msg)
        return f"SENT ({status})"

    async def send_hourly_report(self, now_wib: datetime):
        blocks = []
        
        for symbol, cfg in self.CONFIG.items():
            data = self.last_price_data.get(symbol)
            digits = cfg["digits"]
            
            if data:
                live_price = f"{data['mid']:.{digits}f}"
                dist_s = f"{data['dist_s']:+.{digits}f}"
                dist_r = f"{data['dist_r']:+.{digits}f}"
                st = data["status"]
            else:
                live_price = "N/A"
                dist_s = "N/A"
                dist_r = "N/A"
                st = "NO DATA"
                
            block = (
                f"<b>{symbol}</b>\n"
                f"• Live: {live_price}\n"
                f"• 🔒 S: {cfg['support']:.{digits}f}\n"
                f"• Distance S: {dist_s}\n"
                f"• 🔒 R: {cfg['resistance']:.{digits}f}\n"
                f"• Distance R: {dist_r}\n"
                f"• Status: {st}"
            )
            blocks.append(block)

        report_msg = (
            f"📊 <b>S/R HOURLY REPORT</b>\n\n" +
            "\n\n".join(blocks)
        )
        
        # Generate & Send Visual S/R Card Photo
        try:
            photo_bytes = self.generate_current_photo_card(now_wib)
            await self._send_photo(photo_bytes, caption=report_msg)
        except Exception as e:
            logger.error(f"Failed to send hourly S/R photo: {e}")
            await self._send_safe(report_msg)

        logger.info(f"Hourly S/R Market Report sent.")

    def generate_current_photo_card(self, now_wib: datetime = None) -> bytes:
        from backend.telegram.sr_image_generator import generate_sr_card_bytes
        if now_wib is None:
            now_wib = datetime.now(WIB)
            
        x_data = self.last_price_data.get("XAUUSD", {})
        j_data = self.last_price_data.get("USDJPY", {})
        
        x_p = x_data.get("mid", 4285.00) if x_data else 4285.00
        x_st = x_data.get("status", "NORMAL") if x_data else "NORMAL"
        
        j_p = j_data.get("mid", 157.29) if j_data else 157.29
        j_st = j_data.get("status", "NORMAL") if j_data else "NORMAL"
        
        return generate_sr_card_bytes(
            xau_price=x_p,
            xau_support=self.CONFIG["XAUUSD"]["support"],
            xau_resistance=self.CONFIG["XAUUSD"]["resistance"],
            xau_status=x_st,
            jpy_price=j_p,
            jpy_support=self.CONFIG["USDJPY"]["support"],
            jpy_resistance=self.CONFIG["USDJPY"]["resistance"],
            jpy_status=j_st,
            now_wib=now_wib
        )

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
