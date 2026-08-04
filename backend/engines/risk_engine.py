from .base_engine import BaseEngine
import json

class RiskEngine(BaseEngine):
    """
    Risk Engine: Validates trades against max drawdown and margin rules.
    """
    
    @property
    def engine_name(self) -> str:
        return "RiskEngine"

    def __init__(self, config=None, execution_engine=None):
        super().__init__(config)
        self.execution_engine = execution_engine
        self.news_engine = None
        self.max_daily_drawdown = self.config.get("max_daily_drawdown", 0.02)
        self.current_drawdown = 0.0
        self.autotrade_enabled = False # Starts disabled for safety until toggled from UI
        import os
        self.max_positions = int(os.environ.get("AVERAGING_MAX_POSITIONS", "3"))
        self.hedging_enabled = os.environ.get("HEDGING_ENABLED", "True").lower() == "true"
        self._trailing_task = None
        self._intra_candle_task = None
        self._logical_sls = {}
        self._hedge_locks = {}
        self.last_trade_time = 0.0
        self._highest_profits = {}

    async def start(self):
        self.logger.info("Risk engine online.")
        import asyncio
        self._trailing_task = asyncio.create_task(self._trailing_stop_loop())
        self._intra_candle_task = asyncio.create_task(self._intra_candle_scalper_loop())
        self._open_shift_close_task = asyncio.create_task(self._open_shift_close_loop())
        self._adaptive_task = asyncio.create_task(self._adaptive_portfolio_loop())
        self._forecast_hlc_task = asyncio.create_task(self._forecast_hlc_bound_loop())

    async def stop(self):
        if self._trailing_task:
            self._trailing_task.cancel()
        if self._intra_candle_task:
            self._intra_candle_task.cancel()
        if self._open_shift_close_task:
            self._open_shift_close_task.cancel()
        if hasattr(self, "_adaptive_task") and self._adaptive_task:
            self._adaptive_task.cancel()
        if hasattr(self, "_forecast_hlc_task") and self._forecast_hlc_task:
            self._forecast_hlc_task.cancel()
        self.logger.info("Risk engine offline.")

    async def validate_trade(self, signal: str, price: float, confidence: float = 0.5):
        """
        Validates if a trade can be taken based on current risk exposure and market sentiment.
        """
        if not self.autotrade_enabled:
            self.logger.info(f"AutoTrade is OFF. Trade request ignored: {signal} at {price}")
            return
            
        # Block raw DecisionEngine signals if running a loop-based quantitative strategy
        active_method = os.environ.get("ACTIVE_METHOD", "intra-candle-scalper")
        if active_method in ["forecast-hlc-bound", "intra-candle-scalper", "intra-candle-scalper-m5", "intra-candle-scalper-m15", "intra-candle-scalper-h1", "intra-candle-scalper-h4", "open-shift-close"]:
            self.logger.info(f"DecisionEngine Signal: Raw {signal} trade request ignored because active quantitative method is {active_method}")
            return
            
        # Debounce Filter (prevent multiple fast consecutive orders within 60 seconds)
        import time
        now = time.time()
        if now - self.last_trade_time < 60.0:
            self.logger.warning(f"Risk Reject: Debounce filter active. Last execution was {now - self.last_trade_time:.1f}s ago (Cooldown: 60s).")
            return
            
        import os
        import MetaTrader5 as mt5
        symbol = os.environ.get("TRADE_SYMBOL", "XAUUSD")
        
        # Default fallback values
        thresh = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.68"))
        max_op = int(os.environ.get("AVERAGING_MAX_POSITIONS", "4"))
        
        # Proactively refresh the session and dynamic parameters on the fly before checking entry constraints
        auto_lot = os.environ.get("AUTO_LOT_ENABLED", "False").lower() == "true"
        if auto_lot:
            import datetime
            utc_hour = datetime.datetime.utcnow().hour
            if utc_hour >= 22 or utc_hour < 8:
                session_name = "ASIA (Tokyo/Sydney)"
                lot = 0.40
                thresh = 0.65
                max_op = 4
            elif utc_hour >= 8 and utc_hour < 13:
                session_name = "LONDON (Europe)"
                lot = 0.30
                thresh = 0.68
                max_op = 4
            else:
                session_name = "NEW YORK (USA)"
                lot = 0.20
                thresh = 0.72
                max_op = 3
                
            self.config["lot_size"] = lot
            os.environ["BASE_LOT_SIZE"] = str(lot)
            
        # If Qwen AI has determined custom optimal parameters, we load those from the strategist engine (Always active)
        macro_strat = getattr(self, "macro_strategist", None)
        if not macro_strat and hasattr(self, "decision_engine") and self.decision_engine:
            macro_strat = getattr(self.decision_engine, "macro_strategist", None)
            
        if macro_strat:
            qwen_thresh = getattr(macro_strat, "optimal_confidence_threshold", None)
            qwen_max_op = getattr(macro_strat, "optimal_max_op", None)
            if qwen_thresh is not None: thresh = float(qwen_thresh)
            if qwen_max_op is not None: max_op = int(qwen_max_op)
            
        self.max_positions = max_op
        os.environ["AVERAGING_MAX_POSITIONS"] = str(max_op)
        self.logger.info(f"Entry parameter auto-refresh: Max OP={max_op}, Threshold={thresh}")
        
        # 1. News Cool-down Filter (15 minutes before or after high-impact news)
        if self.news_engine:
            high_impact_keywords = ["NFP", "CPI", "FOMC", "FED RATE", "INTEREST RATE", "PAYROLLS", "DECISION", "CENTRAL BANK"]
            
            for news in getattr(self.news_engine, "news_feed", []):
                headline = news.get("headline", "").upper()
                ts = news.get("timestamp", 0)
                if any(kw in headline for kw in high_impact_keywords):
                    age = abs(now - ts)
                    if age <= 900: # 15 minutes = 900 seconds
                        self.logger.warning(f"Risk Reject: Trade blocked by News Cool-down filter. High-Impact News: '{headline}' was published {age/60:.1f} minutes ago.")
                        return

        # Check if there is already an active position or pending order for the symbol to prevent multiple entries
        positions = mt5.positions_get(symbol=symbol)
        orders = mt5.orders_get(symbol=symbol)
        
        # Check if averaging is enabled
        averaging_enabled = os.environ.get("AVERAGING_ENABLED", "False").lower() == "true"
        
        is_averaging = False
        first_position_volume = None
        
        if (positions is not None and len(positions) > 0) or (orders is not None and len(orders) > 0):
            # Check global max positions limit
            if len(positions) >= self.max_positions:
                self.logger.info(f"Trade Blocked: Max global positions limit reached ({len(positions)}/{self.max_positions})")
                return
                
            # Filter positions of the same direction/type (0 = BUY, 1 = SELL)
            same_type_positions = [p for p in positions if p.type == (0 if signal == "BUY" else 1)]
            
            if len(same_type_positions) > 0:
                is_averaging = True
                # Get the oldest position in this direction to match its initial lot size
                first_pos = min(same_type_positions, key=lambda p: p.time)
                first_position_volume = float(first_pos.volume)
                
                if not averaging_enabled:
                    self.logger.info(f"Trade Blocked: Averaging is disabled and a position of direction {signal} already exists.")
                    return
                # We have open positions of the same type. Enforce spacing limit!
                avg_tf_name = os.environ.get("AVERAGING_TIMEFRAME", "M30")
                avg_mult = float(os.environ.get("AVERAGING_ATR_MULTIPLIER", "1.0"))
                
                tf_map = {
                    "M1": mt5.TIMEFRAME_M1,
                    "M5": mt5.TIMEFRAME_M5,
                    "M15": mt5.TIMEFRAME_M15,
                    "M30": mt5.TIMEFRAME_M30,
                    "H1": mt5.TIMEFRAME_H1,
                    "H4": mt5.TIMEFRAME_H4,
                    "D1": mt5.TIMEFRAME_D1
                }
                tf_const = tf_map.get(avg_tf_name, mt5.TIMEFRAME_M30)
                
                rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, 15)
                if rates is not None and len(rates) >= 15:
                    import numpy as np
                    highs = np.array([r[2] for r in rates])
                    lows = np.array([r[3] for r in rates])
                    closes = np.array([r[4] for r in rates])
                    
                    tr_list = []
                    for i in range(1, len(rates)):
                        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
                        tr_list.append(tr)
                    atr = float(np.mean(tr_list[-14:]))
                else:
                    atr = 9.09
                    
                # Adaptive Volatility & Market Session Spacing Adjustment
                import datetime
                utc_hour = datetime.datetime.now(datetime.timezone.utc).hour
                
                session_name = "Asian Session"
                session_mult = 0.8
                
                if utc_hour >= 8 and utc_hour < 13:
                    session_name = "European Session"
                    session_mult = 1.2
                elif utc_hour >= 13 and utc_hour < 17:
                    session_name = "London/NY Overlap"
                    session_mult = 2.2
                elif utc_hour >= 17 and utc_hour < 21:
                    session_name = "American Session"
                    session_mult = 1.8
                    
                avg_mult *= session_mult
                self.logger.info(f"Session Spacing: Current session: {session_name} (Hour: {utc_hour} UTC). Spacing multiplier adjusted to {avg_mult}x")
                
                regime = "Normal"
                if self.macro_strategist:
                    regime = getattr(self.macro_strategist, "volatility_regime", "Normal")
                
                # Stretch spacing by 2.0x during high news/volatility to prevent clustering grid positions
                if regime in ["HIGH_NEWS", "HIGH_VOLATILITY", "VIP (High Impact)"]:
                    avg_mult *= 2.0
                    self.logger.info(f"Dynamic Spacing: High volatility regime ({regime}) detected. Stretching grid multiplier to {avg_mult}x")
                    
                required_distance = atr * avg_mult
                
                # Get the last opened position of the same type
                last_pos = max(same_type_positions, key=lambda p: p.time)
                last_entry = float(last_pos.price_open)
                actual_distance = abs(price - last_entry)
                
                if actual_distance < required_distance:
                    self.logger.info(f"Trade Blocked: Price {price} is too close to last entry {last_entry} (Distance: {actual_distance:.2f} < Required: {required_distance:.2f})")
                    return
                    
                self.logger.info(f"Additional Position Triggered: Last Entry={last_entry}, Distance={actual_distance:.2f} >= Required={required_distance:.2f}")
            else:
                # No active positions of the same type exist (only opposing positions exist).
                # If hedging is enabled, this is allowed immediately without distance checks!
                if not self.hedging_enabled:
                    self.logger.info("Trade Blocked: Opposing active position exists, and Hedging is disabled.")
                    return
                self.logger.info(f"Hedging Entry Triggered: Opening {signal} opposite to current positions.")
            
        # Check Qwen3.7 Macro Strategist Bias
        if hasattr(self, "macro_strategist") and self.macro_strategist:
            bias = self.macro_strategist.macro_bias
            if bias == "WAIT":
                self.logger.warning(f"Risk Reject: Trade blocked by Macro Strategist Bias (WAIT)")
                return
            elif bias == "BUY_ONLY" and signal != "BUY":
                self.logger.warning(f"Risk Reject: {signal} blocked by Macro Strategist Bias (BUY_ONLY)")
                return
            elif bias == "SELL_ONLY" and signal != "SELL":
                self.logger.warning(f"Risk Reject: {signal} blocked by Macro Strategist Bias (SELL_ONLY)")
                return

        if self.current_drawdown >= self.max_daily_drawdown:
            self.logger.warning(f"Risk Reject: Max Drawdown Reached ({self.current_drawdown * 100:.2f}%)")
            return
            
        # Sentiment Execution Filter (GSI Composite)
        gsi_score = 50.0
        if self.news_engine:
            gsi_score = self.news_engine.current_sentiment_score
            
        # Calculate base volume based on Auto Lot settings and Risk Percent
        auto_lot = os.environ.get("AUTO_LOT_ENABLED", "False").lower() == "true"
        if auto_lot:
            acc = mt5.account_info()
            equity = acc.equity if acc else 10000.0
            risk_percent = float(os.environ.get("RISK_PERCENT", "1.0"))
            risk_usd = equity * (risk_percent / 100.0)
            
            # Retrieve ATR for dynamic SL distance calculation
            avg_tf_name = os.environ.get("AVERAGING_TIMEFRAME", "M30")
            tf_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1
            }
            tf_const = tf_map.get(avg_tf_name, mt5.TIMEFRAME_M30)
            rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, 15)
            atr = 9.09
            if rates is not None and len(rates) >= 15:
                import numpy as np
                highs = np.array([r[2] for r in rates])
                lows = np.array([r[3] for r in rates])
                closes = np.array([r[4] for r in rates])
                tr_list = []
                for i in range(1, len(rates)):
                    tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
                    tr_list.append(tr)
                atr = float(np.mean(tr_list[-14:]))
            
            # Read current SL multiplier from env or config (defaults to 1.5)
            sl_mult = float(os.environ.get("SL_MULTIPLIER", "1.5"))
            sl_distance = sl_mult * atr
            
            # Formula: base_volume = risk_amount / (SL_distance * contract_size)
            base_volume = risk_usd / (sl_distance * 100.0)
            base_volume = round(max(0.01, base_volume), 2)
            self.logger.info(f"Dynamic Auto LOT: Equity=${equity:.2f}, Risk={risk_percent}%, SL Distance={sl_distance:.2f} USD. Calculated Base Volume={base_volume} Lot")
        else:
            base_volume = float(os.environ.get("LOT_SIZE", "0.10"))
        
        # 2. Confidence-Based Sizing (Dynamic Lot Sizing)
        prob = confidence if signal == "BUY" else (1.0 - confidence)
        if prob <= 0.70:
            volume = base_volume * 0.5
            self.logger.info(f"AI Sizing: Low Confidence ({prob:.2f}), scaling lot from {base_volume} to {volume}")
        elif prob <= 0.80:
            volume = base_volume
            self.logger.info(f"AI Sizing: Normal Confidence ({prob:.2f}), lot set to {base_volume}")
        else:
            volume = base_volume * 1.5
            self.logger.info(f"AI Sizing: High Confidence ({prob:.2f}), scaling lot from {base_volume} to {volume}")
            
        volume = round(max(0.01, volume), 2)
        
        # Sentiment Filter (Scale or Reject)
        if signal == "BUY":
            if gsi_score < 30.0:
                self.logger.warning(f"Risk Reject: BUY order blocked due to severe BEARISH GSI index ({gsi_score:.1f}% < 30.0%)")
                return
            elif gsi_score < 35.0:
                scaled_volume = round(max(0.01, volume * 0.5), 2)
                self.logger.warning(f"Sentiment Filter: Scaling BUY lot from {volume} to {scaled_volume} due to BEARISH GSI index ({gsi_score:.1f}%)")
                volume = scaled_volume
        elif signal == "SELL":
            if gsi_score > 70.0:
                self.logger.warning(f"Risk Reject: SELL order blocked due to severe BULLISH GSI index ({gsi_score:.1f}% > 70.0%)")
                return
            elif gsi_score > 65.0:
                scaled_volume = round(max(0.01, volume * 0.5), 2)
                self.logger.warning(f"Sentiment Filter: Scaling SELL lot from {volume} to {scaled_volume} due to BULLISH GSI index ({gsi_score:.1f}%)")
                volume = scaled_volume
            
        if is_averaging and first_position_volume is not None:
            volume = first_position_volume
            self.logger.info(f"Grid Averaging Match: Overriding dynamic lot size with oldest grid position volume: {volume} Lot to maintain grid balance.")
            
        self.logger.info(f"Risk Approved: {signal} {volume} Lot at {price}")
        if self.execution_engine:
            import time
            self.last_trade_time = time.time()
            await self.execution_engine.execute_order(symbol, signal, volume)

    async def _trailing_stop_loop(self):
        """
        Background trailing stop loop running every 5 seconds.
        Performs:
        1. Basket Take Profit Closeout (Hedge Recovery).
        2. Consolidated Basket SL/TP Synchronization (Disaster SL on MT5, Logical SL tracked in memory).
        3. Trailing Stop / Breakeven Lock on individual standalone positions.
        4. Dynamic Hedge Locking (Hedge-Lock trigger at logical SL).
        5. AI Review Loop (Analyzes macroeconomic bias after 15 minutes to resolve the hedge).
        """
        import asyncio
        import MetaTrader5 as mt5
        import os
        import time
        import numpy as np
        
        while True:
            try:
                if mt5.initialize():
                    symbol = os.environ.get("TRADE_SYMBOL", "XAUUSD")
                    positions = mt5.positions_get(symbol=symbol)
                    
                    # 5. AI Review Loop (15 minutes after hedge lock)
                    now_time = time.time()
                    resolved_tickets = []
                    for orig_ticket, lock_info in list(self._hedge_locks.items()):
                        age = now_time - lock_info["lock_time"]
                        if age >= 900: # 15 minutes = 900 seconds
                            bias = "WAIT"
                            if hasattr(self, "macro_strategist") and self.macro_strategist:
                                bias = self.macro_strategist.macro_bias
                                
                            opp_ticket = lock_info["opposing_ticket"]
                            
                            if bias == "SELL_ONLY" and lock_info["type"] == 0: # Original BUY, locked by SELL
                                # Confirm downtrend: close original BUY position
                                if self.execution_engine:
                                    self.logger.info(f"AI Hedge Review: Trend confirmed DOWN. Closing original BUY #{orig_ticket}.")
                                    await self.execution_engine.close_position(orig_ticket)
                                    if hasattr(self.execution_engine, "notifier") and self.execution_engine.notifier:
                                        msg = (
                                            f"🧠 <b>AI RESOLVED HEDGE: TREND DOWN CONFIRMED</b>\n\n"
                                            f"Analisis 15 menit pasca-berita mengkonfirmasi tren turun (bias: SELL_ONLY).\n"
                                            f"Memotong rugi posisi BUY #{orig_ticket} dan membiarkan posisi SELL #{opp_ticket} berjalan."
                                        )
                                        await self.execution_engine.notifier._send_safe(msg)
                                resolved_tickets.append(orig_ticket)
                            elif bias == "BUY_ONLY" and lock_info["type"] == 1: # Original SELL, locked by BUY
                                # Confirm uptrend: close original SELL position
                                if self.execution_engine:
                                    self.logger.info(f"AI Hedge Review: Trend confirmed UP. Closing original SELL #{orig_ticket}.")
                                    await self.execution_engine.close_position(orig_ticket)
                                    if hasattr(self.execution_engine, "notifier") and self.execution_engine.notifier:
                                        msg = (
                                            f"🧠 <b>AI RESOLVED HEDGE: TREND UP CONFIRMED</b>\n\n"
                                            f"Analisis 15 menit pasca-berita mengkonfirmasi tren naik (bias: BUY_ONLY).\n"
                                            f"Memotong rugi posisi SELL #{orig_ticket} dan membiarkan posisi BUY #{opp_ticket} berjalan."
                                        )
                                        await self.execution_engine.notifier._send_safe(msg)
                                resolved_tickets.append(orig_ticket)
                                
                    for t in resolved_tickets:
                        self._hedge_locks.pop(t, None)
                        self._logical_sls.pop(t, None)

                    if positions:
                        # 1. Dynamic Basket Take Profit (Volume-Weighted Recovery)
                        combined_profit = sum(float(p.profit) for p in positions)
                        total_volume = sum(float(p.volume) for p in positions)
                        
                        # Scale target profit: $15.00 for every 0.10 lot size (e.g. 1.0 lot targets $150.00)
                        dynamic_target = (total_volume / 0.10) * 15.00
                        
                        # Adjust target based on current market session
                        import datetime
                        utc_hour = datetime.datetime.now(datetime.timezone.utc).hour
                        if utc_hour >= 0 and utc_hour < 8: # Asian Session (chop): Exit quickly!
                            dynamic_target *= 0.7
                        elif utc_hour >= 13 and utc_hour < 21: # US Session (trend): Hold for more!
                            dynamic_target *= 1.3
                            
                        basket_tp = max(5.00, round(dynamic_target, 2))
                        
                        if len(positions) >= 2 and combined_profit >= basket_tp:
                            self.logger.info(f"AI Basket Target Achieved: Combined Profit {combined_profit:.2f} >= Dynamic Target {basket_tp:.2f} (Vol: {total_volume:.2f} Lot). Closing all positions!")
                            if self.execution_engine:
                                await self.execution_engine.close_all_positions()
                            continue
                            
                        # Calculate ATR for SL/TP calculations
                        avg_tf_name = os.environ.get("AVERAGING_TIMEFRAME", "M30")
                        tf_map = {
                            "M1": mt5.TIMEFRAME_M1,
                            "M5": mt5.TIMEFRAME_M5,
                            "M15": mt5.TIMEFRAME_M15,
                            "M30": mt5.TIMEFRAME_M30,
                            "H1": mt5.TIMEFRAME_H1,
                            "H4": mt5.TIMEFRAME_H4,
                            "D1": mt5.TIMEFRAME_D1
                        }
                        tf_const = tf_map.get(avg_tf_name, mt5.TIMEFRAME_M30)
                        rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, 15)
                        if rates is not None and len(rates) >= 15:
                            highs = np.array([r[2] for r in rates])
                            lows = np.array([r[3] for r in rates])
                            closes = np.array([r[4] for r in rates])
                            tr_list = []
                            for i in range(1, len(rates)):
                                tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
                                tr_list.append(tr)
                            atr = float(np.mean(tr_list[-14:]))
                        else:
                            atr = 9.09
                            
                        sl_mult = 1.5
                        tp_mult = 3.0
                        if hasattr(self, "macro_strategist") and self.macro_strategist:
                            sl_mult = self.macro_strategist.sl_mult
                            tp_mult = self.macro_strategist.tp_mult

                        # 2. Consolidated Basket SL/TP Synchronization
                        for direction in [0, 1]: # 0 = BUY, 1 = SELL
                            dir_positions = [p for p in positions if p.type == direction]
                            if len(dir_positions) >= 2:
                                total_vol = sum(p.volume for p in dir_positions)
                                weighted_sum = sum(p.price_open * p.volume for p in dir_positions)
                                avg_entry = weighted_sum / total_vol
                                
                                if direction == 0: # BUY
                                    logical_sl = round(avg_entry - (sl_mult * atr), 2)
                                    disaster_sl = round(avg_entry - (sl_mult * atr * 3.0), 2)
                                    target_tp = round(avg_entry + (tp_mult * atr), 2)
                                if direction == 1: # SELL
                                    logical_sl = round(avg_entry + (sl_mult * atr), 2)
                                    disaster_sl = round(avg_entry + (sl_mult * atr * 3.0), 2)
                                    target_tp = round(avg_entry - (tp_mult * atr), 2)
                                    
                                for p in dir_positions:
                                    self._logical_sls[p.ticket] = logical_sl
                                    if abs(float(p.sl) - disaster_sl) > 0.05 or abs(float(p.tp) - target_tp) > 0.05:
                                        self.logger.info(f"Syncing Basket Position #{p.ticket}: Modifying SL to Disaster {disaster_sl}, TP to {target_tp} (Based on Average Entry: {avg_entry:.2f})")
                                        self._modify_position_sl(p.ticket, disaster_sl, target_tp)
                                        
                        # 3. Individual position trailing stop logic
                        for p in positions:
                            ticket = p.ticket
                            p_type = p.type # 0 = BUY, 1 = SELL
                            entry_price = float(p.price_open)
                            current_price = float(p.price_current)
                            current_sl = float(p.sl)
                            
                            same_dir_count = sum(1 for pos in positions if pos.type == p_type)
                            
                            # Handle standalone target logical SL & disaster SL
                            if same_dir_count == 1:
                                if p_type == 0: # BUY
                                    logical_sl = round(entry_price - (sl_mult * atr), 2)
                                    disaster_sl = round(entry_price - (sl_mult * atr * 3.0), 2)
                                else: # SELL
                                    logical_sl = round(entry_price + (sl_mult * atr), 2)
                                    disaster_sl = round(entry_price + (sl_mult * atr * 3.0), 2)
                                    
                                self._logical_sls[ticket] = logical_sl
                                if abs(current_sl - disaster_sl) > 0.05:
                                    self._modify_position_sl(ticket, disaster_sl, p.tp)
                                    
                            # 4. Dynamic Hedge Locking (Check if price hit logical SL)
                            logical_sl = self._logical_sls.get(ticket)
                            if logical_sl:
                                hit_hedge = False
                                if p_type == 0 and current_price <= logical_sl:
                                    hit_hedge = True
                                elif p_type == 1 and current_price >= logical_sl:
                                    hit_hedge = True
                                    
                                if hit_hedge and ticket not in self._hedge_locks:
                                    opp_action = "SELL" if p_type == 0 else "BUY"
                                    self.logger.warning(f"Logical SL hit at {logical_sl} for Position #{ticket}. Triggering Hedge Lock: {opp_action} {p.volume} Lot.")
                                    
                                    if self.execution_engine:
                                        res = await self.execution_engine.execute_order(symbol, opp_action, p.volume)
                                        if res.get("status") == "success":
                                            opp_ticket = int(res.get("ticket"))
                                            self._hedge_locks[ticket] = {
                                                "lock_time": time.time(),
                                                "opposing_ticket": opp_ticket,
                                                "volume": p.volume,
                                                "type": p_type
                                            }
                                            
                                            # Send Telegram notification
                                            if hasattr(self.execution_engine, "notifier") and self.execution_engine.notifier:
                                                msg = (
                                                    f"🔒 <b>HEDGE LOCK DIPICU (HEDGE ACTIVATED)</b>\n\n"
                                                    f"Posisi #{ticket} ({'BUY' if p_type == 0 else 'SELL'}) menyentuh SL logis di {logical_sl}.\n"
                                                    f"Membuka posisi kunci lawan #{opp_ticket} ({opp_action}) sebesar {p.volume} lot untuk membekukan kerugian."
                                                )
                                                await self.execution_engine.notifier._send_safe(msg)

                            # Method 10: Hybrid (Trailing Stop + Dynamic Break-Even) Exits
                            if ticket not in self._hedge_locks:
                                pips = (current_price - entry_price) if p_type == 0 else (entry_price - current_price)
                                usd_profit = pips * 100.0 * float(p.volume)
                                 
                                # Track peak profit achieved by this ticket
                                if ticket not in self._highest_profits:
                                    self._highest_profits[ticket] = 0.0
                                if usd_profit > self._highest_profits[ticket]:
                                    self._highest_profits[ticket] = usd_profit
                                     
                                peak_prof = self._highest_profits[ticket]
                                should_exit = False
                                exit_reason = ""
                                 
                                # 1. Trailing Stop Lock-in ($60 trigger, exit at 50% retracement)
                                if peak_prof >= 60.0 and usd_profit < (peak_prof * 0.5):
                                    should_exit = True
                                    exit_reason = f"Trailing Lock-in (Peak: ${peak_prof:.2f}, Current: ${usd_profit:.2f})"
                                # 2. Dynamic Break-Even ($30 trigger, exit at $0.00 or reversal)
                                elif peak_prof >= 30.0 and usd_profit <= 0.0:
                                    should_exit = True
                                    exit_reason = f"Break-Even Protection (Peak: ${peak_prof:.2f}, Current: ${usd_profit:.2f})"
                                     
                                if should_exit and self.execution_engine:
                                    self.logger.info(f"AI Exit Triggered for Position #{ticket}: {exit_reason}. Closing position!")
                                    await self.execution_engine.close_position(ticket)
                                    self._highest_profits.pop(ticket, None)
                                     
                                    # Send Telegram Notification
                                    if hasattr(self.execution_engine, "notifier") and self.execution_engine.notifier:
                                        msg = (
                                            f"👑 <b>AI HYBRID EXIT EXECUTED (METHOD 10)</b>\n\n"
                                            f"Posisi #{ticket} ({'BUY' if p_type == 0 else 'SELL'}) telah ditutup otomatis.\n"
                                            f"• <b>Alasan</b>: <code>{exit_reason}</code>\n"
                                            f"• <b>Lot Size</b>: <code>{p.volume} Lot</code>\n"
                                            f"• <b>Profit Terkunci</b>: <code>${usd_profit:.2f}</code>"
                                        )
                                        await self.execution_engine.notifier._send_safe(msg)
            except Exception as e:
                self.logger.error(f"Error in trailing stop loop: {e}")
            await asyncio.sleep(5)

    def _modify_position_sl(self, ticket: int, sl: float, tp: float):
        import MetaTrader5 as mt5
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": sl,
            "tp": tp
        }
        res = mt5.order_send(request)
        if res.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(f"Breakeven Locked: Moved SL of Position #{ticket} to {sl} (Profit Protected)")
        else:
            self.logger.warning(f"Failed to move SL of Position #{ticket} to {sl}: {res.comment}")

    async def _intra_candle_scalper_loop(self):
        import asyncio
        import MetaTrader5 as mt5
        import os
        import pandas as pd
        import numpy as np
        
        last_bar_time = 0
        
        while True:
            try:
                active_method = os.environ.get("ACTIVE_METHOD", "intra-candle-scalper")
                if active_method in ["intra-candle-scalper", "intra-candle-scalper-m15", "intra-candle-scalper-m5", "intra-candle-scalper-h1", "intra-candle-scalper-h4"] and self.autotrade_enabled:
                    symbol = os.environ.get("TRADE_SYMBOL", "XAUUSD")
                    if active_method == "intra-candle-scalper-m5":
                        tf = mt5.TIMEFRAME_M5
                    elif active_method == "intra-candle-scalper-m15":
                        tf = mt5.TIMEFRAME_M15
                    elif active_method == "intra-candle-scalper-h1":
                        tf = mt5.TIMEFRAME_H1
                    elif active_method == "intra-candle-scalper-h4":
                        tf = mt5.TIMEFRAME_H4
                    else:
                        tf = mt5.TIMEFRAME_M30
                    
                    # 1. Fetch current candle info
                    rates = mt5.copy_rates_from_pos(symbol, tf, 0, 15)
                    if rates is not None and len(rates) >= 15:
                        current_bar = rates[-1]
                        current_bar_time = int(current_bar[0])
                        open_price = float(current_bar[1])
                        
                        # Calculate ATR (14)
                        closes = np.array([r[4] for r in rates])
                        highs = np.array([r[2] for r in rates])
                        lows = np.array([r[3] for r in rates])
                        
                        tr_list = []
                        for i in range(1, len(rates)):
                            tr = max(highs[i] - lows[i], max(abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
                            tr_list.append(tr)
                        atr = float(np.mean(tr_list[-14:]))
                        
                        # 2. Check if a new M30 candle has opened!
                        if current_bar_time > last_bar_time:
                            last_bar_time = current_bar_time
                            
                            # Safety check: limit total active positions
                            existing_positions = mt5.positions_get(symbol=symbol)
                            max_pos = int(os.environ.get("AVERAGING_MAX_POSITIONS", "6"))
                            if existing_positions and len(existing_positions) >= max_pos:
                                self.logger.info(f"Intra-Candle Scalper: Active positions ({len(existing_positions)}) >= Max allowed ({max_pos}). Skipping new pending orders.")
                                continue
                                
                            # Close any remaining open positions on the symbol from the previous candle
                            if self.execution_engine:
                                active_positions = mt5.positions_get(symbol=symbol)
                                if active_positions:
                                    self.logger.info(f"Intra-Candle: Closing {len(active_positions)} active positions from previous bar to align with model...")
                                    for p in active_positions:
                                        await self.execution_engine.close_position(p.ticket)
                                        
                            self.logger.info(f"New candle detected at timestamp {current_bar_time}. Executing Intra-Candle Scalper...")
                            
                            # Clean up old pending orders from previous bar
                            orders = mt5.orders_get(symbol=symbol)
                            if orders:
                                for o in orders:
                                    if o.type in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_SELL_LIMIT]:
                                        req = {
                                            "action": mt5.TRADE_ACTION_REMOVE,
                                            "order": o.ticket
                                        }
                                        mt5.order_send(req)
                                            
                            # Place new limit orders
                            lot_size = float(os.environ.get("LOT_SIZE", "0.10"))
                            buy_limit = open_price - atr * 0.05
                            buy_tp = buy_limit + atr * 0.08
                            buy_sl = buy_limit - atr * 1.0
                            
                            sell_limit = open_price + atr * 0.05
                            sell_tp = sell_limit - atr * 0.08
                            sell_sl = sell_limit + atr * 1.0
                            
                            # Send Limit Orders via execution engine
                            # BUY LIMIT
                            req_buy = {
                                "action": mt5.TRADE_ACTION_PENDING,
                                "symbol": symbol,
                                "volume": lot_size,
                                "type": mt5.ORDER_TYPE_BUY_LIMIT,
                                "price": buy_limit,
                                "sl": buy_sl,
                                "tp": buy_tp,
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": mt5.ORDER_FILLING_IOC
                            }
                            # SELL LIMIT
                            req_sell = {
                                "action": mt5.TRADE_ACTION_PENDING,
                                "symbol": symbol,
                                "volume": lot_size,
                                "type": mt5.ORDER_TYPE_SELL_LIMIT,
                                "price": sell_limit,
                                "sl": sell_sl,
                                "tp": sell_tp,
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": mt5.ORDER_FILLING_IOC
                            }
                            
                            # Let's adjust filling type dynamically for the broker account
                            acc = mt5.account_info()
                            filling = mt5.ORDER_FILLING_FOK
                            if acc and "FXT" in getattr(acc, "company", ""):
                                filling = mt5.ORDER_FILLING_IOC
                            
                            req_buy["type_filling"] = filling
                            req_sell["type_filling"] = filling
                            
                            res1 = mt5.order_send(req_buy)
                            res2 = mt5.order_send(req_sell)
                            self.logger.info(f"Placed M30 pending limit orders. Buy Limit={buy_limit:.2f}, Sell Limit={sell_limit:.2f}")
                            
            except Exception as e:
                self.logger.error(f"Error in _intra_candle_scalper_loop: {e}", exc_info=True)
            await asyncio.sleep(5)

    async def _open_shift_close_loop(self):
        import asyncio
        import MetaTrader5 as mt5
        import os
        import pandas as pd
        import numpy as np
        
        last_bar_time = 0
        
        while True:
            try:
                active_method = os.environ.get("ACTIVE_METHOD", "intra-candle-scalper")
                if active_method == "open-shift-close" and self.autotrade_enabled:
                    symbol = os.environ.get("TRADE_SYMBOL", "XAUUSD")
                    tf = mt5.TIMEFRAME_M30
                    
                    # Fetch rates (need at least 50 bars to calculate EMA 25 accurately)
                    rates = mt5.copy_rates_from_pos(symbol, tf, 0, 50)
                    if rates is not None and len(rates) >= 30:
                        current_bar = rates[-1]
                        current_bar_time = int(current_bar[0])
                        open_price = float(current_bar[1])
                        
                        # Calculate EMA 5 and EMA 15 on past rates (excluding the current uncompleted bar)
                        closes = np.array([r[4] for r in rates[:-1]])
                        highs = np.array([r[2] for r in rates[:-1]])
                        lows = np.array([r[3] for r in rates[:-1]])
                        
                        df_temp = pd.DataFrame(rates[:-1])
                        ema_fast = df_temp[4].ewm(span=5, adjust=False).mean().iloc[-1]
                        ema_slow = df_temp[4].ewm(span=15, adjust=False).mean().iloc[-1]
                        
                        # Calculate ATR (14)
                        tr_list = []
                        for i in range(1, len(df_temp)):
                            tr = max(highs[i] - lows[i], max(abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
                            tr_list.append(tr)
                        atr = float(np.mean(tr_list[-14:]))
                        
                        if current_bar_time > last_bar_time:
                            last_bar_time = current_bar_time
                            self.logger.info(f"New M30 candle detected at timestamp {current_bar_time}. Running Open Shift Close (Breakout Stop) strategy...")
                            
                            is_bullish_cross = ema_fast > ema_slow
                            is_bearish_cross = ema_fast < ema_slow
                            
                            # Check Qwen AI Macro Bias
                            qwen_bias = "ANY"
                            if hasattr(self, "macro_strategist") and self.macro_strategist:
                                qwen_bias = getattr(self.macro_strategist, "macro_bias", "ANY")
                            
                            # Cancel existing pending stop orders on this symbol
                            orders = mt5.orders_get(symbol=symbol)
                            if orders:
                                for o in orders:
                                    if o.type in [mt5.ORDER_TYPE_BUY_STOP, mt5.ORDER_TYPE_SELL_STOP]:
                                        cancel_req = {
                                            "action": mt5.TRADE_ACTION_REMOVE,
                                            "order": o.ticket
                                        }
                                        mt5.order_send(cancel_req)
                                        self.logger.info(f"Open Shift Close: Cancelled old pending order #{o.ticket}")
                            
                            # Check active positions on the symbol
                            active_positions = mt5.positions_get(symbol=symbol)
                            
                            # Shift logic
                            if active_positions:
                                for p in active_positions:
                                    should_close = False
                                    if p.type == mt5.POSITION_TYPE_BUY:
                                        if is_bearish_cross or qwen_bias in ["SELL_ONLY", "WAIT"]:
                                            should_close = True
                                    elif p.type == mt5.POSITION_TYPE_SELL:
                                        if is_bullish_cross or qwen_bias in ["BUY_ONLY", "WAIT"]:
                                            should_close = True
                                        
                                    if should_close:
                                        self.logger.info(f"Open Shift Close: Trend/AI shift detected. Closing position #{p.ticket}...")
                                        await self.execution_engine.close_position(p.ticket)
                                        
                            # Re-fetch positions after closures
                            active_positions = mt5.positions_get(symbol=symbol)
                            
                            # Open new position if none active
                            if not active_positions and qwen_bias != "WAIT":
                                lot_size = float(os.environ.get("LOT_SIZE", "0.20"))
                                acc = mt5.account_info()
                                filling = mt5.ORDER_FILLING_FOK
                                if acc and "FXT" in getattr(acc, "company", ""):
                                    filling = mt5.ORDER_FILLING_IOC
                                    
                                if is_bullish_cross and qwen_bias in ["BUY_ONLY", "ANY"]:
                                    stop_price = float(current_bar[2]) + atr * 0.05
                                    tp_price = stop_price + atr * 3.0
                                    sl_price = stop_price - atr * 2.5
                                    req = {
                                        "action": mt5.TRADE_ACTION_PENDING,
                                        "symbol": symbol,
                                        "volume": lot_size,
                                        "type": mt5.ORDER_TYPE_BUY_STOP,
                                        "price": stop_price,
                                        "sl": sl_price,
                                        "tp": tp_price,
                                        "type_time": mt5.ORDER_TIME_GTC,
                                        "type_filling": filling
                                    }
                                    mt5.order_send(req)
                                    self.logger.info(f"Open Shift Close: Placed BUY STOP order at {stop_price:.2f} (TP={tp_price:.2f}, SL={sl_price:.2f})")
                                elif is_bearish_cross and qwen_bias in ["SELL_ONLY", "ANY"]:
                                    stop_price = float(current_bar[3]) - atr * 0.05
                                    tp_price = stop_price - atr * 3.0
                                    sl_price = stop_price + atr * 2.5
                                    req = {
                                        "action": mt5.TRADE_ACTION_PENDING,
                                        "symbol": symbol,
                                        "volume": lot_size,
                                        "type": mt5.ORDER_TYPE_SELL_STOP,
                                        "price": stop_price,
                                        "sl": sl_price,
                                        "tp": tp_price,
                                        "type_time": mt5.ORDER_TIME_GTC,
                                        "type_filling": filling
                                    }
                                    mt5.order_send(req)
                                    self.logger.info(f"Open Shift Close: Placed SELL STOP order at {stop_price:.2f} (TP={tp_price:.2f}, SL={sl_price:.2f})")
                                    
            except Exception as e:
                self.logger.error(f"Error in _open_shift_close_loop: {e}", exc_info=True)
            await asyncio.sleep(5)

    async def _adaptive_portfolio_loop(self):
        import asyncio
        import os
        import MetaTrader5 as mt5
        import numpy as np
        import time
        
        while True:
            try:
                self.logger.info("Adaptive Portfolio: Running daily strategy optimization based on MAE/MFE/PnL feedback...")
                
                # Fetch trade history from MT5 for the last 30 days
                from_date = time.time() - 30 * 24 * 60 * 60
                deals = mt5.history_deals_get(from_date, time.time())
                
                if deals and len(deals) > 5:
                    self.logger.info(f"Adaptive Portfolio: Analyzing {len(deals)} recent trade deals...")
                    
                    # Export closed trades to data/closed_trades.json for cloud self-learning fallback
                    raw_trades = []
                    for d in deals:
                        if d.entry == 1:
                            raw_trades.append({
                                "time": int(d.time),
                                "profit": float(d.profit),
                                "symbol": str(d.symbol),
                                "volume": float(d.volume)
                            })
                    os.makedirs("data", exist_ok=True)
                    with open("data/closed_trades.json", "w") as tf:
                        json.dump(raw_trades, tf, indent=2)
                        
                    # Filter out non-trading deals (like deposits/adjustments) and get profits of out deals
                    profits = [d.profit for d in deals if d.entry == 1]
                    if len(profits) > 0:
                        winrate = sum(1 for p in profits if p > 0) / len(profits)
                        avg_win = np.mean([p for p in profits if p > 0]) if any(p > 0 for p in profits) else 10.0
                        avg_loss = abs(np.mean([p for p in profits if p < 0])) if any(p < 0 for p in profits) else 10.0
                        
                        payoff = avg_win / avg_loss if avg_loss > 0 else 1.0
                        f_star = winrate - (1.0 - winrate) / payoff
                        
                        # Apply Fractional Kelly Sizing (0.25 multiplier)
                        optimal_risk = max(0.5, min(4.0, f_star * 0.25 * 100.0))
                        os.environ["RISK_PERCENT"] = f"{optimal_risk:.2f}"
                        self.logger.info(f"Adaptive Sizing: Dynamic Kelly Sizing updated to {optimal_risk:.2f}% per trade based on MAE/MFE feedback loop.")
                        
                        # Dynamic Regime Selection
                        if winrate > 0.55:
                            os.environ["ACTIVE_METHOD"] = "scalping-1-1"
                            self.logger.info("Adaptive Portfolio: Dynamic regime shifted to 'scalping-1-1' (High Winrate Scalper).")
                        elif winrate >= 0.42:
                            os.environ["ACTIVE_METHOD"] = "open-shift-close"
                            self.logger.info("Adaptive Portfolio: Dynamic regime shifted to 'open-shift-close-breakout' (Stable Breakout).")
                        else:
                            os.environ["ACTIVE_METHOD"] = "fixed-micro-scalping"
                            self.logger.info("Adaptive Portfolio: Dynamic regime shifted to 'fixed-micro-scalping' (Low-Risk Safety Guard).")
                else:
                    self.logger.info("Adaptive Portfolio: Insufficient trade history. Defaulting to breakout stop-entry mode.")
                    os.environ["ACTIVE_METHOD"] = "open-shift-close"
                    
            except Exception as e:
                self.logger.error(f"Error in _adaptive_portfolio_loop: {e}", exc_info=True)
                
            await asyncio.sleep(86400)

    async def _forecast_hlc_bound_loop(self):
        """
        Background loop for the Forecast HLC Boundary trading method.
        Runs every 30 seconds to place instant market orders and layered pullback limit orders
        using dynamic distance scaling, volume weighting, and auto-hedge safety locks.
        """
        import asyncio
        import MetaTrader5 as mt5
        import os
        import json
        
        while True:
            try:
                active_method = os.environ.get("ACTIVE_METHOD", "intra-candle-scalper")
                if active_method == "forecast-hlc-bound" and self.autotrade_enabled:
                    symbol = os.environ.get("TRADE_SYMBOL", "XAUUSD")
                    
                    # 1. Fetch latest optimized forecasts
                    cache_path = "data/backtest_cache.json"
                    pred_high = None
                    pred_low = None
                    pred_close = None
                    
                    if os.path.exists(cache_path):
                        try:
                            with open(cache_path, "r", encoding="utf-8") as f:
                                bt_cache = json.load(f)
                                d1_list = bt_cache.get("detail_1d", [])
                                if d1_list:
                                    latest = d1_list[-1]
                                    pred_high = float(latest.get("pred_high"))
                                    pred_low = float(latest.get("pred_low"))
                                    pred_close = float(latest.get("pred_close"))
                        except Exception as e:
                            self.logger.error(f"Failed to load forecast cache in loop: {e}")
                            
                    # 2. If forecast is not loaded, fallback to default ATR bounds
                    if pred_high is None or pred_low is None or pred_close is None:
                        tick = mt5.symbol_info_tick(symbol)
                        if tick:
                            pred_close = tick.bid
                            pred_high = tick.bid + 15.0
                            pred_low = tick.bid - 15.0
                            
                    if mt5.initialize() and pred_high and pred_low and pred_close:
                        tick = mt5.symbol_info_tick(symbol)
                        if not tick:
                            continue
                            
                        # Spread Protection Filter (Max 3.5 USD / 35 pips on Gold)
                        spread = tick.ask - tick.bid
                        max_allowed_spread = 3.5
                        if spread > max_allowed_spread:
                            self.logger.warning(f"HLC Strategy: Order placement skipped due to high broker spread: {spread:.2f} (Max allowed: {max_allowed_spread})")
                            continue
                            
                        # 3. Check current positions and pending orders
                        positions = mt5.positions_get(symbol=symbol)
                        orders = mt5.orders_get(symbol=symbol)
                        
                        has_positions = positions is not None and len(positions) > 0
                        has_orders = orders is not None and len(orders) > 0
                        
                        # 4. Resolve Macro Bias
                        bias = "ANY"
                        macro_strat = getattr(self, "macro_strategist", None)
                        if not macro_strat and hasattr(self, "decision_engine") and self.decision_engine:
                            macro_strat = getattr(self.decision_engine, "macro_strategist", None)
                        if macro_strat:
                            bias = getattr(macro_strat, "macro_bias", "ANY")
                            
                        # 5. Calculation parameters
                        mid = (pred_high + pred_low) / 2.0
                        grid_range = pred_high - pred_low
                        grid_dist = grid_range / 3.0
                        
                        # Get broker volume constraints dynamically to avoid Error 10014 (Invalid Volume)
                        sym_info = mt5.symbol_info(symbol)
                        vol_step = 0.01
                        vol_min = 0.01
                        vol_max = 500.0
                        if sym_info is not None:
                            vol_step = float(sym_info.volume_step)
                            vol_min = float(sym_info.volume_min)
                            vol_max = float(sym_info.volume_max)
                            
                        def normalize_vol(v):
                            v_norm = round(v / vol_step) * vol_step
                            return max(vol_min, min(vol_max, round(v_norm, 2)))
                            
                        base_lot = normalize_vol(float(os.environ.get("LOT_SIZE", "0.10")))
                        
                        # 6. Resolve Regime
                        regime = "NORMAL"
                        if macro_strat:
                            regime = getattr(macro_strat, "volatility_regime", "NORMAL")
                            
                        # A. Sideways Range Repeater Logic (Repeated buy low / sell high in range)
                        if regime == "SIDEWAYS" and bias == "ANY":
                            # Arm BUY Limit at low boundary if no active BUY position/order
                            buy_positions = [p for p in positions if p.type == 0] if positions else []
                            buy_orders = [o for o in orders if o.type == mt5.ORDER_TYPE_BUY_LIMIT] if orders else []
                            if not buy_positions and not buy_orders:
                                buy_tp = mid
                                buy_sl = pred_low - 15.0
                                if self.execution_engine and pred_low < tick.bid:
                                    self.logger.info(f"Sideways Range Repeater: Arming BUY Limit at Low boundary {pred_low}")
                                    await self.execution_engine.execute_pending_limit_order(
                                        symbol, "BUY", pred_low, buy_sl, buy_tp, base_lot
                                    )
                                    
                            # Arm SELL Limit at high boundary if no active SELL position/order
                            sell_positions = [p for p in positions if p.type == 1] if positions else []
                            sell_orders = [o for o in orders if o.type == mt5.ORDER_TYPE_SELL_LIMIT] if orders else []
                            if not sell_positions and not sell_orders:
                                sell_tp = mid
                                sell_sl = pred_high + 15.0
                                if self.execution_engine and pred_high > tick.bid:
                                    self.logger.info(f"Sideways Range Repeater: Arming SELL Limit at High boundary {pred_high}")
                                    await self.execution_engine.execute_pending_limit_order(
                                        symbol, "SELL", pred_high, sell_sl, sell_tp, base_lot
                                    )
                                    
                        # B. Trending / Default Zone Scaling Logic
                        else:
                            # Dynamic Lot Weighting:
                            lot_market = normalize_vol(base_lot * 0.30)
                            lot_limit1 = normalize_vol(base_lot * 0.50)
                            lot_limit2 = normalize_vol(base_lot * 1.20)
                            
                            # Auto-Reset Grid: If no active positions exist, cancel old leftover limit orders and start fresh
                            if not has_positions:
                                if has_orders and orders:
                                    self.logger.info("HLC Strategy: All active positions closed. Cancelling old pending orders to start a fresh cycle.")
                                    for o in orders:
                                        if "LIMIT" in getattr(o, "comment", "") or "HLC" in getattr(o, "comment", ""):
                                            req = {
                                                "action": mt5.TRADE_ACTION_REMOVE,
                                                "order": o.ticket
                                            }
                                            mt5.order_send(req)
                                    # Refresh orders
                                    orders = mt5.orders_get(symbol=symbol)
                                    has_orders = orders is not None and len(orders) > 0
                                    
                                # Whipsaw Prevention: Add buffer around midpoint to avoid opening trades on tiny fluctuations
                                mid_buffer = max(1.0, 0.1 * grid_dist)
                                
                                # Trigger trade sequence based on bias and mid price with buffer filter
                                # For range trading (bias ANY): Buy Low (bid <= mid - buffer), Sell High (bid >= mid + buffer)
                                if bias == "BUY_ONLY" or (bias == "ANY" and tick.bid <= mid - mid_buffer):
                                    buy_tp = pred_high - 1.0 # Safety buffer
                                    buy_sl = pred_low - 15.0
                                    
                                    # A. Instant Market BUY Entry (Lot 30%)
                                    if self.execution_engine:
                                        self.logger.info(f"HLC Strategy: Triggering Market BUY Entry ({lot_market} lot) at Open price {tick.ask}")
                                        await self.execution_engine.execute_order(symbol, "BUY", lot_market)
                                        
                                    # B. Pullback BUY LIMIT 1 (Lot 50%) at Mid-Pullback (TP at midpoint for high probability)
                                    limit_price_1 = mid - 0.5 * grid_dist
                                    if self.execution_engine and limit_price_1 < tick.bid:
                                        await self.execution_engine.execute_pending_limit_order(
                                            symbol, "BUY", limit_price_1, buy_sl, mid, lot_limit1
                                        )
                                        
                                    # C. Pullback BUY LIMIT 2 (Lot 120%) at Extreme Low (TP at extreme high for max profit)
                                    if self.execution_engine and pred_low < tick.bid:
                                        await self.execution_engine.execute_pending_limit_order(
                                            symbol, "BUY", pred_low, buy_sl, buy_tp, lot_limit2
                                        )
                                        
                                elif bias == "SELL_ONLY" or (bias == "ANY" and tick.bid >= mid + mid_buffer):
                                    sell_tp = pred_low + 1.0 # Safety buffer
                                    sell_sl = pred_high + 15.0
                                    
                                    # A. Instant Market SELL Entry (Lot 30%)
                                    if self.execution_engine:
                                        self.logger.info(f"HLC Strategy: Triggering Market SELL Entry ({lot_market} lot) at Open price {tick.bid}")
                                        await self.execution_engine.execute_order(symbol, "SELL", lot_market)
                                        
                                    # B. Pullback SELL LIMIT 1 (Lot 50%) at Mid-Pullback (TP at midpoint for high probability)
                                    limit_price_1 = mid + 0.5 * grid_dist
                                    if self.execution_engine and limit_price_1 > tick.bid:
                                        await self.execution_engine.execute_pending_limit_order(
                                            symbol, "SELL", limit_price_1, sell_sl, mid, lot_limit1
                                        )
                                        
                                    # C. Pullback SELL LIMIT 2 (Lot 120%) at Extreme High (TP at extreme low for max profit)
                                    if self.execution_engine and pred_high > tick.bid:
                                        await self.execution_engine.execute_pending_limit_order(
                                            symbol, "SELL", pred_high, sell_sl, sell_tp, lot_limit2
                                        )
                                        
                            elif has_positions:
                                # A. Active Position Management: Cancel opposing pending limit orders
                                active_pos_type = positions[0].type # 0 = BUY, 1 = SELL
                                if has_orders:
                                    for o in orders:
                                        # If active position is BUY, cancel SELL LIMIT pending orders
                                        if active_pos_type == 0 and o.type == mt5.ORDER_TYPE_SELL_LIMIT:
                                            cancel_req = {"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket}
                                            mt5.order_send(cancel_req)
                                            self.logger.info(f"HLC Strategy: Cancelled opposing SELL limit order #{o.ticket} because BUY position is active.")
                                        # If active position is SELL, cancel BUY LIMIT pending orders
                                        elif active_pos_type == 1 and o.type == mt5.ORDER_TYPE_BUY_LIMIT:
                                            cancel_req = {"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket}
                                            mt5.order_send(cancel_req)
                                            self.logger.info(f"HLC Strategy: Cancelled opposing BUY limit order #{o.ticket} because SELL position is active.")
                                            
                                # B. Disaster Auto-Hedge Lock check
                                total_vol = sum(p.volume for p in positions)
                                if active_pos_type == 0 and tick.bid <= (pred_low - 12.0):
                                    # BUY positions breached: open SELL hedge lock
                                    if not any(p.type == 1 for p in positions):
                                        self.logger.warning(f"HLC Strategy Breach: BUY Positions breached extreme low level. Triggering SELL Hedge Lock of {total_vol} lots.")
                                        if self.execution_engine:
                                            await self.execution_engine.execute_order(symbol, "SELL", total_vol)
                                            
                                elif active_pos_type == 1 and tick.ask >= (pred_high + 12.0):
                                    # SELL positions breached: open BUY hedge lock
                                    if not any(p.type == 0 for p in positions):
                                        self.logger.warning(f"HLC Strategy Breach: SELL Positions breached extreme high level. Triggering BUY Hedge Lock of {total_vol} lots.")
                                        if self.execution_engine:
                                            await self.execution_engine.execute_order(symbol, "BUY", total_vol)
                                            
            except Exception as e:
                self.logger.error(f"Error in _forecast_hlc_bound_loop: {e}", exc_info=True)
                
            await asyncio.sleep(30)
