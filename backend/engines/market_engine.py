from .base_engine import BaseEngine
import MetaTrader5 as mt5
import asyncio
import os
import pandas as pd
from datetime import datetime

class MarketEngine(BaseEngine):
    """
    Market Engine: Responsible for connecting to MT5 and ingesting ticks for multiple symbols.
    """
    
    @property
    def engine_name(self) -> str:
        return "MarketEngine"

    def __init__(self, config=None, feature_stores=None, data_engine=None, news_engine=None, symbols=None, v39_engines=None):
        super().__init__(config)
        self.feature_stores = feature_stores or {}
        self.data_engine = data_engine
        self.news_engine = news_engine
        self.symbols = symbols if symbols else ["XAUUSD"]
        self.v39_engines = v39_engines
        self.last_tick_time_msc = {s: 0 for s in self.symbols}
        self._running = False

    async def start(self):
        self.logger.info("Initializing MetaTrader 5...")
        if not mt5.initialize():
            self.logger.error("MT5 initialize() failed, error code: " + str(mt5.last_error()))
        else:
            for symbol in self.symbols:
                self.logger.info(f"Selecting symbol {symbol}...")
                if not mt5.symbol_select(symbol, True):
                    self.logger.error(f"Failed to select symbol {symbol}")
                else:
                    self.logger.info(f"MT5 Connected. Subscribed to {symbol}")
            
        self._running = True
        # Start background polling loop
        asyncio.create_task(self._poll_ticks())

    async def stop(self):
        self.logger.info("Stopping Market Engine...")
        self._running = False
        mt5.shutdown()

    async def _poll_ticks(self):
        """Polls MT5 for the latest tick for all symbols."""
        from backend.api.websocket import ws_manager
        
        loop_counter = 0
        while self._running:
            try:
                # Determine MT5 statuses
                is_mt5_ok = mt5.terminal_info() is not None
                
                # Broadcast status occasionally (every ~2 seconds)
                if loop_counter % 20 == 0:
                    await ws_manager.broadcast_status(
                        broker_status="CONNECTED" if is_mt5_ok else "DISCONNECTED",
                        mt5_status="CONNECTED" if is_mt5_ok else "DISCONNECTED",
                        ai_status="ACTIVE"
                    )
                    
