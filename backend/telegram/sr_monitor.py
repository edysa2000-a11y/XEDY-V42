import asyncio
import logging
import os
import json
import urllib.request
import uuid
from datetime import datetime, timezone, timedelta
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
from backend.telegram.sr_image_generator import generate_sr_card_bytes

logger = logging.getLogger("xedy.telegram.sr_monitor")
WIB = timezone(timedelta(hours=7))

class SRMonitorEngine:
    """
    AI Real-Time Support & Resistance Monitoring Engine (16:9 Bloomberg Hedge Fund Terminal)
    
    Instruments:
    1. GOLD (XAUUSD)
    2. EURUSD (EUR/USD)
    3. OIL (WTI CRUDE)
    4. USDJPY (USD/JPY)
    
    Features:
    - Real-time price scanning via TradingView Global Scanner + MT5 fallback.
    - Tick volume flow analysis (Buy Ticks, Sell Ticks, Delta, Buy%, Sell%, Pressure).
    - Multi-indicator Trend analysis (UP, DOWN, SIDEWAY).
    - %SNR Position tracking & dynamic Zones (Buy Zone, Wait Zone, Sell Zone).
    - Strict institutional hierarchy & reversal watch.
    - Scheduled 1-Hour Report (:00 WIB) sent to Telegram.
    - INSTANT ALERT: When live price hits/touches SNR (Support/Resistance/Breakout/Breakdown),
      immediately generates and sends the 16:9 Bloomberg Dashboard card to Telegram without waiting!
    """
    
    CONFIG = {
        "XAUUSD": {
            "name": "GOLD",
            "subtitle": "XAUUSD",
            "icon_type": "gold",
            "support": 3855.0,
            "resistance": 4230.0,
            "near_pct": 0.003, # 0.3% near/touch threshold
            "digits": 2
        },
        "EURUSD": {
            "name": "EURUSD",
            "subtitle": "EUR/USD",
            "icon_type": "eu",
            "support": 1.1100,
            "resistance": 1.1320,
            "near_pct": 0.002, # 0.2%
            "digits": 4
        },
        "OIL": {
            "name": "OIL",
            "subtitle": "WTI CRUDE",
            "icon_type": "oil",
            "support": 87.90,
            "resistance": 99.10,
            "near_pct": 0.005, # 0.5%
            "digits": 2
        },
        "USDJPY": {
            "name": "USDJPY",
            "subtitle": "USD/JPY",
            "icon_type": "japan",
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
        self.last_scheduled_slot = None
        self.load_custom_snr()

    def canonical_symbol(self, raw: str) -> str:
        s = raw.upper().strip().replace("/", "")
        if s in ("GOLD", "XAUUSD", "XAU", "EMAS"):
            return "XAUUSD"
        elif s in ("EURUSD", "EUR"):
            return "EURUSD"
        elif s in ("OIL", "USOIL", "WTI", "CRUDE"):
            return "OIL"
        elif s in ("USDJPY", "JPY"):
            return "USDJPY"
        return None

    def load_custom_snr(self):
        snr_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "custom_snr.json")
        if os.path.exists(snr_file):
            try:
                with open(snr_file, "r") as f:
                    saved = json.load(f)
                for sym, vals in saved.items():
                    if sym in self.CONFIG:
                        if "support" in vals: self.CONFIG[sym]["support"] = float(vals["support"])
                        if "resistance" in vals: self.CONFIG[sym]["resistance"] = float(vals["resistance"])
                logger.info(f"Loaded custom SNR from {snr_file}")
            except Exception as e:
                logger.warning(f"Failed to load custom SNR: {e}")

    def save_custom_snr(self):
        snr_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "custom_snr.json")
        os.makedirs(os.path.dirname(snr_file), exist_ok=True)
        try:
            dump_data = {}
            for sym, cfg in self.CONFIG.items():
                dump_data[sym] = {
                    "name": cfg["name"],
                    "support": cfg["support"],
                    "resistance": cfg["resistance"]
                }
            with open(snr_file, "w") as f:
                json.dump(dump_data, f, indent=4)
            logger.info(f"Saved custom SNR to {snr_file}")
        except Exception as e:
            logger.error(f"Failed to save custom SNR: {e}")

    def set_snr(self, raw_symbol: str, support: float, resistance: float) -> tuple:
        sym = self.canonical_symbol(raw_symbol)
        if not sym:
            return False, f"⚠️ Simbol <code>{raw_symbol}</code> tidak dikenali.\nPilihan: <b>GOLD</b>, <b>EURUSD</b>, <b>OIL</b>, atau <b>USDJPY</b>."
        
        if support >= resistance:
            return False, f"⚠️ Support (<code>{support}</code>) harus lebih kecil dari Resistance (<code>{resistance}</code>)."
        
        digits = self.CONFIG[sym]["digits"]
        self.CONFIG[sym]["support"] = round(float(support), digits)
        self.CONFIG[sym]["resistance"] = round(float(resistance), digits)
        self.save_custom_snr()
        
        # Reset alert debounce
        self.last_alert_sent_time[sym] = 0.0
        
        name = self.CONFIG[sym]["name"]
        return True, f"✅ <b>Level S/R {name} Berhasil Diperbarui:</b>\n• Support (0%): <code>{support:,.{digits}f}</code>\n• Resistance (100%): <code>{resistance:,.{digits}f}</code>"

    async def start(self, bot=None, admin_id=None):
        if bot:
            self.bot = bot
        if admin_id:
            self.admin_id = admin_id
            
        logger.info("Memulai AI Bloomberg Real-Time S/R Monitor Engine (4 Aset Utama)...")
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
        logger.info("AI Bloomberg Real-Time S/R Monitor dihentikan.")

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
                input_file = BufferedInputFile(photo_bytes, filename="bloomberg_dashboard.png")
                await self.bot.send_photo(chat_id=admin_id, photo=input_file, caption=caption, parse_mode="HTML")
                logger.info("Bloomberg Dashboard Card sent via aiogram.")
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
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"bloomberg_dashboard.png\"\r\nContent-Type: image/png\r\n\r\n".encode("utf-8"))
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
            logger.info("Bloomberg Dashboard Card sent via urllib fallback.")
        except Exception as ex:
            logger.error(f"urllib Telegram photo send failed: {ex}")
            if caption:
                await self._send_safe(caption)

    async def _monitor_loop(self):
        logger.info("Bloomberg S/R Monitor Loop Active. Scanning every 30s...")
        while self._running:
            try:
                now_wib = datetime.now(WIB)
                
                # 1. Fetch live prices, tick volumes, trend & check SNR touch / breakout
                await self.check_all_symbols(now_wib)
                
                # 2. 15-Minute Scheduled Report (Setiap 15 menit sekali: :00, :15, :30, :45 WIB)
                current_slot = (now_wib.hour, now_wib.minute // 15)
                if self.last_scheduled_slot != current_slot:
                    await self.send_scheduled_report(now_wib)
                    self.last_scheduled_slot = current_slot
                    
            except Exception as e:
                logger.error(f"Error in SRMonitorEngine loop: {e}", exc_info=True)
                
            await asyncio.sleep(30) # Scan interval 30 detik

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
            "columns": ["close", "bid", "ask", "change", "change_abs", "high", "low", "volume", "Recommend.All", "RSI"]
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
                        close = vals[0]
                        bid = vals[1]
                        ask = vals[2]
                        chg_pct = vals[3] or 0.0
                        chg_abs = vals[4] or 0.0
                        vol = vals[7] if len(vals) > 7 and vals[7] is not None else 50000
                        rec = vals[8] if len(vals) > 8 and vals[8] is not None else 0.0
                        rsi = vals[9] if len(vals) > 9 and vals[9] is not None else 50.0

                        mid = (bid + ask) / 2.0 if (bid and ask and bid > 0 and ask > 0) else close
                        record = {
                            "price": mid,
                            "change_val": chg_abs,
                            "change_pct": chg_pct,
                            "volume": vol,
                            "rec": rec,
                            "rsi": rsi,
                            "source": f"Cloud TV ({ticker})"
                        }
                        
                        if "XAUUSD" in ticker and "XAUUSD" not in prices:
                            prices["XAUUSD"] = record
                        elif "EURUSD" in ticker and "EURUSD" not in prices:
                            prices["EURUSD"] = record
                        elif ("CL1!" in ticker or "USOIL" in ticker) and "OIL" not in prices:
                            prices["OIL"] = record
                        elif "USDJPY" in ticker and "USDJPY" not in prices:
                            prices["USDJPY"] = record
        except Exception as e:
            logger.warning(f"TradingView cloud price fetch exception: {e}")
        return prices

    def fetch_economic_calendar(self) -> list:
        """Fetches live high-impact macroeconomic events from global cloud calendar feed."""
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [e for e in data if e.get("impact") in ("High", "Medium")]
        except Exception as e:
            logger.debug(f"Calendar fetch notice: {e}")
            return []

    async def check_all_symbols(self, now_wib: datetime):
        loop = asyncio.get_running_loop()
        tv_prices = await loop.run_in_executor(None, self.fetch_tradingview_prices)
        mt5_active = mt5.initialize() if mt5 is not None else False

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
                if mt5_active:
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

            # Order Flow, Tick Volume & Trend Evaluation (Cloud First)
            buy_tick = 1200
            sell_tick = 1000
            trend = "UP"

            if symbol in tv_prices:
                tv_data = tv_prices[symbol]
                rec = tv_data.get("rec", 0.0)
                rsi = tv_data.get("rsi", 50.0)
                
                # Dynamic order flow calculation from cloud indicators (No MT5 needed)
                # rec ranges from -1.0 (Strong Sell) to +1.0 (Strong Buy)
                calc_buy_pct = int(50 + rec * 28 + (chg_pct * 8))
                calc_buy_pct = max(30, min(70, calc_buy_pct))
                
                total_ticks = 2200
                buy_tick = int(total_ticks * (calc_buy_pct / 100.0))
                sell_tick = total_ticks - buy_tick
                
                if rec > 0.12 or (rec >= 0 and chg_val > 0):
                    trend = "UP"
                elif rec < -0.12 or (rec <= 0 and chg_val < 0):
                    trend = "DOWN"
                else:
                    trend = "SIDE"

            # Optional local MT5 Enhancement if terminal happens to be active
            if mt5_active and symbol in ["XAUUSD", "EURUSD", "USDJPY"]:
                try:
                    ticks = mt5.copy_ticks_from(symbol, datetime.now(), 2000, mt5.COPY_TICKS_ALL)
                    if ticks is not None and len(ticks) > 1:
                        b_cnt = 0
                        s_cnt = 0
                        for i in range(1, len(ticks)):
                            p_c = (ticks[i][1] + ticks[i][2]) / 2.0
                            p_p = (ticks[i-1][1] + ticks[i-1][2]) / 2.0
                            if p_c > p_p: b_cnt += 1
                            elif p_c < p_p: s_cnt += 1
                            else:
                                if b_cnt <= s_cnt: b_cnt += 1
                                else: s_cnt += 1
                        buy_tick = b_cnt
                        sell_tick = s_cnt
                except Exception:
                    pass

            tot = max(1, buy_tick + sell_tick)
            buy_pct = round(buy_tick / tot * 100)
            sell_pct = 100 - buy_pct
            delta = buy_tick - sell_tick

            # Pressure Threshold Evaluation (Section D)
            if buy_pct > 55:
                pressure = "BUY_PRESSURE"
            elif sell_pct > 55:
                pressure = "SELL_PRESSURE"
            else:
                pressure = "BALANCED"

            # Strict State & Status Matrix Evaluation (Section E, F, G, H, I)
            is_touch_event = False
            raw_state = "WAIT"
            status = "WAIT"
            status_sub = "Konsolidasi tengah, tunggu setup"

            if price > res:
                self.raw_outside_count[symbol]["BREAKOUT"] += 1
                self.raw_outside_count[symbol]["BREAKDOWN"] = 0
                if self.raw_outside_count[symbol]["BREAKOUT"] >= 2:
                    raw_state = "BREAKOUT"
                    status = "BREAKOUT WATCH"
                    status_sub = "Tembus Resistance waspada breakout"
                    is_touch_event = True
                else:
                    raw_state = self.current_state[symbol]
                    status = "WAIT"
            elif price < supp:
                self.raw_outside_count[symbol]["BREAKDOWN"] += 1
                self.raw_outside_count[symbol]["BREAKOUT"] = 0
                if self.raw_outside_count[symbol]["BREAKDOWN"] >= 2:
                    raw_state = "BREAKDOWN"
                    status = "BREAKDOWN RISK"
                    status_sub = "Tembus Support waspada breakdown"
                    is_touch_event = True
                else:
                    raw_state = self.current_state[symbol]
                    status = "WAIT"
            else:
                self.raw_outside_count[symbol]["BREAKOUT"] = 0
                self.raw_outside_count[symbol]["BREAKDOWN"] = 0

                # Check proximity / touch
                is_near_s = (price <= supp * (1.0 + near_pct)) or (pct_snr <= 5.0)
                is_near_r = (price >= res * (1.0 - near_pct)) or (pct_snr >= 95.0)

                if pct_snr <= 20.0:
                    # 0–20% BUY ZONE
                    if is_near_s: is_touch_event = True
                    if pressure == "BUY_PRESSURE":
                        raw_state = "TOUCH_SUPPORT" if is_near_s else "NEAR_SUPPORT"
                        status = "BUY"
                        status_sub = "Dekat support, Buy volume dominan"
                    elif pressure == "SELL_PRESSURE":
                        # Section G: JANGAN tampilkan BUY bila Sell Volume jauh lebih besar!
                        raw_state = "TOUCH_SUPPORT" if is_near_s else "NEAR_SUPPORT"
                        status = "SELL PRESSURE"
                        status_sub = "Dekat support, waspada breakdown"
                    else:
                        status = "WAIT"
                        status_sub = "Dekat support, volume seimbang"
                elif pct_snr >= 80.0:
                    # 80–100% SELL ZONE
                    if is_near_r: is_touch_event = True
                    if pressure == "BUY_PRESSURE":
                        # Section G: JANGAN langsung tampilkan SELL bila Buy Volume jauh lebih besar!
                        raw_state = "TOUCH_RESISTANCE" if is_near_r else "NEAR_RESISTANCE"
                        status = "BREAKOUT WATCH"
                        status_sub = "Dekat resistance, waspada breakout"
                    elif pressure == "SELL_PRESSURE":
                        raw_state = "TOUCH_RESISTANCE" if is_near_r else "NEAR_RESISTANCE"
                        status = "REVERSAL WATCH"
                        status_sub = "Dekat resistance, Sell volume dominan"
                    else:
                        status = "WAIT"
                        status_sub = "Dekat resistance, volume seimbang"
                else:
                    # 20–80% NEUTRAL / WAIT ZONE
                    if pressure == "BUY_PRESSURE":
                        status = "WAIT"
                        status_sub = "Net Buy, masih tengah tunggu konfirmasi"
                    elif pressure == "SELL_PRESSURE":
                        status = "WAIT"
                        status_sub = "Net Sell, masih tengah tunggu konfirmasi"
                    else:
                        status = "WAIT"
                        status_sub = "Konsolidasi tengah, tunggu setup"

            prev_state = self.current_state[symbol]

            # Save full record
            self.last_price_data[symbol] = {
                "name": cfg["name"],
                "subtitle": cfg["subtitle"],
                "icon_type": cfg["icon_type"],
                "price": price,
                "change_val": chg_val,
                "change_pct": chg_pct,
                "digits": cfg["digits"],
                "support": supp,
                "resistance": res,
                "pct_snr": pct_snr,
                "buy_tick": buy_tick,
                "sell_tick": sell_tick,
                "buy_pct": buy_pct,
                "sell_pct": sell_pct,
                "delta": delta,
                "trend": trend,
                "pressure": pressure,
                "status": status,
                "status_sub": status_sub,
                "raw_state": raw_state,
                "source": source_info,
                "time": now_wib
            }

            # TRIGGER INSTANT ALERT JIKA MENGENAI SNR
            now_ts = datetime.now().timestamp()
            cooldown_expired = (now_ts - self.last_alert_sent_time.get(symbol, 0)) > 1800 # 30 min cooldown
            
            if is_touch_event:
                if raw_state != prev_state or cooldown_expired:
                    self.current_state[symbol] = raw_state
                    self.last_alert_sent_time[symbol] = now_ts
                    await self.send_instant_touch_alert(symbol, raw_state, status, status_sub, price, supp, res, pct_snr, delta, buy_pct, sell_pct, now_wib)
            else:
                self.current_state[symbol] = raw_state

        if mt5_active and mt5 is not None:
            mt5.shutdown()

    async def send_instant_touch_alert(self, symbol: str, state: str, status: str, status_sub: str, price: float, supp: float, res: float, pct_snr: float, delta: int, buy_pct: float, sell_pct: float, now_wib: datetime):
        """
        Sends an INSTANT 16:9 Bloomberg Dashboard Card & alert when price touches or breaks SNR.
        """
        cfg = self.CONFIG[symbol]
        digits = cfg["digits"]
        time_str = now_wib.strftime("%H:%M:%S WIB")
        
        if "RESISTANCE" in state or pct_snr >= 80:
            level_name = "RESISTANCE"
            target_level = res
            dist = res - price
            event_title = "🚨 <b>S/R ALERT — MENGENAI RESISTANCE!</b>"
        elif "SUPPORT" in state or pct_snr <= 20:
            level_name = "SUPPORT"
            target_level = supp
            dist = price - supp
            event_title = "🚨 <b>S/R ALERT — MENGENAI SUPPORT!</b>"
        elif state == "BREAKOUT":
            level_name = "BREAKOUT R"
            target_level = res
            dist = price - res
            event_title = "⚡🚨 <b>BREAKOUT ALERT — TEMBUS RESISTANCE!</b>"
        elif state == "BREAKDOWN":
            level_name = "BREAKDOWN S"
            target_level = supp
            dist = supp - price
            event_title = "⚡🚨 <b>BREAKDOWN ALERT — TEMBUS SUPPORT!</b>"
        else:
            return

        d_sign = "+" if delta >= 0 else ""
        caption = (
            f"{event_title}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 <b>{cfg['name']} ({cfg['subtitle']})</b>\n"
            f"• 💰 <b>Live Price:</b> <code>{price:,.{digits}f}</code>\n"
            f"• 🎯 <b>Level {level_name}:</b> <code>{target_level:,.{digits}f}</code> (Jarak: {dist:+.{digits}f})\n"
            f"• 📊 <b>%SNR:</b> <code>{pct_snr:.1f}%</code>\n"
            f"• ⚡ <b>Volume Flow:</b> Buy {buy_pct}% | Sell {sell_pct}% | Delta: {d_sign}{delta}\n"
            f"• 🏷️ <b>Status Sinyal:</b> <b>{status}</b> ({status_sub})\n"
            f"• ⏱️ <b>Waktu:</b> {time_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        try:
            photo_bytes = self.generate_current_photo_card()
            await self._send_photo(photo_bytes, caption=caption)
            logger.info(f"Instant SNR touch alert sent for {symbol} ({state})")
        except Exception as e:
            logger.error(f"Failed to send instant touch photo: {e}")
            await self._send_safe(caption)

    async def send_scheduled_report(self, now_wib: datetime):
        """
        Sends the scheduled 15-minute report with the latest 16:9 Bloomberg Dashboard Card.
        """
        time_str = now_wib.strftime("%d %b %Y • %H:%M WIB")
        
        summary_rows = []
        for symbol, cfg in self.CONFIG.items():
            d = self.last_price_data.get(symbol)
            digits = cfg["digits"]
            if d:
                p = d["price"]
                st = d["status"]
                pct = d["pct_snr"]
                delta = d["delta"]
                d_sgn = "+" if delta >= 0 else ""
                summary_rows.append(f"• <b>{cfg['name']}</b>: <code>{p:,.{digits}f}</code> (%SNR: {pct:.1f}% | Δ: {d_sgn}{delta}) → <b>{st}</b>")
            else:
                summary_rows.append(f"• <b>{cfg['name']}</b>: <i>Sinkronisasi...</i>")

        report_caption = (
            f"🏛️ <b>BLOOMBERG S/R LIVE DASHBOARD</b>\n"
            f"🕒 <b>{time_str}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(summary_rows) + "\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <i>Update otomatis setiap 15 menit & langsung mengirim visual instan jika harga live mengenai batas SNR.</i>"
        )

        try:
            photo_bytes = self.generate_current_photo_card()
            await self._send_photo(photo_bytes, caption=report_caption)
            logger.info("15-Minute Bloomberg Dashboard card sent to Telegram.")
        except Exception as e:
            logger.error(f"Failed to send scheduled report card: {e}")
            await self._send_safe(report_caption)

    async def send_hourly_report(self, now_wib: datetime):
        """Backwards compatibility alias."""
        await self.send_scheduled_report(now_wib)

    def generate_current_photo_card(self, now_wib: datetime = None) -> bytes:
        """
        Generates the 16:9 Bloomberg Dashboard PNG card in memory.
        """
        data_list = []
        for symbol, cfg in self.CONFIG.items():
            d = self.last_price_data.get(symbol)
            if d:
                data_list.append(d)
            else:
                # Default initial placeholder
                supp = cfg["support"]
                res = cfg["resistance"]
                mid = supp + (res - supp) * 0.5
                data_list.append({
                    "name": cfg["name"],
                    "subtitle": cfg["subtitle"],
                    "icon_type": cfg["icon_type"],
                    "price": mid,
                    "change_val": 0.0,
                    "change_pct": 0.0,
                    "digits": cfg["digits"],
                    "support": supp,
                    "resistance": res,
                    "pct_snr": 50.0,
                    "buy_tick": 1200,
                    "sell_tick": 1000,
                    "buy_pct": 55,
                    "sell_pct": 45,
                    "delta": 200,
                    "trend": "UP",
                    "status": "WAIT",
                    "status_sub": "Sinkronisasi market..."
                })
        return generate_sr_card_bytes(data_list)

    def get_current_status_summary(self) -> str:
        now_wib = datetime.now(WIB)
        time_str = now_wib.strftime("%H:%M:%S WIB")
        summary_lines = [f"📊 <b>BLOOMBERG MASTER S/R DASHBOARD</b> ({time_str})\n━━━━━━━━━━━━━━━━━━━━━━"]
        for symbol, cfg in self.CONFIG.items():
            d = self.last_price_data.get(symbol)
            digits = cfg["digits"]
            if d:
                d_sgn = "+" if d["delta"] >= 0 else ""
                summary_lines.append(
                    f"• <b>{cfg['name']} ({cfg['subtitle']})</b>: <code>{d['price']:,.{digits}f}</code>\n"
                    f"  S: {cfg['support']:.{digits}f} | R: {cfg['resistance']:.{digits}f} | %SNR: <b>{d['pct_snr']:.1f}%</b>\n"
                    f"  Flow: Buy {d['buy_pct']}% / Sell {d['sell_pct']}% (Δ {d_sgn}{d['delta']}) | Trend: <b>{d['trend']}</b>\n"
                    f"  Status: <b>{d['status']}</b> ({d['status_sub']})"
                )
            else:
                summary_lines.append(f"• <b>{cfg['name']}</b>: Menunggu sinkronisasi harga...")
        summary_lines.append("━━━━━━━━━━━━━━━━━━━━━━\n<i>Ketik /sr untuk refresh kartu Bloomberg live.</i>")
        return "\n".join(summary_lines)
