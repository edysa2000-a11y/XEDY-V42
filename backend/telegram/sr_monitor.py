import asyncio
import logging
import os
import json
import urllib.request
import uuid
from datetime import datetime, timezone, timedelta
import MetaTrader5 as mt5
from backend.telegram.sr_image_generator import generate_sr_card_bytes

logger = logging.getLogger("xedy.telegram.sr_monitor")
WIB = timezone(timedelta(hours=7))

class SRMonitorEngine:
    """
    AI Real-Time Support & Resistance Monitoring Engine for 4 Key Assets:
    1. GOLD (XAUUSD)
    2. EURUSD (EUR/USD)
    3. OIL (WTI CRUDE)
    4. USDJPY (USD/JPY)
    
    Features:
    - Real-time price scanning via TradingView Global Scanner + MT5 fallback.
    - Hourly reports sent to Telegram once every 1 hour with visual Bloomberg-style card.
    - INSTANT ALERT: When live price hits/touches SNR (Support/Resistance/Breakout/Breakdown),
      immediately generates and sends the card to Telegram without waiting for the hour.
    - Anti-spam state machine with cooldown.
    """
    
    CONFIG = {
        "XAUUSD": {
            "name": "GOLD",
            "subtitle": "XAUUSD",
            "orb_color": (255, 195, 0),
            "support": 3855.0,
            "resistance": 4230.0,
            "near_pct": 0.003, # 0.3% near/touch threshold
            "digits": 2
        },
        "EURUSD": {
            "name": "EURUSD",
            "subtitle": "EUR/USD",
            "orb_color": (0, 140, 255),
            "support": 1.1100,
            "resistance": 1.1320,
            "near_pct": 0.002, # 0.2%
            "digits": 4
        },
        "OIL": {
            "name": "OIL",
            "subtitle": "WTI CRUDE",
            "orb_color": (60, 65, 75),
            "support": 87.90,
            "resistance": 99.10,
            "near_pct": 0.005, # 0.5%
            "digits": 2
        },
        "USDJPY": {
            "name": "USDJPY",
            "subtitle": "USD/JPY",
            "orb_color": (160, 50, 255),
            "support": 156.20,
            "resistance": 159.40,
            "near_pct": 0.003, # 0.3%
            "digits": 2
        }
    }

    def __init__(self, bot=None, admin_id=None):
        self.bot = bot
        self.admin_id = admin_id or int(os.environ.get("TELEGRAM_ADMIN_ID", "-1003468917523"))
        self._running = False
        self._monitor_task = None
        
        # State Tracking
        self.current_state = {s: "WAIT" for s in self.CONFIG}
        self.raw_outside_count = {s: {"BREAKOUT": 0, "BREAKDOWN": 0} for s in self.CONFIG}
        self.last_price_data = {}
        self.last_error_sent = {s: 0.0 for s in self.CONFIG}
        self.last_alert_sent_time = {s: 0.0 for s in self.CONFIG}
        self.last_hourly_hour = -1

    async def start(self, bot=None, admin_id=None):
        if bot:
            self.bot = bot
        if admin_id:
            self.admin_id = admin_id
            
        logger.info("Memulai AI Real-Time Support & Resistance Monitor (4 Pasang Mata Uang/Komoditas)...")
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
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        loop = asyncio.get_running_loop()
        def _do_post():
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}, method="POST")
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
                input_file = BufferedInputFile(photo_bytes, filename="snr_monitor_card.png")
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
        boundary = uuid.uuid4().hex
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        
        parts = []
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode("utf-8"))
        if caption:
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode("utf-8"))
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nHTML\r\n".encode("utf-8"))
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"snr_card.png\"\r\nContent-Type: image/png\r\n\r\n".encode("utf-8"))
        parts.append(photo_bytes)
        parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
        
        body = b"".join(parts)
        loop = asyncio.get_running_loop()
        def _do_post():
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "Mozilla/5.0"},
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
        # On boot, send an initial welcome card if desired
        logger.info("S/R Monitor Engine active. Checking every 30 seconds...")
        while self._running:
            try:
                now_wib = datetime.now(WIB)
                
                # 1. Fetch live prices & check SNR touch / breakout
                await self.check_all_symbols(now_wib)
                
                # 2. Hourly Report Trigger (1 jam sekali pada awal jam baru)
                if self.last_hourly_hour != now_wib.hour:
                    if self.last_hourly_hour != -1:
                        await self.send_hourly_report(now_wib)
                    else:
                        # Send first report on startup
                        await self.send_hourly_report(now_wib)
                    self.last_hourly_hour = now_wib.hour
                    
            except Exception as e:
                logger.error(f"Error in SRMonitorEngine loop: {e}", exc_info=True)
                
            await asyncio.sleep(30) # Interval pengecekan setiap 30 detik

    def fetch_tradingview_prices(self) -> dict:
        url = "https://scanner.tradingview.com/global/scan"
        payload = {
            "symbols": {
                "tickers": [
                    "OANDA:XAUUSD", "FX_IDC:XAUUSD",
                    "FX:EURUSD", "OANDA:EURUSD",
                    "NYMEX:CL1!", "TVC:USOIL",
                    "FX:USDJPY", "OANDA:USDJPY"
                ]
            },
            "columns": ["close", "bid", "ask", "change", "change_abs", "high", "low"]
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
                    if len(vals) >= 5:
                        close, bid, ask, chg_pct, chg_abs = vals[0], vals[1], vals[2], vals[3], vals[4]
                        mid = (bid + ask) / 2.0 if (bid and ask and bid > 0 and ask > 0) else close
                        
                        if "XAUUSD" in ticker and "XAUUSD" not in prices:
                            prices["XAUUSD"] = {"price": mid, "change_val": chg_abs or 0.0, "change_pct": chg_pct or 0.0, "source": f"TV ({ticker})"}
                        elif "EURUSD" in ticker and "EURUSD" not in prices:
                            prices["EURUSD"] = {"price": mid, "change_val": chg_abs or 0.0, "change_pct": chg_pct or 0.0, "source": f"TV ({ticker})"}
                        elif ("CL1!" in ticker or "USOIL" in ticker) and "OIL" not in prices:
                            prices["OIL"] = {"price": mid, "change_val": chg_abs or 0.0, "change_pct": chg_pct or 0.0, "source": f"TV ({ticker})"}
                        elif "USDJPY" in ticker and "USDJPY" not in prices:
                            prices["USDJPY"] = {"price": mid, "change_val": chg_abs or 0.0, "change_pct": chg_pct or 0.0, "source": f"TV ({ticker})"}
        except Exception as e:
            logger.warning(f"TradingView price fetch exception: {e}")
        return prices

    async def check_all_symbols(self, now_wib: datetime):
        loop = asyncio.get_running_loop()
        tv_prices = await loop.run_in_executor(None, self.fetch_tradingview_prices)

        for symbol, cfg in self.CONFIG.items():
            price = 0.0
            chg_val = 0.0
            chg_pct = 0.0
            source_info = "TradingView"

            if symbol in tv_prices:
                tv_data = tv_prices[symbol]
                price = round(float(tv_data["price"]), cfg["digits"])
                chg_val = float(tv_data["change_val"])
                chg_pct = float(tv_data["change_pct"])
                source_info = tv_data["source"]
            else:
                # MT5 Fallback
                if mt5.initialize():
                    alias = "XAUUSD" if symbol == "XAUUSD" else "EURUSD" if symbol == "EURUSD" else "USDJPY" if symbol == "USDJPY" else None
                    if alias:
                        tick = mt5.symbol_info_tick(alias)
                        if tick and tick.bid > 0:
                            price = round((tick.bid + tick.ask) / 2.0, cfg["digits"])
                            rates = mt5.copy_rates_from_pos(alias, mt5.TIMEFRAME_D1, 0, 1)
                            if rates is not None and len(rates) > 0:
                                d_open = float(rates[-1][1])
                                chg_val = price - d_open
                                chg_pct = (chg_val / d_open) * 100.0 if d_open > 0 else 0.0
                            source_info = "MT5"
                        else:
                            rates = mt5.copy_rates_from_pos(alias, mt5.TIMEFRAME_M1, 0, 1)
                            if rates is not None and len(rates) > 0:
                                price = round(float(rates[-1][4]), cfg["digits"])
                                source_info = "MT5 Rate"

            if price <= 0:
                continue

            supp = cfg["support"]
            res = cfg["resistance"]
            near_pct = cfg.get("near_pct", 0.003)

            # Calculate %SNR
            if res > supp:
                pct_snr = (price - supp) / (res - supp) * 100.0
            else:
                pct_snr = 50.0

            # Determine State & Status
            # 1. Breakout / Breakdown (confirmed over 2 readings)
            raw_state = "WAIT"
            status_label = "WAIT"
            is_touch_event = False

            if price > res:
                self.raw_outside_count[symbol]["BREAKOUT"] += 1
                self.raw_outside_count[symbol]["BREAKDOWN"] = 0
                if self.raw_outside_count[symbol]["BREAKOUT"] >= 2:
                    raw_state = "BREAKOUT"
                    status_label = "BREAKOUT"
                    is_touch_event = True
                else:
                    raw_state = self.current_state[symbol]
                    status_label = "WAIT"
            elif price < supp:
                self.raw_outside_count[symbol]["BREAKDOWN"] += 1
                self.raw_outside_count[symbol]["BREAKOUT"] = 0
                if self.raw_outside_count[symbol]["BREAKDOWN"] >= 2:
                    raw_state = "BREAKDOWN"
                    status_label = "BREAKDOWN"
                    is_touch_event = True
                else:
                    raw_state = self.current_state[symbol]
                    status_label = "WAIT"
            else:
                self.raw_outside_count[symbol]["BREAKOUT"] = 0
                self.raw_outside_count[symbol]["BREAKDOWN"] = 0
                
                # Check touch / near thresholds
                dist_to_res = res - price
                dist_to_supp = price - supp
                
                # Touch condition: within near_pct of level (e.g. 0.3%) or extreme %SNR
                if price >= res * (1.0 - near_pct) or pct_snr >= 95.0:
                    raw_state = "TOUCH_RESISTANCE"
                    status_label = "REVERSAL"
                    is_touch_event = True
                elif price <= supp * (1.0 + near_pct) or pct_snr <= 5.0:
                    raw_state = "TOUCH_SUPPORT"
                    status_label = "BUY"
                    is_touch_event = True
                elif pct_snr >= 78.0:
                    raw_state = "NEAR_RESISTANCE"
                    status_label = "REVERSAL"
                elif pct_snr <= 22.0:
                    raw_state = "NEAR_SUPPORT"
                    status_label = "BUY"
                else:
                    raw_state = "NORMAL"
                    status_label = "WAIT"

            prev_state = self.current_state[symbol]

            # Save data
            self.last_price_data[symbol] = {
                "name": cfg["name"],
                "subtitle": cfg["subtitle"],
                "orb_color": cfg["orb_color"],
                "price": price,
                "change_val": chg_val,
                "change_pct": chg_pct,
                "digits": cfg["digits"],
                "support": supp,
                "resistance": res,
                "pct_snr": pct_snr,
                "status": status_label,
                "raw_state": raw_state,
                "source": source_info,
                "time": now_wib
            }

            # TRIGGER INSTANT ALERT JIKA MENGENAI SNR
            now_ts = datetime.now().timestamp()
            cooldown_expired = (now_ts - self.last_alert_sent_time.get(symbol, 0)) > 1800 # 30 min cooldown
            
            # Send immediately if:
            # 1. State changed into a touch/breakout event
            # 2. Or is a touch event and cooldown has passed
            if is_touch_event:
                if raw_state != prev_state or cooldown_expired:
                    self.current_state[symbol] = raw_state
                    self.last_alert_sent_time[symbol] = now_ts
                    await self.send_instant_touch_alert(symbol, raw_state, status_label, price, supp, res, pct_snr, now_wib)
            else:
                self.current_state[symbol] = raw_state

    async def send_instant_touch_alert(self, symbol: str, state: str, status_label: str, price: float, supp: float, res: float, pct_snr: float, now_wib: datetime):
        """
        Sends an INSTANT visual card & urgent notification when price touches or breaks SNR.
        """
        cfg = self.CONFIG[symbol]
        digits = cfg["digits"]
        time_str = now_wib.strftime("%H:%M:%S WIB")
        
        if state == "TOUCH_RESISTANCE":
            event_title = "🚨 <b>S/R ALERT — MENGENAI RESISTANCE!</b>"
            level_name = "RESISTANCE"
            target_level = res
            dist = res - price
            tactical = "⚠️ <i>Harga menguji batas atas Resistance. Pantau potensi REVERSAL / SELL Rejection!</i>"
        elif state == "TOUCH_SUPPORT":
            event_title = "🚨 <b>S/R ALERT — MENGENAI SUPPORT!</b>"
            level_name = "SUPPORT"
            target_level = supp
            dist = price - supp
            tactical = "🎯 <i>Harga menyentuh batas bawah Support. Pantau potensi BUY / Demand Bounce!</i>"
        elif state == "BREAKOUT":
            event_title = "⚡🚨 <b>BREAKOUT ALERT — TEMBUS RESISTANCE!</b>"
            level_name = "BREAKOUT R"
            target_level = res
            dist = price - res
            tactical = "🚀 <i>Momentum kuat menembus Resistance. Waspada kelanjutan reli ke level berikutnya.</i>"
        elif state == "BREAKDOWN":
            event_title = "⚡🚨 <b>BREAKDOWN ALERT — TEMBUS SUPPORT!</b>"
            level_name = "BREAKDOWN S"
            target_level = supp
            dist = supp - price
            tactical = "🔻 <i>Harga tembus di bawah Support. Waspada percepatan tekanan jual.</i>"
        else:
            return

        caption = (
            f"{event_title}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 <b>{cfg['name']} ({cfg['subtitle']})</b>\n"
            f"• 💰 <b>Live Price:</b> <code>{price:,.{digits}f}</code>\n"
            f"• 🎯 <b>Level {level_name}:</b> <code>{target_level:,.{digits}f}</code>\n"
            f"• 📏 <b>Jarak Level:</b> {dist:+.{digits}f} (%SNR: {pct_snr:.1f}%)\n"
            f"• 🏷️ <b>Status Sinyal:</b> <b>{status_label}</b>\n"
            f"• ⏱️ <b>Waktu:</b> {time_str}\n\n"
            f"{tactical}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        try:
            photo_bytes = self.generate_current_photo_card()
            await self._send_photo(photo_bytes, caption=caption)
            logger.info(f"Instant SNR touch alert photo sent for {symbol} ({state})")
        except Exception as e:
            logger.error(f"Failed to send instant touch photo: {e}")
            await self._send_safe(caption)

    async def send_hourly_report(self, now_wib: datetime):
        """
        Sends the scheduled 1-hour report with the latest 4-pair visual SNR card.
        """
        time_str = now_wib.strftime("%d %b %Y • %H:00 WIB")
        
        summary_rows = []
        for symbol, cfg in self.CONFIG.items():
            data = self.last_price_data.get(symbol)
            digits = cfg["digits"]
            if data:
                p = data["price"]
                st = data["status"]
                pct = data["pct_snr"]
                summary_rows.append(f"• <b>{cfg['name']}</b>: <code>{p:,.{digits}f}</code> ({pct:.1f}%) → <b>{st}</b>")
            else:
                summary_rows.append(f"• <b>{cfg['name']}</b>: <i>Syncing...</i>")

        report_caption = (
            f"📊 <b>S/R HOURLY MONITOR REPORT</b>\n"
            f"🕒 <b>{time_str}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(summary_rows) + "\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <i>Update otomatis setiap 1 jam & langsung kirim notifikasi jika harga mengenai SNR.</i>"
        )

        try:
            photo_bytes = self.generate_current_photo_card()
            await self._send_photo(photo_bytes, caption=report_caption)
            logger.info("Hourly S/R 4-pair report card sent to Telegram.")
        except Exception as e:
            logger.error(f"Failed to send hourly report card: {e}")
            await self._send_safe(report_caption)

    def generate_current_photo_card(self, now_wib: datetime = None) -> bytes:
        """
        Generates the 4-pair visual card PNG bytes matching user's blueprint.
        """
        data_list = []
        for symbol, cfg in self.CONFIG.items():
            d = self.last_price_data.get(symbol)
            if d:
                data_list.append({
                    "name": cfg["name"],
                    "subtitle": cfg["subtitle"],
                    "orb_color": cfg["orb_color"],
                    "price": d["price"],
                    "change_val": d.get("change_val", 0.0),
                    "change_pct": d.get("change_pct", 0.0),
                    "digits": cfg["digits"],
                    "support": cfg["support"],
                    "resistance": cfg["resistance"],
                    "status": d.get("status", "WAIT"),
                })
            else:
                # Default placeholder if not yet ticked
                data_list.append({
                    "name": cfg["name"],
                    "subtitle": cfg["subtitle"],
                    "orb_color": cfg["orb_color"],
                    "price": cfg["support"] + (cfg["resistance"] - cfg["support"]) * 0.5,
                    "change_val": 0.0,
                    "change_pct": 0.0,
                    "digits": cfg["digits"],
                    "support": cfg["support"],
                    "resistance": cfg["resistance"],
                    "status": "WAIT",
                })
        return generate_sr_card_bytes(data_list)

    def get_current_status_summary(self) -> str:
        now_wib = datetime.now(WIB)
        time_str = now_wib.strftime("%H:%M:%S WIB")
        summary_lines = [f"📊 <b>XEDY MASTER S/R MONITOR</b> ({time_str})\n━━━━━━━━━━━━━━━━━━━━━━"]
        for symbol, cfg in self.CONFIG.items():
            d = self.last_price_data.get(symbol)
            digits = cfg["digits"]
            if d:
                summary_lines.append(
                    f"• <b>{cfg['name']} ({cfg['subtitle']})</b>: <code>{d['price']:,.{digits}f}</code>\n"
                    f"  S: {cfg['support']:.{digits}f} | R: {cfg['resistance']:.{digits}f} | %SNR: <b>{d['pct_snr']:.1f}%</b> | Status: <b>{d['status']}</b>"
                )
            else:
                summary_lines.append(f"• <b>{cfg['name']}</b>: Menunggu sinkronisasi harga...")
        summary_lines.append("━━━━━━━━━━━━━━━━━━━━━━\n<i>Ketik /sr untuk refresh kartu visual.</i>")
        return "\n".join(summary_lines)