# Fetch detailed dashboard data if engines exist
                    if self.data_engine and self.news_engine:
                        dashboard_payload = {
                            "type": "dashboard_data",
                            "data_engine": self.data_engine.get_dashboard_data(),
                            "news_engine": self.news_engine.get_dashboard_data()
                        }
                        if not hasattr(self, "_last_dash_str") or self._last_dash_str != str(dashboard_payload):
                            self._last_dash_str = str(dashboard_payload)
                            await ws_manager._broadcast_json(dashboard_payload)
                        
                    # Broadcast V39 Causal Engine Data
                    if self.v39_engines and "XAUUSD" in self.v39_engines:
                        v39 = self.v39_engines["XAUUSD"]
                        
                        import time
                        current_time = time.time()
                        if not hasattr(self, "_last_tele_outlook_time"):
                            self._last_tele_outlook_time = current_time - 1790 # Trigger almost immediately on start
                        
                        # Cache slow AI/Macro responses to prevent API rate limits
                        if not hasattr(self, "_cached_event_res") or loop_counter % 600 == 0: # Every ~60 seconds
                            latest_headline = "Technical & Macro Dynamics"
                            if hasattr(self, "news_engine") and self.news_engine and hasattr(self.news_engine, 'news_feed') and len(self.news_engine.news_feed) > 0:
                                latest_headline = self.news_engine.news_feed[-1].get('headline', latest_headline)
                                
                            self._cached_event_res = await v39["v39_event"].process_news(latest_headline)
                            self._cached_macro_res = await v39["v39_macro"].calculate_yield_dxy(self._cached_event_res)
                            
                        event_res = self._cached_event_res
                        macro_res = self._cached_macro_res
                        
                        # Use actual tick volume from MT5 if available (async non-blocking)
                        tick_vol = 500
                        try:
                            if is_mt5_ok:
                                rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M5, 0, 1)
                                if rates is not None and len(rates) > 0:
                                    tick_vol = int(rates[0]['tick_volume'])
                        except Exception:
                            pass
                                
                        flow_res = await v39["v39_flow"].aggregate_flow_channels(0.005, tick_vol)
                        div_res = await v39["v39_div"].check_divergence(1.5, flow_res, macro_res)
                        
                        # --- Adaptive Self-Learning Technical Score (RSI + BB Sniper) ---
                        tech_score = 50.0
                        try:
                            if is_mt5_ok:
                                rates_50 = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M15, 0, 50)
                                if rates_50 is not None and len(rates_50) >= 50:
                                    df_tech = pd.DataFrame(rates_50)
                                    
                                    # Calculate RSI 14
                                    delta = df_tech['close'].diff()
                                    gain = delta.where(delta > 0, 0)
                                    loss = -delta.where(delta < 0, 0)
                                    avg_gain = gain.rolling(window=14, min_periods=1).mean()
                                    avg_loss = loss.rolling(window=14, min_periods=1).mean()
                                    rs = avg_gain / avg_loss
                                    df_tech['rsi'] = 100 - (100 / (1 + rs))
                                    current_rsi = df_tech['rsi'].iloc[-1]
                                    
                                    # --- CAUSAL SUPREMACY TREND FILTER (EMA 50 D1) ---
                                    trend_filter = "NEUTRAL"
                                    rates_d1 = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_D1, 0, 100)
                                    if rates_d1 is not None and len(rates_d1) >= 50:
                                        df_d1 = pd.DataFrame(rates_d1)
                                        ema_50_d1 = df_d1['close'].ewm(span=50, adjust=False).mean().iloc[-1]
                                        trend_filter = "UP" if df_tech['close'].iloc[-1] > ema_50_d1 else "DOWN"

                                    # Calculate Bollinger Bands (20, 2.0) for Sniper Entries (Optimized)
                                    rolling_mean = df_tech['close'].rolling(window=20).mean()
                                    rolling_std = df_tech['close'].rolling(window=20).std()
                                    upper_band = rolling_mean + (rolling_std * 2.0)
                                    lower_band = rolling_mean - (rolling_std * 2.0)
                                    current_upper = upper_band.iloc[-1]
                                    current_lower = lower_band.iloc[-1]
                                    
                                    current_close = df_tech['close'].iloc[-1]
                                    current_low = df_tech['low'].iloc[-1]
                                    current_high = df_tech['high'].iloc[-1]
                                    
                                    # Adaptive Sniper Logic (Optimized: RSI 70/30, BB 2.0, Trend Filter)
                                    # BUY if touches lower band AND RSI < 30 AND Trend is not DOWN
                                    if current_low <= current_lower and current_rsi < 30 and trend_filter != "DOWN":
                                        tech_score = 95.0
                                        self.logger.info(f"SNIPER BUY SIGNAL: RSI={current_rsi:.1f}, Low={current_low:.2f} <= BB_Low={current_lower:.2f}, Trend={trend_filter}")
                                    # SELL if touches upper band AND RSI > 70 AND Trend is not UP
                                    elif current_high >= current_upper and current_rsi > 70 and trend_filter != "UP":
                                        tech_score = 5.0 # Low tech score means DOWN (0-50 = SELL, 50-100 = BUY)
                                        self.logger.info(f"SNIPER SELL SIGNAL: RSI={current_rsi:.1f}, High={current_high:.2f} >= BB_Up={current_upper:.2f}, Trend={trend_filter}")
                                    else:
                                        tech_score = 50.0 # Neutral, don't force a trade
                        except Exception as e:
                            self.logger.error(f"Tech Score Error: {e}")
                            tech_score = 50.0
                            
                        gate_res = await v39["v39_consensus"].final_trade_gate(event_res, macro_res, flow_res, div_res, tech_score)
                        
                        from backend.main import app
                        qwen_autotrade = getattr(app.state, 'qwen_settings', {})
                        import time
                        current_time = time.time()
                        if not hasattr(self, "last_v39_trade_time"):
                            self.last_v39_trade_time = 0
                            
                        # The backend toggle status might be a string if sent over WS depending on parsing
                        is_autotrade_on = qwen_autotrade.get("autotrade", False)
                        if isinstance(is_autotrade_on, str):
                            is_autotrade_on = is_autotrade_on.lower() == 'true'
                            
                        # Conf_ok and ai_ok logic
                        min_conf = int(qwen_autotrade.get("min_confidence", 61))
                        calib_prob = round(float(gate_res.get("calibrated_prob", 0)))
                        
                        print(f"DEBUG GATE CHECKS: UI ON: {is_autotrade_on} | MIN CONF: {min_conf} | CALIB PROB: {calib_prob} | COOLDOWN: {current_time - self.last_v39_trade_time}")
                        
                        status_msg = "Waiting for Perfect Setup"
                        if calib_prob >= min_conf:
                            if not gate_res.get("trade_allowed"):
                                status_msg = "Rejected: Divergence/Anomaly Risk"
                            elif current_time - self.last_v39_trade_time <= 300:
                                status_msg = "Cooldown Active (Wait 5m)"
                            elif hasattr(self, 'last_safety_reject_reason') and self.last_safety_reject_reason:
                                status_msg = f"Guard Block: {self.last_safety_reject_reason}"
                            else:
                                status_msg = "Checking Safety Guards..."
                                
                        # Reset the guard reject reason for the next check
                        self.last_safety_reject_reason = ""
                                
                        v39_payload = {
                            "event": event_res,
                            "macro": macro_res,
                            "flow": flow_res,
                            "div": div_res,
                            "gate": gate_res,
                            "conditions": {
                                "is_on": bool(is_autotrade_on),
                                "conf_ok": bool(calib_prob >= min_conf),
                                "mt5_ok": bool(is_mt5_ok),
                                "cooldown_ok": bool((current_time - self.last_v39_trade_time) > 300),
                                "ai_ok": bool(calib_prob >= min_conf and gate_res.get("edge", 0) > 0),
                                "status_msg": status_msg,
                                "tech_score": float(tech_score)
                            }
                        }
                        
                        # Generate instant zero-token narrative for websocket broadcast
                        try:
                            from backend.telegram.zero_token_formatter import generate_ascii_narrative
                            headline = "Macro & Technical Dynamics"
                            if self.news_engine and hasattr(self.news_engine, 'news_feed') and len(self.news_engine.news_feed) > 0:
                                headline = self.news_engine.news_feed[-1].get('headline', headline)
                            
                            cp = 0.0
                            try:
                                tick = mt5.symbol_info_tick("XAUUSD")
                                if tick: cp = tick.bid
                            except: pass
                                
                            raw_ascii = generate_ascii_narrative(v39_payload, cp, headline)
                            
                            # Run Qwen LLM for beautification if autotrade/ai is enabled
                            from backend.engines.qwen_writer import rewrite_narrative_with_qwen
                            v39_payload["narrative"] = await rewrite_narrative_with_qwen(raw_ascii)
                        except Exception as e:
                            self.logger.error(f"Narrative Gen Error: {e}")
                            v39_payload["narrative"] = ""
                            
                        self.latest_v39_payload = v39_payload
                        await ws_manager.broadcast_v39_causal(v39_payload)
                        
                        # Only trigger Telegram/Execution rarely, to avoid spam, maybe use a cooldown mechanism
                        from backend.main import app
                        qwen_autotrade = getattr(app.state, 'qwen_settings', {})
                        
                        min_conf = qwen_autotrade.get("min_confidence", 61)
                        is_autotrade_on = qwen_autotrade.get("autotrade", False)
                        risk_model = qwen_autotrade.get("risk_model", "Conservative")
                        confidence = round(float(gate_res.get("calibrated_prob", 0)))
                        
                        # Let's check if trade is allowed and probabilty is high enough based on UI slider
                        import time
                        current_time = time.time()
                        if not hasattr(self, "last_v39_trade_time"):
                            self.last_v39_trade_time = 0
                            
                        if gate_res.get("trade_allowed") and confidence >= min_conf:
                            # 5-minute cooldown for signals (Pencegah Spam)
                            if current_time - self.last_v39_trade_time > 300:
                                raw_dir = gate_res.get("direction", "UP")
                                action = "BUY" if raw_dir == "UP" else "SELL"
                                
                                # Execute Trade via Qwen MT5 Logic
                                if is_autotrade_on and is_mt5_ok:
                                    try:
                                        # --- 4 ADAPTIVE SAFETY GUARDS ---
                                        safety_passed = True
                                        safety_reason = ""
                                        last_tick_check = mt5.symbol_info_tick("XAUUSD")
                                        
                                        if not last_tick_check:
                                            safety_passed = False
                                            safety_reason = "No tick data available."
                                        else:
                                            # 1. Stale Data Guard (> 5 seconds)
                                            if current_time - last_tick_check.time > 5.0:
                                                safety_passed = False
                                                safety_reason = f"Stale Data: Tick is {current_time - last_tick_check.time:.1f}s old."
                                                
                                            # 2. Adaptive Spread Guard (2.5x normal)
                                            rates_spread = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M1, 0, 10)
                                            if safety_passed and rates_spread is not None and len(rates_spread) > 0:
                                                avg_spread = sum([r['spread'] for r in rates_spread]) / len(rates_spread)
                                                current_spread = (last_tick_check.ask - last_tick_check.bid) / mt5.symbol_info("XAUUSD").point
                                                if current_spread > (avg_spread * 2.5) and current_spread > 40:
                                                    safety_passed = False
                                                    safety_reason = f"Spread Anomaly: {current_spread:.0f} > Avg {avg_spread:.0f} x 2.5"
                                                    
                                            # 3. Relative Volume Guard (VMA 14 on M5)
                                            rates_vol = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M5, 0, 15)
                                            if safety_passed and rates_vol is not None and len(rates_vol) >= 15:
                                                vma_14 = sum([r['tick_volume'] for r in rates_vol[:-1]]) / 14
                                                current_vol = rates_vol[-1]['tick_volume']
                                                if current_vol < (vma_14 * 0.5) and current_vol < 100:
                                                    safety_passed = False
                                                    safety_reason = f"Ghost Town Volume: {current_vol} < 50% of VMA {vma_14:.0f}"
                                                    
                                            # 4. Volatility-Based Daily Circuit Breaker (3x ATR D1 limits)
                                            if safety_passed:
                                                from datetime import datetime, timedelta
                                                today = datetime.now()
                                                start_day = datetime(today.year, today.month, today.day)
                                                history = mt5.history_deals_get(start_day, today + timedelta(days=1))
                                                today_profit = sum([d.profit for d in history if d.symbol == "XAUUSD" and d.entry == mt5.DEAL_ENTRY_OUT]) if history else 0.0
                                                acc_info = mt5.account_info()
                                                if acc_info:
                                                    # As a proxy for 3x ATR monetary value, we cap at 5% of balance for the day to avoid complex lot math.
                                                    if today_profit < -(acc_info.balance * 0.05):
                                                        safety_passed = False
                                                        safety_reason = f"Daily Circuit Breaker: Loss {today_profit:.2f} > 5% Equity."
                                        
                                        if not safety_passed:
                                            self.logger.info(f"Signal {action} DITOLAK oleh Safety Guard: {safety_reason}")
                                            self.last_safety_reject_reason = safety_reason
                                        else:
                                            acc_info = mt5.account_info()
                                            # Cek Posisi Aktif: Sniper AI hanya boleh buka 1 posisi dalam 1 waktu (No Hedging/Averaging)
                                            current_pos = mt5.positions_get(symbol="XAUUSD")
                                            if current_pos:
                                                current_pos = [p for p in current_pos if getattr(p, 'magic', 0) == int(os.environ.get("AUTOTRADE_MAGIC", "999111"))]
                                            num_pos = len(current_pos) if current_pos else 0
                                            
                                            can_open = True
                                            if num_pos > 0:
                                                can_open = False
                                                self.logger.info(f"Signal {action} ditolak: Masih ada {num_pos} posisi aktif. Menunggu clear.")
                                                self.last_safety_reject_reason = f"Waiting (1 Active Position)"
                                                
                                            if not can_open:
                                                pass # Skip eksekusi
                                            else:
                                                risk_pct = 0.5
                                                rm_lower = risk_model.lower() if isinstance(risk_model, str) else "conservative"
                                                if rm_lower == "standard": risk_pct = 1.0
                                                elif rm_lower == "moderate": risk_pct = 1.5
                                                elif rm_lower == "extreme": risk_pct = 2.0
                                                
                                                risk_amount = acc_info.balance * (risk_pct / 100)
                                                
                                                # ML Confidence Multiplier
                                                try:
                                                    from backend.engines.v39_causal.ml_state import get_weights
                                                    conf_mult = get_weights().get("confidence_multiplier", 1.0)
                                                except Exception:
                                                    conf_mult = 1.0
                                                
                                                # $500 risk per 1.0 lot for XAUUSD (assuming 50 pips SL at $10/pip)
                                                lot_size = round((risk_amount / 500) * conf_mult, 2)
                                                if lot_size < 0.01: lot_size = 0.01
                                                if lot_size > 10.0: lot_size = 10.0
                                                
                                                last_tick = mt5.symbol_info_tick("XAUUSD")
                                                if last_tick:
                                                    price = last_tick.ask if action == "BUY" else last_tick.bid
                                                    
                                                    # Dynamic ATR Calculation (14 periods on M15)
                                                    rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M15, 0, 14)
                                                    atr = 3.0 # Fallback
                                                    if rates is not None and len(rates) > 0:
                                                        true_ranges = []
                                                        for i in range(1, len(rates)):
                                                            high = rates[i]['high']
                                                            low = rates[i]['low']
                                                            prev_close = rates[i-1]['close']
                                                            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                                                            true_ranges.append(tr)
                                                        if true_ranges:
                                                            atr = sum(true_ranges) / len(true_ranges)
                                                    
                                                    # Limit ATR to prevent absurdly tight or wide SL (Min 20 pips, Max 150 pips)
                                                    atr = max(2.0, min(15.0, atr))
                                                    
                                                    # Risk to Reward 1:3 (SL lebih kecil dari TP - Tighter SL)
                                                    sl_dist = atr * 1.0
                                                    tp_dist = atr * 3.0
                                                    
                                                    sl = price - sl_dist if action == "BUY" else price + sl_dist
                                                    tp = price + tp_dist if action == "BUY" else price - tp_dist
                                                    
                                                    request = {
                                                        "action": mt5.TRADE_ACTION_DEAL,
                                                        "symbol": "XAUUSD",
                                                        "volume": lot_size,
                                                        "type": mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL,
                                                        "price": price,
                                                        "sl": sl,
                                                        "tp": tp,
                                                        "deviation": 20,
                                                        "magic": int(os.environ.get("AUTOTRADE_MAGIC", "999111")),
                                                        "comment": f"Qwen {risk_model}",
                                                        "type_time": mt5.ORDER_TIME_GTC,
                                                        "type_filling": mt5.ORDER_FILLING_IOC,
                                                    }
                                                    res = mt5.order_send(request)
                                                    if res is None:
                                                        err = mt5.last_error()
                                                        self.logger.error(f"Qwen MT5 OP Failed (None): {err}")
                                                        self.last_safety_reject_reason = f"MT5 Error: {err}"
                                                    elif res.retcode != mt5.TRADE_RETCODE_DONE:
                                                        self.logger.error(f"Qwen MT5 OP Failed: {res.comment}")
                                                        self.last_safety_reject_reason = f"Broker Reject: {res.comment}"
                                                    else:
                                                        self.last_v39_trade_time = current_time
                                                        self.logger.info(f"Qwen MT5 OP Success. Cooldown started.")
                                                        try:
                                                            from backend.engines.v39_causal.ml_state import save_trade_context
                                                            # Store scores to evaluate later when trade closes
                                                            save_trade_context(
                                                                ticket=res.order,
                                                                action=action,
                                                                macro_score=100 - macro_res.get("dxy_strength", 50),
                                                                tech_score=tech_score,
                                                                flow_score=flow_res.get("flow_score", 50),
                                                                mixed_prob=gate_res.get("calibrated_prob", 50)
                                                            )
                                                        except Exception as ml_err:
                                                            self.logger.error(f"Failed to save ML context: {ml_err}")
                                                else:
                                                    self.logger.error("V39 Engine Execution Failed (No Tick).")
                                                    self.last_safety_reject_reason = "No Tick Data"
                                    except Exception as e:
                                        self.logger.error(f"V39 Auto-Trade Error: {e}")
                                        self.last_safety_reject_reason = f"Error: {str(e)[:25]}"

                        if not hasattr(self, "last_narrative_time"): self.last_narrative_time = 0
                        if time.time() - self.last_narrative_time >= 1800:
                            self.last_narrative_time = time.time()
                            try:
                                from backend.telegram.zero_token_formatter import generate_ascii_narrative
                                # Get latest headline
                                headline = "Macro & Technical Dynamics"
                                if self.news_engine and hasattr(self.news_engine, 'news_feed') and len(self.news_engine.news_feed) > 0:
                                    headline = self.news_engine.news_feed[-1].get('headline', headline)
                                
                                cp = 0.0
                                try:
                                    tick = mt5.symbol_info_tick("XAUUSD")
                                    if tick: cp = tick.bid
                                except: pass
                                    
                                raw_ascii = generate_ascii_narrative(v39_payload, cp, headline)
                                
                                from backend.engines.qwen_writer import rewrite_narrative_with_qwen
                                narrative = await rewrite_narrative_with_qwen(raw_ascii)
                                
                                # Cache it for the UI as well
                                self.latest_narrative = narrative
                                
                                # Use notify_ascii_dashboard to keep the template perfectly aligned
                                if hasattr(self, "telegram"):
                                    await self.telegram.notify_ascii_dashboard(narrative)
                            except Exception as e:
                                logging.error(f"Auto-narrative generation failed: {e}")

                    # Fetch Qwen Autotrade Data
                    if is_mt5_ok:
                        try:
                            acc_info = mt5.account_info()
                            if acc_info is not None:
                                # Get active positions and apply Causal Supremacy Trailing Stop (1.5 ATR SL / 0.5 ATR Step)
                                pos_list = []
                                positions = mt5.positions_get(symbol="XAUUSD")
                                if positions:
                                    positions = [p for p in positions if getattr(p, 'magic', 0) == int(os.environ.get("AUTOTRADE_MAGIC", "999111"))]
                                if positions:
                                    rates_ts = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M15, 0, 14)
                                    atr_ts = 3.0
                                    if rates_ts is not None and len(rates_ts) > 0:
                                        tr_list = [max(rates_ts[i]['high'] - rates_ts[i]['low'], abs(rates_ts[i]['high'] - rates_ts[i-1]['close']), abs(rates_ts[i]['low'] - rates_ts[i-1]['close'])) for i in range(1, len(rates_ts))]
                                        if tr_list: atr_ts = sum(tr_list) / len(tr_list)
                                    atr_ts = max(2.0, min(15.0, atr_ts))
                                    
                                    tick_ts = mt5.symbol_info_tick("XAUUSD")
                                    
                                    for p in positions:
                                        if tick_ts:
                                            if p.type == mt5.ORDER_TYPE_BUY:
                                                if tick_ts.bid - p.price_open > (atr_ts * 0.5):
                                                    new_sl = tick_ts.bid - (atr_ts * 1.5)
                                                    if p.sl == 0.0 or new_sl > p.sl:
                                                        mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": new_sl, "tp": p.tp})
                                            elif p.type == mt5.ORDER_TYPE_SELL:
                                                if p.price_open - tick_ts.ask > (atr_ts * 0.5):
                                                    new_sl = tick_ts.ask + (atr_ts * 1.5)
                                                    if p.sl == 0.0 or new_sl < p.sl:
                                                        mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": new_sl, "tp": p.tp})
                                                        
                                        pos_list.append({
                                            "ticket": p.ticket,
                                            "time": getattr(p, 'time', 0),
                                            "type": "buy" if p.type == mt5.ORDER_TYPE_BUY else "sell",
                                            "volume": p.volume,
                                            "symbol": "XAUUSD",
                                            "price": p.price_open,
                                            "sl": p.sl,
                                            "tp": p.tp,
                                            "profit": p.profit
                                        })
                                        
                                # Get today's history
                                from datetime import datetime, timedelta
                                today = datetime.now()
                                start = datetime(today.year, today.month, today.day)
                                history = mt5.history_deals_get(start, today + timedelta(days=1))
                                hist_list = []
                                win_count = 0
                                loss_count = 0
                                if history:
                                    for d in history:
                                        if d.symbol == "XAUUSD" and d.entry == mt5.DEAL_ENTRY_OUT:
                                            pos_id = getattr(d, 'position_id', d.ticket)
                                            
                                            # Self-Learning: Evaluate Closed Trade (Safe to call on all, checks memory internally)
                                            try:
                                                from backend.engines.v39_causal.ml_state import evaluate_and_update_weights
                                                evaluate_and_update_weights(pos_id, d.profit)
                                            except Exception as ml_eval_err:
                                                self.logger.error(f"ML Eval Error: {ml_eval_err}")
                                                
                                            if getattr(d, 'magic', 0) == int(os.environ.get("AUTOTRADE_MAGIC", "999111")):
                                                open_time = 0
                                                open_price = 0.0
                                            sl = 0.0
                                            tp = 0.0
                                            deals = mt5.history_deals_get(position=pos_id)
                                            if deals:
                                                for deal in deals:
                                                    if deal.entry == mt5.DEAL_ENTRY_IN:
                                                        open_time = deal.time
                                                        open_price = deal.price
                                                        break
                                            orders = mt5.history_orders_get(position=pos_id)
                                            if orders:
                                                for o in orders:
                                                    if getattr(o, 'sl', 0) > 0: sl = o.sl
                                                    if getattr(o, 'tp', 0) > 0: tp = o.tp

                                            hist_list.append({
                                                "ticket": pos_id,
                                                "time": open_time,
                                                "time_close": d.time,
                                                "type": "buy" if d.type == mt5.DEAL_TYPE_SELL else "sell",
                                                "volume": d.volume,
                                                "symbol": getattr(d, 'symbol', "XAUUSD"),
                                                "price": open_price,
                                                "price_close": d.price,
                                                "sl": sl,
                                                "tp": tp,
                                                "profit": d.profit
                                            })
                                            if d.profit > 0: win_count += 1
                                            elif d.profit < 0: loss_count += 1
                                
                                total_trades = win_count + loss_count
                                winrate = (win_count / total_trades * 100) if total_trades > 0 else 0
                                
                                # Send to frontend
                                autotrade_payload = {
                                    "type": "qwen_autotrade_data",
                                    "account": {
                                        "balance": acc_info.balance,
                                        "equity": acc_info.equity,
                                        "margin_free": acc_info.margin_free,
                                        "profit": acc_info.profit,
                                        "winrate": winrate,
                                        "dd": 0 # MT5 doesn't easily expose DD
                                    },
                                    "live_trades": pos_list,
                                    "history_trades": hist_list[-50:]
                                }
                                # Broadcast unconditionally so new UI connections get it immediately
                                await ws_manager._broadcast_json(autotrade_payload)
                        except Exception as e:
                            import traceback
                            self.logger.error(f"Market Engine AI Loop Error: {e}\n{traceback.format_exc()}")
                            with open("market_engine_debug.log", "a") as f:
                                f.write(f"{e}\n{traceback.format_exc()}\n")
                        
                loop_counter += 1

                if is_mt5_ok:
                    for symbol in self.symbols:
                        tick = mt5.symbol_info_tick(symbol)
                        if tick:
                            tick_time_msc = getattr(tick, 'time_msc', tick.time * 1000)
                            if tick_time_msc > self.last_tick_time_msc.get(symbol, 0):
                                self.last_tick_time_msc[symbol] = tick_time_msc
                                await self.on_tick_received(symbol, tick.bid, tick.ask, tick.time)
            except Exception as e:
                self.logger.error(f"Error dalam _poll_ticks: {e}", exc_info=True)
            await asyncio.sleep(0.1)  # 100ms poll interval

    async def on_tick_received(self, symbol: str, bid: float, ask: float, time_sec: int):
        try:
            from backend.api.websocket import ws_manager
            # Broadcast to frontend
            await ws_manager.broadcast_tick(symbol, bid, ask, time_sec)
            
            # Process AI pipeline
            fs = self.feature_stores.get(symbol)
            if fs:
                await fs.process_tick(symbol, bid, ask, time_sec)
        except Exception as e:
            self.logger.error(f"Error dalam on_tick_received: {e}", exc_info=True)
