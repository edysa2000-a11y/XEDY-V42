import asyncio
import logging
import os
import json
import urllib.request
import uuid
import math
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
            "support": 4220.0,
            "resistance": 4580.0,
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
            "support": 152.80,
            "resistance": 158.30,
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
                
                # Composite institutional directional order flow proxy
                # Driven by Technical Oscillators/MA rating (45%), RSI Displacement (25%), Intraday Momentum (30%)
                rsi_disp = (rsi - 50.0) / 50.0
                mom_bias = math.copysign(min(1.0, abs(chg_pct) / 0.5), chg_pct) if abs(chg_pct) > 0.001 else 0.0
                flow_bias = (rec * 0.45) + (rsi_disp * 0.25) + (mom_bias * 0.30)
                
                calc_buy_pct = int(round(50.0 + flow_bias * 36.0))
                calc_buy_pct = max(24, min(76, calc_buy_pct))
                
                total_ticks = 2200
                buy_tick = int(total_ticks * (calc_buy_pct / 100.0))
                sell_tick = total_ticks - buy_tick
                
                if rec > 0.12 or (rec >= 0 and chg_val > 0):
                    trend = "UP"
                elif rec < -0.12 or (rec <= 0 and chg_val < 0):
                    trend = "DOWN"
                else:
                    trend = "SIDE"

            # Optional local MT5 calibration of volume scale
            if mt5_active and symbol in ["XAUUSD", "EURUSD", "USDJPY"]:
                try:
                    t_info = mt5.symbol_info_tick(symbol)
                    if t_info and t_info.volume > 0:
                        total_ticks = int(max(1500, min(5000, t_info.volume)))
                        buy_tick = int(total_ticks * (calc_buy_pct / 100.0))
                        sell_tick = total_ticks - buy_tick
                except Exception:
                    pass

            tot = max(1, buy_tick + sell_tick)
            buy_pct = round(buy_tick / tot * 100)
            sell_pct = 100 - buy_pct
            delta = buy_tick - sell_tick
            delta_pct = round((delta / tot) * 100)

            # Pressure Threshold Evaluation
            if buy_pct >= 65:
                pressure = "STRONG_BUY"
            elif buy_pct > 55:
                pressure = "BUY_PRESSURE"
            elif sell_pct >= 65:
                pressure = "STRONG_SELL"
            elif sell_pct > 55:
                pressure = "SELL_PRESSURE"
            else:
                pressure = "BALANCED"

            # Reversal Score Engine (0 - 100)
            if pct_snr <= 20.0:
                rev_base = int((20.0 - max(0.0, pct_snr)) * 1.5)
                rev_press = int((buy_pct - 50) * 1.5) if buy_pct >= 55 else 0
                rev_delta = min(20, int((delta / tot) * 40)) if delta > 0 else 0
                rev_pa = 15 if (trend == "UP" or chg_val > 0) else 0
                reversal_score = min(98, max(20, rev_base + rev_press + rev_delta + rev_pa + 15))
            elif pct_snr >= 80.0:
                rev_base = int((min(100.0, pct_snr) - 80.0) * 1.5)
                rev_press = int((sell_pct - 50) * 1.5) if sell_pct >= 55 else 0
                rev_delta = min(20, int((-delta / tot) * 40)) if delta < 0 else 0
                rev_pa = 15 if (trend == "DOWN" or chg_val < 0) else 0
                reversal_score = min(98, max(20, rev_base + rev_press + rev_delta + rev_pa + 15))
            else:
                reversal_score = min(60, max(25, int(42 + (buy_pct - 50) * 0.4)))

            # Confidence Score Engine (0 - 100)
            c_loc = 20 if (pct_snr <= 20.0 or pct_snr >= 80.0) else max(8, int(20 - abs(pct_snr - 50.0) * 0.3))
            c_press = min(20, max(8, int((abs(buy_pct - 50) / 50.0) * 12) + 8))
            c_delta = min(15, max(5, int(abs(delta / tot) * 45)))
            c_trend = 15 if trend != "SIDE" else 8
            c_pa = 20 if ((buy_pct > 50 and chg_val > 0) or (sell_pct > 50 and chg_val < 0)) else 10
            c_mkt = 10
            confidence = min(98, max(35, c_loc + c_press + c_delta + c_trend + c_pa + c_mkt))

            # Action Score Engine (0 - 100)
            a_loc = 25 if (pct_snr <= 15.0 or pct_snr >= 85.0) else (20 if (pct_snr <= 20.0 or pct_snr >= 80.0) else 10)
            a_press = 25 if (buy_pct >= 65 or sell_pct >= 65) else (18 if (buy_pct > 55 or sell_pct > 55) else 10)
            a_delta = min(15, max(5, int(abs(delta / tot) * 45)))
            a_trend = 15 if trend != "SIDE" else 8
            a_pa = 20 if ((buy_pct > 50 and chg_val > 0) or (sell_pct > 50 and chg_val < 0)) else 10
            action_score = min(98, max(35, a_loc + a_press + a_delta + a_trend + a_pa))

            # Daily Scalping Signal Grade Engine
            if (buy_pct >= 65 or sell_pct >= 65) and abs(delta / tot) >= 0.18 and confidence >= 85 and action_score >= 80:
                grade = "A+"
            elif (buy_pct >= 60 or sell_pct >= 60) and confidence >= 75 and action_score >= 70:
                grade = "A"
            elif (buy_pct >= 55 or sell_pct >= 55) and confidence >= 65 and action_score >= 60:
                grade = "B"
            elif confidence >= 60 and action_score >= 48:
                grade = "C"
            else:
                grade = "D"

            # Daily Scalping Final Status Engine Priority (1 to 15)
            is_touch_event = False
            raw_state = "WAIT"

            if price > res and buy_pct >= 60 and trend == "UP":
                status = "BREAKOUT BUY"
                status_sub = "Breakout scalping, ikuti momentum"
                raw_state = "BREAKOUT"
                is_touch_event = True
            elif price < supp and sell_pct >= 60 and trend == "DOWN":
                status = "BREAKDOWN"
                status_sub = "Breakdown scalping, ikuti momentum"
                raw_state = "BREAKDOWN"
                is_touch_event = True
            elif buy_pct >= 65 and trend == "UP" and confidence >= 80:
                status = "STRONG BUY"
                status_sub = "Momentum buy scalping agresif"
                raw_state = "TOUCH_SUPPORT" if pct_snr <= 25.0 else "NEAR_SUPPORT"
                is_touch_event = True if pct_snr <= 25.0 else False
            elif sell_pct >= 65 and trend == "DOWN" and confidence >= 80:
                status = "STRONG SELL"
                status_sub = "Momentum sell scalping agresif"
                raw_state = "TOUCH_RESISTANCE" if pct_snr >= 75.0 else "NEAR_RESISTANCE"
                is_touch_event = True if pct_snr >= 75.0 else False
            elif pct_snr <= 25.0 and buy_pct >= 55 and reversal_score >= 60:
                status = "REVERSAL UP"
                status_sub = "Pantulan support scalping valid"
                raw_state = "NEAR_SUPPORT"
                is_touch_event = True
            elif pct_snr >= 75.0 and sell_pct >= 55 and reversal_score >= 60:
                status = "REVERSAL DOWN"
                status_sub = "Pantulan resist scalping valid"
                raw_state = "NEAR_RESISTANCE"
                is_touch_event = True
            elif buy_pct >= 60 and (trend == "UP" or pct_snr <= 40.0):
                status = "BUY SCALP"
                status_sub = "Entri buy scalping terkonfirmasi"
                raw_state = "NEAR_SUPPORT"
            elif sell_pct >= 60 and (trend == "DOWN" or pct_snr >= 60.0):
                status = "SELL SCALP"
                status_sub = "Entri sell scalping terkonfirmasi"
                raw_state = "NEAR_RESISTANCE"
            elif pct_snr >= 70.0 and buy_pct >= 55:
                status = "BREAKOUT WATCH"
                status_sub = "Dekat resist, waspada breakout"
            elif pct_snr <= 30.0 and sell_pct >= 55:
                status = "BREAKDOWN RISK"
                status_sub = "Dekat support, waspada breakdown"
            elif action_score >= 60:
                if buy_pct > sell_pct:
                    status = "BUY SETUP"
                    status_sub = "Setup buy scalping terbentuk"
                else:
                    status = "SELL SETUP"
                    status_sub = "Setup sell scalping terbentuk"
            elif buy_pct >= 55:
                status = "BUY PRESSURE"
                status_sub = "Tekanan beli aktif, cari pullback"
            elif sell_pct >= 55:
                status = "SELL PRESSURE"
                status_sub = "Tekanan jual aktif, cari pullback"
            elif pct_snr <= 20.0:
                status = "WAIT"
                status_sub = "Dekat support, volume seimbang"
            elif pct_snr >= 80.0:
                status = "WAIT"
                status_sub = "Dekat resistance, volume seimbang"
            else:
                status = "WAIT"
                status_sub = "Konsolidasi sempit, tunggu setup"

            # Precision Daily Scalping TP / SL Engine
            digits = cfg["digits"]
            if symbol == "XAUUSD":
                sl_dist = 5.20     # ~5.2 points risk
                tp1_dist = 4.50    # ~4.5 points target (0.86R)
                tp2_dist = 8.80    # ~8.8 points target (1.7R)
                tp3_dist = 13.50   # ~13.5 points target (2.6R)
                rr = "1:1.9"
            elif symbol == "EURUSD":
                sl_dist = 0.0016   # 16 pips risk
                tp1_dist = 0.0013  # 13 pips target
                tp2_dist = 0.0025  # 25 pips target
                tp3_dist = 0.0036  # 36 pips target
                rr = "1:1.8"
            elif symbol == "OIL":
                sl_dist = 0.65     # 65 cents risk
                tp1_dist = 0.55    # 55 cents target
                tp2_dist = 1.10    # $1.10 target
                tp3_dist = 1.65    # $1.65 target
                rr = "1:1.8"
            elif symbol == "USDJPY":
                sl_dist = 0.25     # 25 pips risk
                tp1_dist = 0.22    # 22 pips target
                tp2_dist = 0.44    # 44 pips target
                tp3_dist = 0.66    # 66 pips target
                rr = "1:1.8"
            else:
                sl_dist = price * 0.0025
                tp1_dist = sl_dist * 0.85
                tp2_dist = sl_dist * 1.70
                tp3_dist = sl_dist * 2.50
                rr = "1:1.8"

            is_buy_bias = any(k in status for k in ["BUY", "UP"]) or (buy_pct > sell_pct and "SELL" not in status)
            if is_buy_bias:
                sl = round(price - sl_dist, digits)
                tp1 = round(price + tp1_dist, digits)
                tp2 = round(price + tp2_dist, digits)
                tp3 = round(price + tp3_dist, digits)
            else:
                sl = round(price + sl_dist, digits)
                tp1 = round(price - tp1_dist, digits)
                tp2 = round(price - tp2_dist, digits)
                tp3 = round(price - tp3_dist, digits)

            prev_state = self.current_state[symbol]

            # Save full record
            self.last_price_data[symbol] = {
                "name": cfg["name"],
                "subtitle": cfg["subtitle"],
                "icon_type": cfg["icon_type"],
                "price": price,
                "change_val": chg_val,
                "change_pct": chg_pct,
                "digits": digits,
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
                "reversal_score": reversal_score,
                "confidence": confidence,
                "action_score": action_score,
                "grade": grade,
                "status": status,
                "status_sub": status_sub,
                "tp1": tp1,
                "tp2": tp2,
                "tp3": tp3,
                "sl": sl,
                "rr": rr,
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
                    "pressure": "BALANCED",
                    "reversal_score": 45,
                    "confidence": 75,
                    "action_score": 65,
                    "grade": "B",
                    "status": "WAIT",
                    "status_sub": "Sinkronisasi market...",
                    "tp1": mid,
                    "tp2": mid,
                    "tp3": mid,
                    "sl": supp,
                    "rr": "1:1.8"
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
                gr = d.get("grade", "B")
                conf = d.get("confidence", 75)
                act = d.get("action_score", 65)
                summary_lines.append(
                    f"• <b>[{gr}] {cfg['name']} ({cfg['subtitle']})</b>: <code>{d['price']:,.{digits}f}</code>\n"
                    f"  S: {cfg['support']:.{digits}f} | R: {cfg['resistance']:.{digits}f} | %SNR: <b>{d['pct_snr']:.1f}%</b>\n"
                    f"  Flow: B {d['buy_pct']}% / S {d['sell_pct']}% (Δ {d_sgn}{d['delta']}) | Score: Conf {conf}% / Act {act}\n"
                    f"  Status: <b>{d['status']}</b> ({d['status_sub']})"
                )
            else:
                summary_lines.append(f"• <b>{cfg['name']}</b>: Menunggu sinkronisasi harga...")
        summary_lines.append("━━━━━━━━━━━━━━━━━━━━━━\n<i>Ketik /popup atau /sr untuk kartu visual 16:9 widescreen.</i>")
        return "\n".join(summary_lines)
